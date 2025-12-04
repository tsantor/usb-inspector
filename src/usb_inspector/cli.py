import asyncio
import json
import signal

import click

from usb_inspector.db import delete_data_file
from usb_inspector.db import delete_usb_db
from usb_inspector.db import lookup_usb_details
from usb_inspector.monitor import USBDeviceMonitor
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


@cli.command()
def monitor():
    """Start monitoring USB devices. Stop with Ctrl+C."""

    async def run_monitor():
        monitor = USBDeviceMonitor(poll_interval=1.0)

        async def callback(event_type, device_info):
            click.secho(
                f"{event_type.upper()}: {json.dumps(device_info, indent=2)}",
                fg="cyan" if event_type == "connected" else "yellow",
            )

        # Start monitoring
        click.secho("Starting USB device monitor. Press Ctrl+X to stop.", fg="green")
        await monitor.run(callback)

    def stop_monitor():
        click.secho("\nStopping USB device monitor...", fg="red")
        loop.stop()

    # Set up asyncio loop and signal handling for Ctrl+X
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGQUIT, stop_monitor)  # Ctrl+X sends SIGQUIT
    try:
        loop.run_until_complete(run_monitor())
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()
