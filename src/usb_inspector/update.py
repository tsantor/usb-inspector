import re
import sqlite3
import urllib.request
from pathlib import Path

import chardet
import click
import pandas as pd

from usb_inspector import data_file
from usb_inspector import usb_db


def dataframes_to_sqlite(vendors_df, devices_df):
    """
    Writes two pandas DataFrames to a SQLite database with proper foreign key
    relationship.

    :param vendors_df: DataFrame containing vendor information.
    :param devices_df: DataFrame containing device information.
    :param db_name: The name of the SQLite database file.
    """
    # Connect to the SQLite database (creates the file if it doesn't exist)
    conn = sqlite3.connect(usb_db)

    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON")

    # Write the vendors DataFrame to the vendors table
    vendors_df.to_sql("vendors", conn, if_exists="replace", index=False)

    # Write the devices DataFrame to the devices table
    devices_df.to_sql("devices", conn, if_exists="replace", index=False)

    # Create indexes for better query performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vendor_id ON vendors(vendor_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_device_vendor ON devices(vendor_id)")

    # Commit and close the connection
    conn.commit()
    conn.close()
    click.secho(f"✅ Data successfully written to **{Path(usb_db).name}**", fg="green")
    click.echo(f"\t- Table 'vendors': {len(vendors_df):,} records")
    click.echo(f"\t- Table 'devices': {len(devices_df):,} records")


def parse_usb_ids_to_dataframes(data_string):
    """
    Parses the USB ID list into two pandas DataFrames (vendors and devices).

    :param data_string: The content of the usb.ids file as a string.
    :return: A tuple of (vendors_df, devices_df).
    """
    lines = data_string.splitlines()
    vendors = []
    devices = []
    current_vendor_id = None
    current_vendor_name = None

    # Use regular expressions to match lines with IDs and names
    # Vendor: Starts with 4 hex digits, followed by name
    vendor_pattern = re.compile(r"^([0-9a-fA-F]{4})\s+(.*)$")
    # Device: Starts with a single tab, 4 hex digits, followed by name
    device_pattern = re.compile(r"^\t([0-9a-fA-F]{4})\s+(.*)$")

    for line in lines:
        if not line or line.startswith("#"):
            continue  # Skip comments and empty lines

        # 1. Try to match a Vendor
        vendor_match = vendor_pattern.match(line)
        if vendor_match:
            current_vendor_id = vendor_match.group(1)
            current_vendor_name = vendor_match.group(2).strip()
            # Add vendor to vendors list
            vendors.append(
                {
                    "vendor_id": current_vendor_id,
                    "vendor_name": current_vendor_name,
                }
            )
            continue

        # 2. Try to match a Device (requires an active vendor)
        if current_vendor_id:
            device_match = device_pattern.match(line)
            if device_match:
                device_id = device_match.group(1)
                device_name = device_match.group(2).strip()
                # Add device to devices list with FK to vendor
                devices.append(
                    {
                        "device_id": device_id,
                        "device_name": device_name,
                        "vendor_id": current_vendor_id,  # Foreign key
                    }
                )
                continue

    # Convert the lists to DataFrames
    vendors_df = pd.DataFrame(vendors)
    devices_df = pd.DataFrame(devices)

    return vendors_df, devices_df


def update_usb_db() -> bool:
    """Update the USB database."""
    url = "http://www.linux-usb.org/usb.ids"

    if Path(usb_db).exists():
        click.secho(
            (
                f"⚠️ Database '{Path(usb_db).name}' already exists. "
                "Remove it to recreate."
            ),
            fg="yellow",
        )
        return False

    # Download the latest usb.ids file if not present
    if not data_file.exists():
        click.echo(f"Downloading latest usb.ids file from '{url}'...")
        urllib.request.urlretrieve(url, str(data_file))  # noqa: S310
        click.secho("✅ Download complete.", fg="green")

    # Run the parsing function
    with data_file.open("rb") as f:
        raw_data = f.read()
        detected_encoding = chardet.detect(raw_data)["encoding"]

    # Open the file with the detected encoding
    with data_file.open("r", encoding=detected_encoding) as f:
        data = f.read()

    vendors_df, devices_df = parse_usb_ids_to_dataframes(data)

    click.secho("✅ Vendors DataFrame created successfully.", fg="green")
    # click.echo(vendors_df.head(10).to_markdown(index=False))
    click.secho("✅ Devices DataFrame created successfully.", fg="green")
    # click.echo(devices_df.head(10).to_markdown(index=False))

    dataframes_to_sqlite(vendors_df, devices_df)
    return True
