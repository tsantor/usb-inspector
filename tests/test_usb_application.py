from unittest.mock import MagicMock

from usb_inspector.usb.application.service import USBMonitoringService


class FakeEnumerator:
    def __init__(self, devices):
        self._devices = devices

    def iter_devices(self):
        return self._devices


class FakeLookup:
    def lookup(self, vendor_id, device_id=None):
        return {
            "vendor_id": vendor_id,
            "vendor_name": "Vendor",
            "device_id": device_id,
            "device_name": "Device",
        }


def test_service_get_device_info_uses_ports():
    device = MagicMock()
    device.idVendor = 0x1234
    device.idProduct = 0x5678
    device.bcdDevice = 0x0100
    device.bus = 1
    device.address = 2
    device.port_numbers = (1, 2)
    device.manufacturer = "Short Vendor"
    device.product = None
    device.serial_number = "SERIAL"

    service = USBMonitoringService(
        enumerator=FakeEnumerator([device]),
        details_lookup=FakeLookup(),
        poll_interval=1,
    )
    service.usb_details_cache = {}

    info = service.get_device_info(device)

    assert info.vendor_id == "1234"
    assert info.device_id == "5678"
    assert info.vendor_name is not None
    assert info.full_system_uid.endswith("SERIAL")
