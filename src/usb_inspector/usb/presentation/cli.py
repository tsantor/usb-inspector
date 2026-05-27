import asyncio
import dataclasses
import json
import signal

import click


@click.group()
@click.pass_context
def cli(ctx):
    """USB Inspector CLI"""
    ctx.ensure_object(dict)


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
@click.pass_obj
def lookup(services, vendor_id, device_id):
    details = services["lookup_service"].lookup(vendor_id, device_id)
    if details:
        click.echo(json.dumps(details, indent=2))
    else:
        click.secho(
            "⚠️ No details found for the given Vendor ID and Device ID.",
            fg="yellow",
        )


@cli.command()
@click.pass_obj
def update_db(services):
    services["maintenance_service"].update_db()
    click.secho("✅ USB database updated successfully.", fg="green")


@cli.command()
@click.pass_obj
def delete_db(services):
    services["maintenance_service"].delete_db()
    click.secho("✅ USB database deleted successfully.", fg="green")


@cli.command()
@click.pass_obj
def delete_data(services):
    services["maintenance_service"].delete_data_file()
    click.secho("✅ Data file deleted successfully.", fg="green")


@cli.command()
@click.pass_obj
def monitor(services):
    service = services["monitoring_service"]

    async def run_monitor():
        async def callback(event_type, device_info):
            click.secho(
                f"{event_type.upper()}: {json.dumps(dataclasses.asdict(device_info), indent=2)}",
                fg="cyan" if event_type == "connected" else "yellow",
            )

        click.secho("Starting USB device monitor. Press Ctrl+C to stop.", fg="green")
        await service.run(callback)

    def stop_monitor():
        click.secho("\nStopping USB device monitor...", fg="red")
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
                continue

    loop = asyncio.get_event_loop()
    _register_signal_handlers()
    try:
        loop.run_until_complete(run_monitor())
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        loop.run_until_complete(service.stop())
    finally:
        loop.close()
