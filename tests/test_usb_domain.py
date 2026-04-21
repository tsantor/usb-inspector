import pytest

import usb_inspector.usb.domain as domain_package
from usb_inspector.usb.domain.entities import USBDeviceSnapshot
from usb_inspector.usb.domain.exceptions import InvalidDeviceIdError
from usb_inspector.usb.domain.exceptions import InvalidVendorIdError
from usb_inspector.usb.domain.value_objects import DeviceId
from usb_inspector.usb.domain.value_objects import FullSystemUid
from usb_inspector.usb.domain.value_objects import PortPath
from usb_inspector.usb.domain.value_objects import SimpleUid
from usb_inspector.usb.domain.value_objects import VendorId

CONNECTED_BUS = 3
CONNECTED_ADDRESS = 4


def test_vendor_id_normalizes_uppercase_hex():
    vendor = VendorId("1A40")
    assert vendor.value == "1a40"


def test_domain_package_exports_snapshot():
    assert domain_package.USBDeviceSnapshot is USBDeviceSnapshot


def test_domain_exceptions_are_constructible():
    assert str(InvalidVendorIdError("bad vendor")) == "bad vendor"
    assert str(InvalidDeviceIdError("bad device")) == "bad device"


def test_device_id_normalizes_uppercase_hex():
    device = DeviceId("0801")
    assert device.value == "0801"


def test_vendor_id_rejects_wrong_length():
    with pytest.raises(ValueError, match="Vendor ID must be 4 hex characters"):
        VendorId("123")


def test_device_id_rejects_non_hex():
    with pytest.raises(ValueError, match="invalid literal for int\\(\\) with base 16"):
        DeviceId("zzzz")


def test_uid_value_objects_store_value():
    assert SimpleUid("1a40:0801").value == "1a40:0801"
    assert FullSystemUid("1a40:0801:serial").value == "1a40:0801:serial"
    assert PortPath("1.2.3").value == "1.2.3"


def test_usb_device_snapshot_state_transitions():
    snapshot = USBDeviceSnapshot(
        vendor_id="1a40",
        device_id="0801",
        version=1,
        bus=1,
        address=2,
        uid="1a40_0801",
        full_system_uid="1a40:0801:abc",
        is_connected=False,
        last_seen="2026-03-13T00:00:00+00:00",
    )

    snapshot.mark_connected(
        "2026-03-13T00:00:10+00:00",
        bus=CONNECTED_BUS,
        address=CONNECTED_ADDRESS,
    )
    assert snapshot.is_connected is True
    assert snapshot.last_seen == "2026-03-13T00:00:10+00:00"
    assert snapshot.bus == CONNECTED_BUS
    assert snapshot.address == CONNECTED_ADDRESS

    snapshot.mark_disconnected("2026-03-13T00:00:20+00:00")
    assert snapshot.is_connected is False
    assert snapshot.last_seen == "2026-03-13T00:00:20+00:00"
