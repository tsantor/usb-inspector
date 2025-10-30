import json

import click

from usb_inspector.db import delete_data_file
from usb_inspector.db import delete_usb_db
from usb_inspector.db import lookup_usb_details
from usb_inspector.update import update_usb_db


@click.group()
def cli():
    """USB Inspector CLI"""


@cli.command()
@click.option(
    "--vendor-id", "-v", required=True, help="Vendor ID of the USB device (4-digit hex)"
)
@click.option(
    "--device-id",
    "-d",
    required=False,
    help="Device ID of the USB device (4-digit hex)",
)
def lookup(vendor_id, device_id):
    """Lookup USB device details by Vendor ID and optional Device ID."""
    details = lookup_usb_details(vendor_id, device_id)
    if details:
        click.echo(json.dumps(details, indent=2))
    else:
        click.secho(
            "⚠️ No details found for the given Vendor ID and Device ID.",
            fg="yellow",
        )


@cli.command()
def update_db():
    """Update the USB database from a given source URL."""
    update_usb_db()
    click.secho("✅ USB database updated successfully.", fg="green")


@cli.command()
def delete_db():
    """Delete the existing USB database."""
    delete_usb_db()
    click.secho("✅ USB database deleted successfully.", fg="green")


@cli.command()
def delete_data():
    """Delete the existing usb.ids data file."""
    delete_data_file()
    click.secho("✅ Data file deleted successfully.", fg="green")
