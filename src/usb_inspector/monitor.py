from usb_inspector.usb.application.service import USBMonitoringService
from usb_inspector.usb.infrastructure.repository import PyUSBEnumerator
from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository


class USBDeviceMonitor(USBMonitoringService):
    """Compatibility wrapper for legacy monitor import path."""

    def __init__(self, poll_interval: float = 1.0):
        super().__init__(
            enumerator=PyUSBEnumerator(),
            details_lookup=SQLiteUSBDetailsRepository(),
            poll_interval=poll_interval,
        )
