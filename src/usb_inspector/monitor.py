import asyncio
import logging

# import time
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass

import usb.core

from usb_inspector.db import lookup_usb_details

logger = logging.getLogger(__name__)


@dataclass
class UsbData:
    vendor_id: str
    bus: int
    address: int
    device_id: str


class USBDeviceMonitor:
    """Cross-platform async USB device monitor using pyusb"""

    def __init__(self, poll_interval: float = 1.0):
        """
        Initialize the USB monitor

        Args:
            poll_interval: Time in seconds between device checks
        """
        self.poll_interval = poll_interval
        self.previous_devices = set()
        self.current_devices_list = []
        self._monitoring = False

    def get_device_uid(self, device) -> str:
        """Generate unique identifier for a USB device"""
        return f"{device.idVendor:04x}:{device.idProduct:04x}:{device.bus}:{device.address}"

    def get_device_info(self, device) -> dict[str, any]:
        """Extract detailed information from a USB device"""
        info = {
            "device_id": f"{device.idProduct:04x}",
            "vendor_id": f"{device.idVendor:04x}",
            "version": device.bcdDevice,
            "bus": device.bus,
            "address": device.address,
            "uid": self.get_device_uid(device),
        }

        # Try to get manufacturer and product strings (may fail without permissions)
        try:
            info["vendor_name_short"] = device.manufacturer
        except (ValueError, usb.core.USBError, NotImplementedError):
            info["vendor_name_short"] = None

        try:
            info["device_name"] = device.product
        except (ValueError, usb.core.USBError, NotImplementedError):
            info["device_name"] = None

        try:
            info["serial"] = device.serial_number
        except (ValueError, usb.core.USBError, NotImplementedError):
            info["serial"] = None

        # Lookup additional details from the USB database
        details = lookup_usb_details(info["vendor_id"], info["device_id"])
        if details:
            info["vendor_name"] = details["vendor_name"]
            if info["device_name"] is None:
                logger.debug(
                    "Found device name for %s:%s: %s",
                    info["vendor_id"],
                    info["device_id"],
                    details["device_name"],
                )
                info["device_name"] = details["device_name"]
            # info.update(details)
        info["vendor_name"] = f"{details['vendor_name']}"
        if info["vendor_name_short"]:
            info["vendor_name"] += f" ({info['vendor_name_short']})"

        # Sort the dictionary by keys
        return dict(sorted(info.items()))

    async def get_current_devices(self) -> list[dict[str, any]]:
        """Get list of all currently connected USB devices (async)"""
        # Run USB enumeration in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_devices_sync)

    def _get_devices_sync(self) -> list[dict[str, any]]:
        """Synchronous helper for device enumeration"""
        return [self.get_device_info(device) for device in usb.core.find(find_all=True)]

    async def monitor(
        self, callback: Callable[[str, dict], Awaitable[None]] | None = None
    ):
        """
        Monitor USB devices for changes (async)

        Args:
            callback: Optional async function to call when devices change.
                     Receives (event_type, device_info) where event_type is
                     'connected' or 'disconnected'
        """
        logger.info("Starting USB device monitor...")

        self._monitoring = True

        # Get initial device list
        current_devices_list = await self.get_current_devices()
        self.previous_devices = {dev["device_id"] for dev in current_devices_list}

        logger.info("Currently connected devices: %d", len(current_devices_list))
        for dev in current_devices_list:
            manufacturer = dev.get("vendor_name", None)
            product = dev.get("device_name", None)
            logger.info(
                "  - %s %s (%s:%s)",
                manufacturer,
                product,
                dev.get("vendor_id"),
                dev.get("device_id"),
            )

        try:
            while self._monitoring:
                # start_time = time.perf_counter()

                # Get current devices
                self.current_devices_list = await self.get_current_devices()
                current_device_ids = {
                    dev["device_id"] for dev in self.current_devices_list
                }

                # Find newly connected devices
                new_devices = current_device_ids - self.previous_devices
                if new_devices:
                    for dev in self.current_devices_list:
                        if dev["device_id"] in new_devices:
                            manufacturer = dev.get("vendor_name", None)
                            product = dev.get("device_name", None)
                            logger.info(
                                "[CONNECTED] - %s %s (%s:%s)",
                                manufacturer,
                                product,
                                dev.get("vendor_id"),
                                dev.get("device_id"),
                            )
                            if callback:
                                await callback("connected", dev)

                # Find disconnected devices
                removed_devices = self.previous_devices - current_device_ids
                if removed_devices:
                    for dev_id in removed_devices:
                        logger.info("[DISCONNECTED] Device %s", dev_id)
                        if callback:
                            await callback("disconnected", {"device_id": dev_id})

                self.previous_devices = current_device_ids

                # end_time = time.perf_counter()  # End timing
                # elapsed_time = end_time - start_time
                # logger.info("Poll duration: %.4f seconds", elapsed_time)

                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
            raise
        except KeyboardInterrupt:
            logger.info("Monitoring stopped")

    async def start(
        self, callback: Callable[[str, dict], Awaitable[None]] | None = None
    ):
        """Alias for monitor() to start monitoring"""
        await self.monitor(callback)

    def stop(self):
        """Stop monitoring"""
        self._monitoring = False
