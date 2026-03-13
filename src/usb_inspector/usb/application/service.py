import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from datetime import datetime
from typing import Any

from usb_inspector.usb.application.ports import USBDetailsLookupPort
from usb_inspector.usb.application.ports import USBEnumeratorPort

logger = logging.getLogger(__name__)


class USBMonitoringService:
    """Application service that orchestrates USB monitoring use-cases."""

    usb_details_cache = {}

    def __init__(
        self,
        enumerator: USBEnumeratorPort,
        details_lookup: USBDetailsLookupPort,
        poll_interval: float = 1.0,
    ):
        self._enumerator = enumerator
        self._details_lookup = details_lookup
        self._shutdown_event = asyncio.Event()
        self._loop_interval = poll_interval
        self.previous_system_uids = set()
        self.device_registry = {}
        self.devices_by_type = {}
        self._callback = None

    def get_simple_uid(self, device) -> str:
        return f"{device.idVendor:04x}:{device.idProduct:04x}"

    def get_full_system_uid(self, device) -> str:
        vendor_device = self.get_simple_uid(device)

        try:
            serial = device.serial_number
            if serial:
                return f"{vendor_device}:{serial}"
        except Exception:  # pragma: no cover  # noqa: BLE001, S110
            pass

        port_path = self.get_port_path(device)
        if port_path:
            return f"{vendor_device}:bus{device.bus}:port{port_path}"

        return f"{vendor_device}:bus{device.bus}:address{device.address}"

    def get_port_path(self, device) -> str | None:
        try:
            if device.port_numbers:
                return ".".join(str(p) for p in device.port_numbers)
        except Exception:  # pragma: no cover  # noqa: BLE001
            return None
        return None

    def get_device_info(self, device) -> dict[str, Any]:
        vendor_id_str = f"{device.idVendor:04x}"
        device_id_str = f"{device.idProduct:04x}"
        simple_uid = f"{vendor_id_str}_{device_id_str}"
        full_system_uid = self.get_full_system_uid(device)
        port_path = self.get_port_path(device)

        timestamp = datetime.now().astimezone().isoformat()

        info = {
            "device_id": device_id_str,
            "vendor_id": vendor_id_str,
            "version": getattr(device, "bcdDevice", None),
            "bus": getattr(device, "bus", None),
            "port": port_path,
            "address": getattr(device, "address", None),
            "uid": simple_uid,
            "full_system_uid": full_system_uid,
            "is_connected": True,
            "last_seen": timestamp,
        }

        try:
            info["vendor_name_short"] = device.manufacturer
        except Exception:  # pragma: no cover  # noqa: BLE001
            info["vendor_name_short"] = None

        try:
            info["device_name"] = device.product
        except Exception:  # pragma: no cover  # noqa: BLE001
            info["device_name"] = None

        try:
            info["serial"] = device.serial_number
        except Exception:  # pragma: no cover  # noqa: BLE001
            info["serial"] = None

        cache_key = f"{info['vendor_id']}:{info['device_id']}"
        if cache_key not in self.usb_details_cache:
            details = self._details_lookup.lookup(info["vendor_id"], info["device_id"])
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

        return dict(sorted(info.items()))

    async def get_current_devices(self) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_devices_sync)

    def _get_devices_sync(self) -> list[dict[str, Any]]:
        return [
            self.get_device_info(device) for device in self._enumerator.iter_devices()
        ]

    async def _handle_new_devices(self, new_devices: list[dict[str, Any]]):
        timestamp = datetime.now().astimezone().isoformat()

        for dev in new_devices:
            simple_uid = dev["uid"]
            full_system_uid = dev["full_system_uid"]

            if full_system_uid in self.device_registry:
                old_dev = self.device_registry[full_system_uid]
                old_dev["bus"] = dev["bus"]
                old_dev["address"] = dev["address"]
                old_dev["is_connected"] = True
                old_dev["last_seen"] = timestamp
                dev = old_dev  # noqa: PLW2901
            else:
                dev["is_connected"] = True
                dev["last_seen"] = timestamp
                self.device_registry[full_system_uid] = dev

                if simple_uid not in self.devices_by_type:
                    self.devices_by_type[simple_uid] = set()
                self.devices_by_type[simple_uid].add(full_system_uid)

            manufacturer = dev.get("vendor_name", "Unknown")
            product = dev.get("device_name", "Unknown")

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
        timestamp = datetime.now().astimezone().isoformat()

        for full_system_uid in removed_system_uids:
            dev = self.device_registry.get(full_system_uid)

            if dev:
                dev["is_connected"] = False
                dev["last_seen"] = timestamp
                self.device_registry[full_system_uid] = dev

                manufacturer = dev.get("vendor_name", "Unknown")
                product = dev.get("device_name", "Unknown")
                simple_uid = dev["uid"]

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
        initial_devices = await self.get_current_devices()
        logger.info("Currently connected devices: %d", len(initial_devices))

        for dev in initial_devices:
            simple_uid = dev["uid"]
            full_system_uid = dev["full_system_uid"]
            self.device_registry[full_system_uid] = dev

            if simple_uid not in self.devices_by_type:
                self.devices_by_type[simple_uid] = set()
            self.devices_by_type[simple_uid].add(full_system_uid)
            self.previous_system_uids.add(full_system_uid)

            logger.info(
                "  - %s %s ('%s')",
                dev.get("vendor_name", "Unknown"),
                dev.get("device_name", "Unknown"),
                dev["full_system_uid"],
            )

    async def run(self, callback: Callable[[str, dict], Awaitable[None]] | None = None):
        self._callback = callback
        await self.init_tracking()

        try:
            while not self._shutdown_event.is_set():
                current_devices_list = await self.get_current_devices()
                current_system_uids = {
                    dev["full_system_uid"] for dev in current_devices_list
                }

                new_system_uids = current_system_uids - self.previous_system_uids
                if new_system_uids:
                    new_devices = [
                        dev
                        for dev in current_devices_list
                        if dev["full_system_uid"] in new_system_uids
                    ]
                    await self._handle_new_devices(new_devices)

                removed_system_uids = self.previous_system_uids - current_system_uids
                if removed_system_uids:
                    await self._handle_removed_devices(removed_system_uids)

                self.previous_system_uids = current_system_uids

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
        await self.run(callback)

    async def stop(self):
        self._shutdown_event.set()

    async def wait_or_timeout(self, timeout: float):  # noqa: ASYNC109
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout)
            return True
        except TimeoutError:
            return False

    def get_all_devices(self) -> dict[str, dict[str, Any]]:
        return self.device_registry.copy()

    def get_connected_devices(self) -> list[dict[str, Any]]:
        return [
            dev
            for dev in self.device_registry.values()
            if dev.get("is_connected", False)
        ]

    def get_disconnected_devices(self) -> list[dict[str, Any]]:
        return [
            dev
            for dev in self.device_registry.values()
            if not dev.get("is_connected", True)
        ]

    def get_devices_by_type(self, simple_uid: str) -> list[dict[str, Any]]:
        return [
            self.device_registry[full_uid]
            for full_uid in self.devices_by_type[simple_uid]
            if full_uid in self.device_registry
        ]

    def get_connected_devices_by_type(self, simple_uid: str) -> list[dict[str, Any]]:
        devices = self.get_devices_by_type(simple_uid)
        return [dev for dev in devices if dev.get("is_connected", False)]

    def get_device_by_full_uid(self, full_system_uid: str) -> dict[str, Any] | None:
        return self.device_registry.get(full_system_uid)

    def get_device_types(self) -> list[str]:
        return list(self.devices_by_type.keys())

    def get_device_type_summary(self) -> dict[str, dict[str, Any]]:
        summary = {}
        for simple_uid, full_uids in self.devices_by_type.items():
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
