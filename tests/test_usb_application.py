from unittest.mock import MagicMock

import pytest

from usb_inspector.usb.application.service import USBMonitoringService


class FakeEnumerator:
    def __init__(self, devices):
        self.devices = devices

    def iter_devices(self):
        return self.devices


class FakeLookup:
    def lookup(self, vendor_id, device_id=None):
        return {
            "vendor_id": vendor_id,
            "vendor_name": "Vendor",
            "device_id": device_id,
            "device_name": "Device",
        }


class FakeUSBDevice:
    def __init__(self, serial, port_numbers=(1,), address=2):
        self.idVendor = 0x1234
        self.idProduct = 0x5678
        self.bcdDevice = 0x0100
        self.bus = 1
        self.address = address
        self.port_numbers = port_numbers
        self.manufacturer = "Short Vendor"
        self.product = "Product"
        self._serial = serial
        self.serial_reads = 0

    @property
    def serial_number(self):
        self.serial_reads += 1
        if isinstance(self._serial, Exception):
            raise self._serial
        return self._serial


def make_service(devices):
    return USBMonitoringService(
        enumerator=FakeEnumerator(devices),
        details_lookup=FakeLookup(),
        poll_interval=1,
    )


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


def test_service_reads_serial_once_per_snapshot():
    device = FakeUSBDevice("SERIAL")
    service = make_service([device])

    info = service.get_device_info(device)

    assert info.serial == "SERIAL"
    assert info.full_system_uid == "1234:5678:SERIAL"
    assert device.serial_reads == 1


@pytest.mark.asyncio
async def test_serial_read_failure_reuses_identity_from_usb_topology():
    enumerator = FakeEnumerator([FakeUSBDevice("SERIAL")])
    service = make_service([])
    service._enumerator = enumerator  # noqa: SLF001

    await service.init_tracking()
    canonical_uid = "1234:5678:SERIAL"
    # A changed address represents the normal re-enumeration case that must
    # not produce a duplicate device.
    enumerator.devices = [FakeUSBDevice(RuntimeError("serial unavailable"), address=99)]

    current_devices = await service.get_current_devices()

    assert [device.full_system_uid for device in current_devices] == [canonical_uid]
    assert {device.full_system_uid for device in current_devices} == service.previous_system_uids
    assert len(service.device_registry) == 1


@pytest.mark.asyncio
async def test_serial_recovery_enriches_initial_topology_identity():
    enumerator = FakeEnumerator([FakeUSBDevice(None)])
    service = make_service([])
    service._enumerator = enumerator  # noqa: SLF001

    await service.init_tracking()
    canonical_uid = "1234:5678:bus1:port1"
    enumerator.devices = [FakeUSBDevice("RECOVERED")]
    current_devices = await service.get_current_devices()
    service._refresh_known_devices(current_devices)  # noqa: SLF001

    assert current_devices[0].full_system_uid == canonical_uid
    assert service.device_registry[canonical_uid].serial == "RECOVERED"
    assert len(service.device_registry) == 1


@pytest.mark.asyncio
async def test_identical_devices_on_distinct_ports_remain_distinct():
    service = make_service(
        [
            FakeUSBDevice(None, port_numbers=(1,)),
            FakeUSBDevice(None, port_numbers=(2,)),
        ]
    )

    await service.init_tracking()

    assert set(service.device_registry) == {
        "1234:5678:bus1:port1",
        "1234:5678:bus1:port2",
    }


@pytest.mark.asyncio
async def test_different_serial_at_same_port_is_a_replacement():
    enumerator = FakeEnumerator([FakeUSBDevice("FIRST")])
    service = make_service([])
    service._enumerator = enumerator  # noqa: SLF001

    await service.init_tracking()
    enumerator.devices = [FakeUSBDevice("SECOND")]
    current_devices = await service.get_current_devices()

    assert current_devices[0].full_system_uid == "1234:5678:SECOND"
    assert current_devices[0].full_system_uid not in service.previous_system_uids
