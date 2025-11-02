import asyncio
import logging

# import time
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

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
        self.previous_devices_uids = set()  # Changed to store UIDs
        self.current_devices_list = []
        self._monitoring = False
        # Track all devices we've ever seen with their full details
        # Key is now a combined identifier: "vendor_id_device_id" (e.g., "076b_5022")
        self.device_registry = {}  # key: str (UID), value: device info dict
        self._callback = None

    def get_device_uid(self, device) -> str:
        """
        Generate unique identifier for a USB device in the format
        "vendor_id_device_id"
        (e.g., "076b_5022") for the registry key.
        The full UID (vendor:device:bus:address) is still used for *true*
        uniqueness on the system.
        """
        return f"{device.idVendor:04x}_{device.idProduct:04x}"

    def get_full_system_uid(self, device) -> str:
        """Generate unique identifier for a USB device including bus/address"""
        return f"{device.idVendor:04x}:{device.idProduct:04x}:{device.bus}:{device.address}"

    def get_device_info(self, device) -> dict[str, any]:
        """Extract detailed information from a USB device"""
        vendor_id_str = f"{device.idVendor:04x}"
        device_id_str = f"{device.idProduct:04x}"
        uid = f"{vendor_id_str}_{device_id_str}"  # New registry key

        info = {
            "device_id": device_id_str,
            "vendor_id": vendor_id_str,
            "version": device.bcdDevice,
            "bus": device.bus,
            "address": device.address,
            "uid": uid,  # Registry key identifier
            "full_system_uid": self.get_full_system_uid(device),
            "is_connected": True,  # Add connection status
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
            info["vendor_name"] = details.get("vendor_name", "Unknown")
            if info["device_name"] is None:
                logger.debug(
                    "Found device name for %s:%s: %s",
                    info["vendor_id"],
                    info["device_id"],
                    details.get("device_name", "Unknown"),
                )
                info["device_name"] = details.get("device_name", "Unknown")
        else:
            info["vendor_name"] = "Unknown"

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

    async def _handle_new_devices(self, new_uids: set[str]):
        """Handle newly connected devices and call callback if provided."""
        for dev in self.current_devices_list:
            if dev["uid"] in new_uids:
                # Register/update device in registry
                self.device_registry[dev["uid"]] = dev

                manufacturer = dev.get("vendor_name", None)
                product = dev.get("device_name", None)
                logger.info(
                    "[CONNECTED] - %s %s (%s:%s)",
                    manufacturer,
                    product,
                    dev.get("vendor_id"),
                    dev.get("device_id"),
                )
                if self._callback:
                    await self._callback("connected", dev)

    async def _handle_removed_devices(self, removed_uids: set[str]):
        """Handle disconnected devices and call callback if provided."""
        for dev_uid in removed_uids:
            # Get full device info from registry
            if dev_uid in self.device_registry:
                dev_info = self.device_registry[dev_uid].copy()
                dev_info["is_connected"] = False
                self.device_registry[dev_uid] = (
                    dev_info  # Update connection status in registry
                )

                manufacturer = dev_info.get("vendor_name", None)
                product = dev_info.get("device_name", None)
                logger.info(
                    "[DISCONNECTED] - %s %s (%s:%s)",
                    manufacturer,
                    product,
                    dev_info.get("vendor_id"),
                    dev_info.get("device_id"),
                )
                if self._callback:
                    await self._callback("disconnected", dev_info)
            else:
                # Fallback if device wasn't in registry (shouldn't happen with correct UID logic)
                logger.info(
                    "[DISCONNECTED] Device %s (UID not found in registry)", dev_uid
                )
                if self._callback:
                    # Provide minimal info for the disconnected event
                    vendor_id, device_id = (
                        dev_uid.split("_") if "_" in dev_uid else (None, None)
                    )
                    await self._callback(
                        "disconnected",
                        {
                            "uid": dev_uid,
                            "vendor_id": vendor_id,
                            "device_id": device_id,
                            "is_connected": False,
                        },
                    )

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
        self._callback = callback  # Store callback for use in helper methods

        # Get initial device list
        current_devices_list = await self.get_current_devices()
        self.previous_devices_uids = {dev["uid"] for dev in current_devices_list}

        # Register initial devices using the combined UID
        for dev in current_devices_list:
            dev["last_seen"] = datetime.now().astimezone().isoformat()
            self.device_registry[dev["uid"]] = dev

        logger.info("Currently connected devices: %d", len(current_devices_list))
        for dev in current_devices_list:
            manufacturer = dev.get("vendor_name", None)
            product = dev.get("device_name", None)
            logger.info(
                "  - %s %s (%s)",
                manufacturer,
                product,
                dev.get("uid"),
            )

        try:
            while self._monitoring:
                # start_time = time.perf_counter()

                # Get current devices
                self.current_devices_list = await self.get_current_devices()
                current_device_uids = {dev["uid"] for dev in self.current_devices_list}

                # Find newly connected devices
                new_devices_uids = current_device_uids - self.previous_devices_uids
                if new_devices_uids:
                    await self._handle_new_devices(new_devices_uids)

                # Find disconnected devices
                removed_devices_uids = self.previous_devices_uids - current_device_uids
                if removed_devices_uids:
                    await self._handle_removed_devices(removed_devices_uids)

                # Update last_seen for currently connected devices
                for dev in self.current_devices_list:
                    dev["last_seen"] = datetime.now().astimezone().isoformat()
                    self.device_registry[dev["uid"]] = dev

                self.previous_devices_uids = current_device_uids

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

    def get_all_devices(self) -> dict[str, dict[str, any]]:
        """
        Get all devices that have been seen by the monitor.

        Returns:
            Dictionary mapping combined UID (vendor_id_device_id) to device info (includes is_connected status)
        """
        return self.device_registry.copy()

    def get_connected_devices(self) -> list[dict[str, any]]:
        """Get list of currently connected devices from registry"""
        return [
            dev
            for dev in self.device_registry.values()
            if dev.get("is_connected", False)
        ]

    def get_disconnected_devices(self) -> list[dict[str, any]]:
        """Get list of previously connected but now disconnected devices"""
        return [
            dev
            for dev in self.device_registry.values()
            if not dev.get("is_connected", True)
        ]
