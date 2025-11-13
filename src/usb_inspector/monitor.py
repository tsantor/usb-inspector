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
        self._shutdown_event = asyncio.Event()
        self.poll_interval = poll_interval
        self.previous_system_uids = (
            set()
        )  # Track full system UIDs (includes bus/address)
        self._monitoring = False
        # Registry uses simple UID (vendor_device) as key
        # This tracks device info but not multiple instances
        self.device_registry = {}  # key: str (simple UID), value: device info dict
        # Track currently connected devices with full system info
        self.connected_devices = {}  # key: full_system_uid, value: device info
        self._callback = None

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
            "uid": simple_uid,  # Simple identifier
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
        # Run USB enumeration in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_devices_sync)

    def _get_devices_sync(self) -> list[dict[str, any]]:
        """Synchronous helper for device enumeration"""
        return [self.get_device_info(device) for device in usb.core.find(find_all=True)]

    async def _handle_new_devices(self, new_devices: list[dict[str, any]]):
        """Handle newly connected devices and call callback if provided."""
        timestamp = datetime.now().astimezone().isoformat()

        for dev in new_devices:
            # Update registry with latest info (using simple UID)
            self.device_registry[dev["uid"]] = {
                **dev,
                "is_connected": True,
                "last_seen": timestamp,
            }

            # Add to connected devices tracking (using full system UID)
            self.connected_devices[dev["full_system_uid"]] = dev

            manufacturer = dev.get("vendor_name", "Unknown")
            product = dev.get("device_name", "Unknown")
            logger.info(
                "[CONNECTED] - %s %s (%s:%s) [%s]",
                manufacturer,
                product,
                dev["vendor_id"],
                dev["device_id"],
                dev["full_system_uid"],
            )

            if self._callback:
                await self._callback("connected", dev)

    async def _handle_removed_devices(self, removed_system_uids: set[str]):
        """Handle disconnected devices and call callback if provided."""
        timestamp = datetime.now().astimezone().isoformat()

        for full_system_uid in removed_system_uids:
            # Get device info from connected_devices
            dev = self.connected_devices.get(full_system_uid)

            if dev:
                # Update registry (using simple UID)
                simple_uid = dev["uid"]
                self.device_registry[simple_uid] = {
                    **dev,
                    "is_connected": False,
                    "last_seen": timestamp,
                }

                # Remove from connected devices
                del self.connected_devices[full_system_uid]

                manufacturer = dev.get("vendor_name", "Unknown")
                product = dev.get("device_name", "Unknown")
                logger.info(
                    "[DISCONNECTED] - %s %s (%s:%s) [%s]",
                    manufacturer,
                    product,
                    dev["vendor_id"],
                    dev["device_id"],
                    full_system_uid,
                )

                if self._callback:
                    await self._callback("disconnected", dev)
            else:
                # Shouldn't happen, but log if it does
                logger.warning(
                    "[DISCONNECTED] Device %s not found in connected_devices",
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

            # Add to registry
            self.device_registry[simple_uid] = dev

            # Add to connected devices
            self.connected_devices[full_system_uid] = dev

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
                # start_time = time.perf_counter()
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
                    # logger.debug("New devices: %s", new_system_uids)
                    await self._handle_new_devices(new_devices)

                # Find disconnected devices
                removed_system_uids = self.previous_system_uids - current_system_uids
                if removed_system_uids:
                    # logger.debug("Removed devices: %s", removed_system_uids)
                    await self._handle_removed_devices(removed_system_uids)

                # Update last_seen for all currently connected devices
                timestamp = datetime.now().astimezone().isoformat()
                for dev in current_devices_list:
                    simple_uid = dev["uid"]
                    full_system_uid = dev["full_system_uid"]

                    # Update registry
                    if simple_uid in self.device_registry:
                        self.device_registry[simple_uid]["last_seen"] = timestamp

                    # Update connected devices tracking
                    if full_system_uid in self.connected_devices:
                        self.connected_devices[full_system_uid]["last_seen"] = timestamp

                # Update tracking set
                self.previous_system_uids = current_system_uids

                # elapsed = time.perf_counter() - start_time
                # logger.debug("USB monitor iteration took %.3f seconds", elapsed)

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
        """Get all devices that have been seen by the monitor."""
        return self.device_registry.copy()

    def get_connected_devices(self) -> list[dict[str, any]]:
        """Get list of currently connected devices"""
        return list(self.connected_devices.values())

    def get_disconnected_devices(self) -> list[dict[str, any]]:
        """Get list of previously connected but now disconnected devices"""
        return [
            dev
            for dev in self.device_registry.values()
            if not dev.get("is_connected", True)
        ]
