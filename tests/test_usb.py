import asyncio
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from usb_inspector.monitor import USBDeviceMonitor


@pytest.fixture
def usb_device():
    """Fixture to create a mock USB device."""
    device = MagicMock()
    device.idVendor = 0x1234
    device.idProduct = 0x5678
    device.bcdDevice = 0x0100
    device.bus = 1
    device.address = 2
    device.port_numbers = (1, 2)
    device.manufacturer = "Test Manufacturer"
    device.product = "Test Product"
    device.serial_number = "ABC123"
    return device


@pytest.fixture
def usb_device2():
    """Fixture to create a mock USB device."""
    device = MagicMock()
    device.idVendor = 0x0987
    device.idProduct = 0x6543
    device.bcdDevice = 0x0100
    device.bus = 1
    device.address = 3
    device.port_numbers = (1, 3)
    device.manufacturer = "Test Manufacturer 2"
    device.product = "Test Product 2"
    device.serial_number = "ABC456"
    return device


@pytest.fixture
def monitor():
    """Fixture to create a USBDeviceMonitor instance."""
    return USBDeviceMonitor(poll_interval=1)


@patch("usb.core.find")
def test_get_device_info(mock_find, monitor, usb_device):
    """Test the get_device_info method."""
    mock_find.return_value = [usb_device]

    device_info = monitor.get_device_info(usb_device)

    assert device_info["vendor_id"] == "1234"
    assert device_info["device_id"] == "5678"
    assert device_info["bus"] == 1
    assert device_info["address"] == 2
    assert device_info["port"] == "1.2"
    assert device_info["vendor_name_short"] == "Test Manufacturer"
    assert device_info["device_name"] == "Test Product"
    assert device_info["serial"] == "ABC123"


@patch("usb.core.find")
@pytest.mark.asyncio
async def test_get_current_devices(mock_find, monitor, usb_device):
    """Test the get_current_devices method."""
    mock_find.return_value = [usb_device]

    devices = await monitor.get_current_devices()

    assert len(devices) == 1
    assert devices[0]["vendor_id"] == "1234"
    assert devices[0]["device_id"] == "5678"


@patch("usb.core.find")
@pytest.mark.asyncio
async def test_handle_new_devices(mock_find, monitor, usb_device):
    """Test the _handle_new_devices method."""
    mock_find.return_value = [usb_device]

    # Simulate adding a device
    await monitor._handle_new_devices([usb_device])  # noqa: SLF001

    device_info = monitor.get_device_info(usb_device)
    assert device_info["is_connected"] is True

    # Test reconnecting the same device
    await monitor._handle_new_devices([usb_device])  # noqa: SLF001


@patch("usb.core.find")
@pytest.mark.asyncio
async def test_handle_removed_devices(mock_find, monitor, usb_device):
    """Test the _handle_removed_devices method."""
    mock_find.return_value = [usb_device]

    # Simulate adding a device
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info

    # Simulate removing the device
    removed_uids = {device_info["full_system_uid"]}
    await monitor._handle_removed_devices(removed_uids)  # noqa: SLF001

    assert (
        monitor.device_registry[device_info["full_system_uid"]]["is_connected"] is False
    )


@patch("usb.core.find")
@pytest.mark.asyncio
async def test_run(mock_find, monitor, usb_device):
    """Test the run method."""
    mock_find.return_value = [usb_device]

    async def mock_callback(event_type, device_info):
        assert event_type in ["connected", "disconnected"]
        assert device_info is not None

    monitor._callback = mock_callback  # noqa: SLF001

    # Run the monitor for a short time
    with patch.object(monitor, "wait_or_timeout", side_effect=[False, True]):
        await monitor.run(mock_callback)


def test_get_connected_devices(monitor, usb_device):
    """Test the get_connected_devices method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info

    connected_devices = monitor.get_connected_devices()
    assert len(connected_devices) == 1
    assert connected_devices[0]["is_connected"] is True


def test_get_disconnected_devices(monitor, usb_device):
    """Test the get_disconnected_devices method."""
    device_info = monitor.get_device_info(usb_device)
    device_info["is_connected"] = False
    monitor.device_registry[device_info["full_system_uid"]] = device_info

    disconnected_devices = monitor.get_disconnected_devices()
    assert len(disconnected_devices) == 1
    assert disconnected_devices[0]["is_connected"] is False


def test_get_devices_by_type(monitor, usb_device):
    """Test the get_devices_by_type method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info
    monitor.devices_by_type[device_info["uid"]] = {device_info["full_system_uid"]}

    devices = monitor.get_devices_by_type(device_info["uid"])
    assert len(devices) == 1
    assert devices[0]["vendor_id"] == "1234"


def test_get_connected_devices_by_type(monitor, usb_device):
    """Test the get_connected_devices_by_type method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info
    monitor.devices_by_type[device_info["uid"]] = {device_info["full_system_uid"]}

    devices = monitor.get_connected_devices_by_type(device_info["uid"])
    assert len(devices) == 1
    assert devices[0]["vendor_id"] == "1234"


def test_get_device_by_full_uid(monitor, usb_device):
    """Test the get_device_by_full_uid method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info

    device = monitor.get_device_by_full_uid(device_info["full_system_uid"])
    assert device["vendor_id"] == "1234"
    assert device["device_id"] == "5678"


def test_get_all_devices(monitor, usb_device):
    """Test the get_all_devices method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info

    all_devices = monitor.get_all_devices()
    assert isinstance(all_devices, dict)
    assert len(all_devices) == 1


def test_get_device_types(monitor, usb_device):
    """Test the get_device_types method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info
    monitor.devices_by_type[device_info["uid"]] = {device_info["full_system_uid"]}

    device_types = monitor.get_device_types()
    assert isinstance(device_types, list)
    assert device_info["uid"] in device_types


def test_get_device_type_summary(monitor, usb_device):
    """Test the get_device_type_summary method."""
    device_info = monitor.get_device_info(usb_device)
    monitor.device_registry[device_info["full_system_uid"]] = device_info
    monitor.devices_by_type[device_info["uid"]] = {device_info["full_system_uid"]}

    device_type_summary = monitor.get_device_type_summary()
    assert isinstance(device_type_summary, dict)


@pytest.mark.asyncio
async def test_get_current_devices_real():
    """Test USBDeviceMonitor with real USB devices"""
    # Create an instance of USBDeviceMonitor
    monitor = USBDeviceMonitor(poll_interval=1.0)
    # Get the current devices
    current_devices = await monitor.get_current_devices()
    # Ensure we get a list back
    assert isinstance(current_devices, list), "Expected a list of devices"
    # Log the devices for debugging
    # for device in current_devices:
    #     print(json.dumps(device, indent=2))
    # Ensure each device in the list is a dictionary
    for device in current_devices:
        assert isinstance(device, dict), "Each device should be a dictionary"
        assert "vendor_id" in device, "Each device should have a 'vendor_id' key"
        assert "vendor_name" in device, "Each device should have a 'vendor_name' key"
        assert "device_id" in device, "Each device should have a 'device_id' key"
        assert "device_name" in device, "Each device should have a 'device_name' key"
