import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from datetime import datetime

import usb.core

from usb_inspector.db import lookup_usb_details

logger = logging.getLogger(__name__)


class USBDeviceMonitor:
    """Cross-platform async USB device monitor using pyusb"""

    usb_details_cache = {}

    def __init__(self, poll_interval: float = 1.0):
        self._shutdown_event = asyncio.Event()
        self._loop_interval = poll_interval
        self.previous_system_uids = set()

        # Primary registry: tracks ALL device instances by full system UID
        self.device_registry = {}
        # Secondary index: tracks which full system UIDs belong to each device type
        self.devices_by_type = {}

        self._callback = None

    def get_simple_uid(self, device) -> str:
        """
        Generate simple identifier for device type: "vendor_id:device_id"
        """
        return f"{device.idVendor:04x}:{device.idProduct:04x}"

    def get_full_system_uid(self, device) -> str:
        """
        Generate unique identifier for a USB device.
        Priority order:
        1. Serial number (if available) - most stable
        2. Bus + port path - stable for same physical port
        3. Bus + address - fallback (may change on reconnect)
        """
        vendor_device = self.get_simple_uid(device)

        # Try to get serial number (most stable)
        try:
            serial = device.serial_number
            if serial:
                return f"{vendor_device}:{serial}"
        except (ValueError, usb.core.USBError, NotImplementedError):
            pass

        # Try to use port path (stable for same physical port)
        port_path = self.get_port_path(device)
        if port_path:
            return f"{vendor_device}:bus{device.bus}:port{port_path}"

        # Fall back to bus:address (may change on reconnect)
        return f"{vendor_device}:bus{device.bus}:address{device.address}"

    def get_port_path(self, device) -> str | None:
        """
        Get the physical port path for a device.
        This is more stable than bus:address across reconnections.
        """
        try:
            # port_numbers is a tuple representing the physical USB port path
            # e.g., (1, 2) means hub port 1, then port 2
            if device.port_numbers:
                return ".".join(str(p) for p in device.port_numbers)
        except (AttributeError, ValueError, usb.core.USBError):  # pragma: no cover
            return None

    def get_device_info(self, device) -> dict[str, any]:
        """Extract detailed information from a USB device"""
        vendor_id_str = f"{device.idVendor:04x}"
        device_id_str = f"{device.idProduct:04x}"
        simple_uid = f"{vendor_id_str}_{device_id_str}"
        full_system_uid = self.get_full_system_uid(device)
        port_path = self.get_port_path(device)

        timestamp = datetime.now().astimezone().isoformat()

        info = {
            "device_id": device_id_str,
            "vendor_id": vendor_id_str,
            "version": device.bcdDevice,
            "bus": device.bus,
            "port": port_path,
            "address": device.address,
            "uid": simple_uid,  # Simple identifier (device type)
            "full_system_uid": full_system_uid,  # Full unique identifier
            "is_connected": True,
            "last_seen": timestamp,
        }

        # Try to get manufacturer and product strings
        try:
            info["vendor_name_short"] = device.manufacturer
        except (ValueError, usb.core.USBError, NotImplementedError):  # pragma: no cover
            info["vendor_name_short"] = None

        try:
            info["device_name"] = device.product
        except (ValueError, usb.core.USBError, NotImplementedError):  # pragma: no cover
            info["device_name"] = None

        try:
            info["serial"] = device.serial_number
        except (ValueError, usb.core.USBError, NotImplementedError):  # pragma: no cover
            info["serial"] = None

        # Check if details are already cached
        cache_key = f"{info['vendor_id']}:{info['device_id']}"
        if cache_key not in self.usb_details_cache:
            # Lookup additional details from the USB database
            details = lookup_usb_details(info["vendor_id"], info["device_id"])
            self.usb_details_cache[cache_key] = details
        else:
            details = self.usb_details_cache[cache_key]

        if details:
            info["vendor_name"] = details.get("vendor_name", "Unknown")
            if info["device_name"] is None:
                info["device_name"] = details.get("device_name", "Unknown")
        else:
            info["vendor_name"] = "Unknown"

        if info["vendor_name_short"]:
            info["vendor_name"] += f" ({info['vendor_name_short']})"

        # Sort the dictionary by keys
        return dict(sorted(info.items()))

    async def get_current_devices(self) -> list[dict[str, any]]:
        """Get list of all currently connected USB devices (async)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_devices_sync)

    def _get_devices_sync(self) -> list[dict[str, any]]:
        """Synchronous helper for device enumeration"""
        return [self.get_device_info(device) for device in usb.core.find(find_all=True)]

    async def _handle_new_devices(self, new_devices: list[dict[str, any]]):
        """Handle newly connected devices and call callback if provided."""
        timestamp = datetime.now().astimezone().isoformat()

        for dev in new_devices:
            simple_uid = dev["uid"]
            full_system_uid = dev["full_system_uid"]

            # Check if this device was previously seen (by full_system_uid)
            # If so, update its bus/address and mark as reconnected
            if full_system_uid in self.device_registry:
                # Device reconnected - update bus/address which may have changed
                old_dev = self.device_registry[full_system_uid]
                old_dev["bus"] = dev["bus"]
                old_dev["address"] = dev["address"]
                old_dev["is_connected"] = True
                old_dev["last_seen"] = timestamp
                dev = old_dev  # noqa: PLW2901
            else:
                # Brand new device
                dev["is_connected"] = True
                dev["last_seen"] = timestamp
                self.device_registry[full_system_uid] = dev

                # Update type index
                if simple_uid not in self.devices_by_type:
                    self.devices_by_type[simple_uid] = set()
                self.devices_by_type[simple_uid].add(full_system_uid)

            manufacturer = dev.get("vendor_name", "Unknown")
            product = dev.get("device_name", "Unknown")

            # Count how many of this type are now connected
            connected_count = len(
                [
                    uid
                    for uid in self.devices_by_type[simple_uid]
                    if self.device_registry.get(uid, {}).get("is_connected", False)
                ]
            )

            logger.info(
                "[CONNECTED] - %s %s ('%s') (device %d of this type)",
                manufacturer,
                product,
                full_system_uid,
                connected_count,
            )

            if self._callback:
                await self._callback("connected", dev)

    async def _handle_removed_devices(self, removed_system_uids: set[str]):
        """Handle disconnected devices and call callback if provided."""
        timestamp = datetime.now().astimezone().isoformat()

        for full_system_uid in removed_system_uids:
            # Get device info from registry
            dev = self.device_registry.get(full_system_uid)

            if dev:
                # Update connection status
                dev["is_connected"] = False
                dev["last_seen"] = timestamp
                self.device_registry[full_system_uid] = dev

                manufacturer = dev.get("vendor_name", "Unknown")
                product = dev.get("device_name", "Unknown")
                simple_uid = dev["uid"]

                # Count remaining connected devices of this type
                connected_count = len(
                    [
                        uid
                        for uid in self.devices_by_type.get(simple_uid, set())
                        if self.device_registry.get(uid, {}).get("is_connected", False)
                    ]
                )

                logger.info(
                    "[DISCONNECTED] - %s %s ('%s') (device %d of this type)",
                    manufacturer,
                    product,
                    full_system_uid,
                    connected_count,
                )

                if self._callback:
                    await self._callback("disconnected", dev)
            else:
                logger.warning(
                    "[DISCONNECTED] Device %s not found in registry",
                    full_system_uid,
                )

    async def init_tracking(self) -> None:
        # Get initial device list
        initial_devices = await self.get_current_devices()
        logger.info("Currently connected devices: %d", len(initial_devices))

        # Initialize tracking structures
        for dev in initial_devices:
            simple_uid = dev["uid"]
            full_system_uid = dev["full_system_uid"]

            # Add to main registry
            self.device_registry[full_system_uid] = dev

            # Add to type index
            if simple_uid not in self.devices_by_type:
                self.devices_by_type[simple_uid] = set()
            self.devices_by_type[simple_uid].add(full_system_uid)

            # Track system UID
            self.previous_system_uids.add(full_system_uid)

            logger.info(
                "  - %s %s ('%s')",
                dev.get("vendor_name", "Unknown"),
                dev.get("device_name", "Unknown"),
                dev["full_system_uid"],
            )

    async def run(self, callback: Callable[[str, dict], Awaitable[None]] | None = None):
        """
        Monitor USB devices for changes (async)

        Args:
            callback: Optional async function to call when devices change.
                     Receives (event_type, device_info) where event_type is
                     'connected' or 'disconnected'
        """

        self._callback = callback

        await self.init_tracking()

        try:
            while not self._shutdown_event.is_set():
                # Get current devices
                current_devices_list = await self.get_current_devices()
                current_system_uids = {
                    dev["full_system_uid"] for dev in current_devices_list
                }

                # Find newly connected devices
                new_system_uids = current_system_uids - self.previous_system_uids
                if new_system_uids:
                    new_devices = [
                        dev
                        for dev in current_devices_list
                        if dev["full_system_uid"] in new_system_uids
                    ]
                    await self._handle_new_devices(new_devices)

                # Find disconnected devices
                removed_system_uids = self.previous_system_uids - current_system_uids
                if removed_system_uids:
                    await self._handle_removed_devices(removed_system_uids)

                # Update tracking set
                self.previous_system_uids = current_system_uids

                # Wait for the loop interval or shutdown signal
                shutdown_signaled = await self.wait_or_timeout(self._loop_interval)
                if shutdown_signaled:
                    break

        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
            raise
        except KeyboardInterrupt:
            logger.info("Monitoring stopped")

    async def start(
        self, callback: Callable[[str, dict], Awaitable[None]] | None = None
    ):
        """Alias for monitor() to start monitoring"""
        await self.run(callback)

    async def stop(self):
        """Trigger shutdown."""
        self._shutdown_event.set()

    async def wait_or_timeout(self, timeout: float):  # noqa: ASYNC109
        """Wait for shutdown event or timeout."""
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout)
            return True
        except TimeoutError:
            return False

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def get_all_devices(self) -> dict[str, dict[str, any]]:
        """Get all device instances that have been seen by the monitor."""
        return self.device_registry.copy()

    def get_connected_devices(self) -> list[dict[str, any]]:
        """Get list of currently connected device instances"""
        return [
            dev
            for dev in self.device_registry.values()
            if dev.get("is_connected", False)
        ]

    def get_disconnected_devices(self) -> list[dict[str, any]]:
        """Get list of previously connected but now disconnected device instances"""
        return [
            dev
            for dev in self.device_registry.values()
            if not dev.get("is_connected", True)
        ]

    def get_devices_by_type(self, simple_uid: str) -> list[dict[str, any]]:
        """
        Get all instances (connected and disconnected) of a specific device type.
        """
        return [
            self.device_registry[full_uid]
            for full_uid in self.devices_by_type[simple_uid]
            if full_uid in self.device_registry
        ]

    def get_connected_devices_by_type(self, simple_uid: str) -> list[dict[str, any]]:
        """
        Get all currently connected instances of a specific device type.
        """
        devices = self.get_devices_by_type(simple_uid)
        return [dev for dev in devices if dev.get("is_connected", False)]

    def get_device_by_full_uid(self, full_system_uid: str) -> dict[str, any] | None:
        """Get a specific device instance by its full system UID."""
        return self.device_registry.get(full_system_uid)

    def get_device_types(self) -> list[str]:
        """Get list of all device types (simple UIDs) that have been seen."""
        return list(self.devices_by_type.keys())

    def get_device_type_summary(self) -> dict[str, dict[str, any]]:
        """Get summary of all device types with connection counts."""
        summary = {}
        for simple_uid, full_uids in self.devices_by_type.items():
            # Get one device instance for name/vendor info
            sample_device = None
            for full_uid in full_uids:
                if full_uid in self.device_registry:
                    sample_device = self.device_registry[full_uid]
                    break

            if sample_device:
                connected_count = sum(
                    1
                    for uid in full_uids
                    if self.device_registry.get(uid, {}).get("is_connected", False)
                )
                total_count = len(full_uids)

                summary[simple_uid] = {
                    "vendor_id": sample_device["vendor_id"],
                    "device_id": sample_device["device_id"],
                    "vendor_name": sample_device.get("vendor_name", "Unknown"),
                    "device_name": sample_device.get("device_name", "Unknown"),
                    "connected_count": connected_count,
                    "total_seen_count": total_count,
                    "disconnected_count": total_count - connected_count,
                }

        return summary
