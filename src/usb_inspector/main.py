from usb_inspector.usb.infrastructure.factory import create_usb_lookup_service
from usb_inspector.usb.infrastructure.factory import create_usb_maintenance_service
from usb_inspector.usb.infrastructure.factory import create_usb_monitoring_service
from usb_inspector.usb.presentation.cli import cli


def main():
    cli(
        standalone_mode=True,
        obj={
            "lookup_service": create_usb_lookup_service(),
            "maintenance_service": create_usb_maintenance_service(),
            "monitoring_service": create_usb_monitoring_service(),
        },
    )
