from usb_inspector.usb.application.service import USBMonitoringService
from usb_inspector.usb.infrastructure.repository import PyUSBEnumerator
from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository


def create_usb_monitoring_service(poll_interval: float = 1.0) -> USBMonitoringService:
    return USBMonitoringService(
        enumerator=PyUSBEnumerator(),
        details_lookup=SQLiteUSBDetailsRepository(),
        poll_interval=poll_interval,
    )
