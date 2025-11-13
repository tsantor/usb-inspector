import asyncio
import logging
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
        self._shutdown_event = asyncio.Event()
        self.poll_interval = poll_interval
        self.previous_system_uids = set()  # Track full system UIDs
        self._monitoring = False

        # Primary registry: tracks ALL device instances by full system UID
        self.device_registry = {}  # key: full_system_uid, value: device info dict

        # Secondary index: tracks which full system UIDs belong to each device type
        # This allows looking up "all printers of type X" efficiently
        self.devices_by_type = {}  # key: simple_uid, value: set of full_system_uids

        self._callback = None

    def get_simple_uid(self, device) -> str:
        """
        Generate simple identifier for device type: "vendor_id_device_id"
        """
        return f"{device.idVendor:04x}_{device.idProduct:04x}"

    def get_full_system_uid(self, device) -> str:
        """Generate unique identifier for a USB device including bus/address"""
        return f"{device.idVendor:04x}:{device.idProduct:04x}:{device.bus}:{device.address}"

    def get_device_info(self, device) -> dict[str, any]:
        """Extract detailed information from a USB device"""
        vendor_id_str = f"{device.idVendor:04x}"
        device_id_str = f"{device.idProduct:04x}"
        simple_uid = f"{vendor_id_str}_{device_id_str}"
        full_system_uid = self.get_full_system_uid(device)

        timestamp = datetime.now().astimezone().isoformat()

        info = {
            "device_id": device_id_str,
            "vendor_id": vendor_id_str,
            "version": device.bcdDevice,
            "bus": device.bus,
            "address": device.address,
            "uid": simple_uid,  # Simple identifier (device type)
            "full_system_uid": full_system_uid,  # Full unique identifier
            "is_connected": True,
            "last_seen": timestamp,
        }

        # Try to get manufacturer and product strings
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

            # Update device info
            dev["is_connected"] = True
            dev["last_seen"] = timestamp

            # Add to main registry (keyed by full system UID)
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
                "[CONNECTED] - %s %s (%s:%s) [%s] (device %d of this type)",
                manufacturer,
                product,
                dev["vendor_id"],
                dev["device_id"],
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
                    "[DISCONNECTED] - %s %s (%s:%s) [%s] (%d of this type still connected)",
                    manufacturer,
                    product,
                    dev["vendor_id"],
                    dev["device_id"],
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
        self._callback = callback

        # Get initial device list
        initial_devices = await self.get_current_devices()

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

        logger.info("Currently connected devices: %d", len(initial_devices))
        for dev in initial_devices:
            manufacturer = dev.get("vendor_name", "Unknown")
            product = dev.get("device_name", "Unknown")
            logger.info(
                "  - %s %s (%s) [%s]",
                manufacturer,
                product,
                dev["uid"],
                dev["full_system_uid"],
            )

        try:
            while self._monitoring:
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

        Args:
            simple_uid: Device type identifier (e.g., "076b_5022")

        Returns:
            List of device info dicts for all instances of this type
        """
        if simple_uid not in self.devices_by_type:
            return []

        return [
            self.device_registry[full_uid]
            for full_uid in self.devices_by_type[simple_uid]
            if full_uid in self.device_registry
        ]

    def get_connected_devices_by_type(self, simple_uid: str) -> list[dict[str, any]]:
        """
        Get all currently connected instances of a specific device type.

        Args:
            simple_uid: Device type identifier (e.g., "076b_5022")

        Returns:
            List of device info dicts for connected instances of this type
        """
        devices = self.get_devices_by_type(simple_uid)
        return [dev for dev in devices if dev.get("is_connected", False)]

    def get_device_by_full_uid(self, full_system_uid: str) -> dict[str, any] | None:
        """
        Get a specific device instance by its full system UID.

        Args:
            full_system_uid: Full system identifier (e.g., "076b:5022:1:5")

        Returns:
            Device info dict or None if not found
        """
        return self.device_registry.get(full_system_uid)

    def get_device_types(self) -> list[str]:
        """
        Get list of all device types (simple UIDs) that have been seen.

        Returns:
            List of simple UIDs
        """
        return list(self.devices_by_type.keys())

    def get_device_type_summary(self) -> dict[str, dict[str, any]]:
        """
        Get summary of all device types with connection counts.

        Returns:
            Dict mapping simple_uid to summary info including counts
        """
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
