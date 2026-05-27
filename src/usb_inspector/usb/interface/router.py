import asyncio
import json
import signal

import click

from usb_inspector.usb.interface.dependencies import get_details_repository
from usb_inspector.usb.interface.dependencies import get_maintenance_repository
from usb_inspector.usb.interface.dependencies import get_monitoring_service


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
    details = get_details_repository().lookup(vendor_id, device_id)
    if details:
        click.echo(json.dumps(details, indent=2))
    else:
        click.secho(
            "⚠️ No details found for the given Vendor ID and Device ID.",
            fg="yellow",
        )


@cli.command()
def update_db():
    get_maintenance_repository().update_usb_db()
    click.secho("✅ USB database updated successfully.", fg="green")


@cli.command()
def delete_db():
    get_maintenance_repository().delete_usb_db()
    click.secho("✅ USB database deleted successfully.", fg="green")


@cli.command()
def delete_data():
    get_maintenance_repository().delete_data_file()
    click.secho("✅ Data file deleted successfully.", fg="green")


@cli.command()
def monitor():
    service = None

    async def run_monitor():
        nonlocal service
        service = get_monitoring_service(poll_interval=1.0)

        async def callback(event_type, device_info):
            click.secho(
                f"{event_type.upper()}: {json.dumps(device_info, indent=2)}",
                fg="cyan" if event_type == "connected" else "yellow",
            )

        click.secho("Starting USB device monitor. Press Ctrl+C to stop.", fg="green")
        await service.run(callback)

    def stop_monitor():
        click.secho("\nStopping USB device monitor...", fg="red")
        if service is not None:
            loop.create_task(service.stop())

    def _register_signal_handlers():
        # Windows does not expose SIGQUIT and some event loops do not support
        # add_signal_handler; register only what's available.
        for name in ("SIGINT", "SIGTERM", "SIGQUIT"):
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            try:
                loop.add_signal_handler(sig, stop_monitor)
            except NotImplementedError:
                # Fallback for platforms/event loops without signal support.
                continue

    loop = asyncio.get_event_loop()
    _register_signal_handlers()
    try:
        loop.run_until_complete(run_monitor())
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        if service is not None:
            loop.run_until_complete(service.stop())
    finally:
        loop.close()
