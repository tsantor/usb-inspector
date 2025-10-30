import asyncio
import json

import pytest
from rich import print

from usb_inspector.monitor import USBDeviceMonitor


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
    for device in current_devices:
        print(json.dumps(device, indent=2))

    # Ensure each device in the list is a dictionary
    for device in current_devices:
        assert isinstance(device, dict), "Each device should be a dictionary"
        assert "vendor_id" in device, "Each device should have a 'vendor_id' key"
        assert "vendor_name" in device, "Each device should have a 'vendor_name' key"
        assert "device_id" in device, "Each device should have a 'device_id' key"
        assert "device_name" in device, "Each device should have a 'device_name' key"
