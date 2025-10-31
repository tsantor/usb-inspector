import re
import sqlite3

import chardet
import click
import pandas as pd
import requests

from usb_inspector import data_file
from usb_inspector import usb_db


def create_database_schema():
    """
    Create the SQLite database schema if it doesn't already exist.
    """
    conn = sqlite3.connect(usb_db)
    conn.execute("PRAGMA foreign_keys = ON")

    # Create the vendors table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id TEXT PRIMARY KEY,
            vendor_name TEXT NOT NULL
        )
        """
    )

    # Create the devices table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            vendor_id TEXT NOT NULL,
            FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id)
        )
        """
    )

    conn.commit()
    conn.close()


def update_existing_database(vendors_df: pd.DataFrame, devices_df: pd.DataFrame):
    """
    Update the existing SQLite database with new vendors and devices.

    :param vendors_df: DataFrame containing new vendor information.
    :param devices_df: DataFrame containing new device information.
    """
    # Connect to the SQLite database
    conn = sqlite3.connect(usb_db)

    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON")

    # Load existing data from the database
    existing_vendors = pd.read_sql("SELECT * FROM vendors", conn)
    existing_devices = pd.read_sql("SELECT * FROM devices", conn)

    # Find new vendors
    new_vendors = vendors_df[
        ~vendors_df["vendor_id"].isin(existing_vendors["vendor_id"])
    ]

    # Find new devices
    new_devices = devices_df[
        ~devices_df[["device_id", "vendor_id"]]
        .apply(tuple, axis=1)
        .isin(existing_devices[["device_id", "vendor_id"]].apply(tuple, axis=1))
    ]

    # Insert new vendors into the database
    if not new_vendors.empty:
        new_vendors.to_sql("vendors", conn, if_exists="append", index=False)
        click.secho(
            f"✅ Added {len(new_vendors):,} new vendors to the database.",
            fg="green",
        )
    else:
        click.secho("No new vendors to add.", fg="yellow")

    # Insert new devices into the database
    if not new_devices.empty:
        new_devices.to_sql("devices", conn, if_exists="append", index=False)
        click.secho(
            f"✅ Added {len(new_devices):,} new devices to the database.",
            fg="green",
        )
    else:
        click.secho("No new devices to add.", fg="yellow")

    # Commit and close the connection
    conn.commit()
    conn.close()


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
    """Update the USB database by adding new vendors and devices."""
    url = "http://www.linux-usb.org/usb.ids"

    # Ensure the database schema exists
    create_database_schema()

    # Download the latest usb.ids file if not present
    if not data_file.exists():
        click.echo(f"Downloading latest usb.ids file from '{url}'...")
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            with data_file.open("wb") as f:
                f.write(r.content)
            click.secho("✅ Download complete.", fg="green")
        except requests.exceptions.RequestException as e:
            click.secho(f"❌ Failed to download usb.ids: {e}", fg="red")
            return False

    # Run the parsing function
    with data_file.open("rb") as f:
        raw_data = f.read()
        detected_encoding = chardet.detect(raw_data)["encoding"]

    # Open the file with the detected encoding
    with data_file.open("r", encoding=detected_encoding) as f:
        data = f.read()

    # Parse the new usb.ids file into DataFrames
    vendors_df, devices_df = parse_usb_ids_to_dataframes(data)

    click.secho("✅ Vendors DataFrame created successfully.", fg="green")
    click.secho("✅ Devices DataFrame created successfully.", fg="green")

    # Update the database with new data
    update_existing_database(vendors_df, devices_df)
    return True
