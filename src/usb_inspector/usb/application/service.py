import asyncio
import logging
from collections.abc import Awaitable
from collections.abc import Callable
from datetime import datetime
from typing import Any

from usb_inspector.usb.application.ports import USBDetailsLookupPort
from usb_inspector.usb.application.ports import USBEnumeratorPort
from usb_inspector.usb.domain.entities import USBDeviceSnapshot

logger = logging.getLogger(__name__)
_UNREAD_SERIAL = object()


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
        self.previous_system_uids: set[str] = set()
        self.device_registry: dict[str, USBDeviceSnapshot] = {}
        self.devices_by_type: dict[str, set[str]] = {}
        # Keeps a device's identity stable when a backend temporarily cannot
        # retrieve its USB serial number.  A USB address is intentionally not
        # used when a port path is available because addresses can change on
        # re-enumeration.
        self.topology_to_system_uid: dict[str, str] = {}
        self._callback = None

    def get_simple_uid(self, device) -> str:
        return f"{device.idVendor:04x}:{device.idProduct:04x}"

    def get_full_system_uid(
        self,
        device,
        serial: str | None | object = _UNREAD_SERIAL,
        topology_key: str | None = None,
    ) -> str:
        vendor_device = self.get_simple_uid(device)

        if serial is _UNREAD_SERIAL:
            serial = self.get_serial_number(device)

        if serial:
            return f"{vendor_device}:{serial}"

        if topology_key is None:
            topology_key = self.get_topology_key(device, self.get_port_path(device))

        if topology_key:
            return topology_key

        return f"{vendor_device}:bus{device.bus}:address{device.address}"

    def get_topology_key(self, device, port_path: str | None = None) -> str | None:
        """Return the stable physical-location key when the backend exposes it."""
        if port_path:
            return f"{self.get_simple_uid(device)}:bus{device.bus}:port{port_path}"
        return None

    @staticmethod
    def get_serial_number(device) -> str | None:
        """Read the serial once so identity and displayed data cannot disagree."""
        try:
            return device.serial_number or None
        except Exception:  # pragma: no cover  # noqa: BLE001
            return None

    def get_port_path(self, device) -> str | None:
        try:
            if device.port_numbers:
                return ".".join(str(p) for p in device.port_numbers)
        except Exception:  # pragma: no cover  # noqa: BLE001
            return None
        return None

    def get_device_info(self, device) -> USBDeviceSnapshot:
        vendor_id_str = f"{device.idVendor:04x}"
        device_id_str = f"{device.idProduct:04x}"
        simple_uid = f"{vendor_id_str}_{device_id_str}"
        port_path = self.get_port_path(device)
        topology_key = self.get_topology_key(device, port_path)
        serial = self.get_serial_number(device)
        full_system_uid = self.get_full_system_uid(device, serial, topology_key)
        timestamp = datetime.now().astimezone().isoformat()

        try:
            vendor_name_short = device.manufacturer
        except Exception:  # pragma: no cover  # noqa: BLE001
            vendor_name_short = None

        try:
            device_name = device.product
        except Exception:  # pragma: no cover  # noqa: BLE001
            device_name = None

        cache_key = f"{vendor_id_str}:{device_id_str}"
        if cache_key not in self.usb_details_cache:
            details = self._details_lookup.lookup(vendor_id_str, device_id_str)
            self.usb_details_cache[cache_key] = details
        else:
            details = self.usb_details_cache[cache_key]

        vendor_name = "Unknown"
        if details:
            vendor_name = details.get("vendor_name", "Unknown")
            if device_name is None:
                device_name = details.get("device_name", "Unknown")

        if vendor_name_short:
            vendor_name += f" ({vendor_name_short})"

        return USBDeviceSnapshot(
            vendor_id=vendor_id_str,
            device_id=device_id_str,
            version=getattr(device, "bcdDevice", None),
            bus=getattr(device, "bus", None),
            address=getattr(device, "address", None),
            uid=simple_uid,
            full_system_uid=full_system_uid,
            is_connected=True,
            last_seen=timestamp,
            port=port_path,
            vendor_name=vendor_name,
            vendor_name_short=vendor_name_short,
            device_name=device_name,
            serial=serial,
            topology_key=topology_key,
        )

    async def get_current_devices(self) -> list[USBDeviceSnapshot]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_devices_sync)

    def _get_devices_sync(self) -> list[USBDeviceSnapshot]:
        devices = [
            self.get_device_info(device) for device in self._enumerator.iter_devices()
        ]
        return [self._reconcile_identity(device) for device in devices]

    def _reconcile_identity(self, device: USBDeviceSnapshot) -> USBDeviceSnapshot:
        """Resolve an observed device to its established canonical identity.

        Serial numbers are preferred for a newly observed device.  Once a
        device has been seen at a USB port, that port maps to its canonical
        identity so a transient serial read failure cannot create a duplicate.
        """
        topology_key = device.topology_key
        if topology_key:
            known_uid = self.topology_to_system_uid.get(topology_key)
            known_device = self.device_registry.get(known_uid) if known_uid else None

            if known_device:
                if device.serial and known_device.serial and device.serial != known_device.serial:
                    # A different serial at the same port is a replacement, not
                    # a transient failure. Let normal removed/new handling
                    # represent it as such.
                    device.full_system_uid = (
                        f"{device.vendor_id}:{device.device_id}:{device.serial}"
                    )
                else:
                    device.full_system_uid = known_uid
                return device

        if device.serial and device.full_system_uid in self.device_registry:
            # The device may have moved ports; the serial preserves continuity.
            return device

        return device

    def _remember_identity(self, device: USBDeviceSnapshot) -> None:
        if device.topology_key:
            self.topology_to_system_uid[device.topology_key] = device.full_system_uid

    @staticmethod
    def _refresh_observed_details(
        existing: USBDeviceSnapshot, observed: USBDeviceSnapshot
    ) -> None:
        """Enrich an existing record without changing its connection timestamp."""
        if observed.serial:
            existing.serial = observed.serial
        existing.port = observed.port

    def _refresh_known_devices(self, current_devices: list[USBDeviceSnapshot]) -> None:
        for device in current_devices:
            existing = self.device_registry.get(device.full_system_uid)
            if existing:
                self._refresh_observed_details(existing, device)
                self._remember_identity(device)

    async def _handle_new_devices(self, new_devices: list[USBDeviceSnapshot]):
        timestamp = datetime.now().astimezone().isoformat()

        for dev in new_devices:
            simple_uid = dev.uid
            full_system_uid = dev.full_system_uid

            if full_system_uid in self.device_registry:
                old_dev = self.device_registry[full_system_uid]
                old_dev.mark_connected(timestamp, dev.bus, dev.address)
                self._refresh_observed_details(old_dev, dev)
                dev = old_dev  # noqa: PLW2901
            else:
                dev.mark_connected(timestamp, dev.bus, dev.address)
                self.device_registry[full_system_uid] = dev

                if simple_uid not in self.devices_by_type:
                    self.devices_by_type[simple_uid] = set()
                self.devices_by_type[simple_uid].add(full_system_uid)

            self._remember_identity(dev)

            manufacturer = dev.vendor_name or "Unknown"
            product = dev.device_name or "Unknown"

            connected_count = sum(
                1
                for uid in self.devices_by_type[simple_uid]
                if self.device_registry.get(uid) is not None
                and self.device_registry[uid].is_connected
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
                dev.mark_disconnected(timestamp)

                manufacturer = dev.vendor_name or "Unknown"
                product = dev.device_name or "Unknown"
                simple_uid = dev.uid

                connected_count = sum(
                    1
                    for uid in self.devices_by_type.get(simple_uid, set())
                    if self.device_registry.get(uid) is not None
                    and self.device_registry[uid].is_connected
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
            simple_uid = dev.uid
            full_system_uid = dev.full_system_uid
            self.device_registry[full_system_uid] = dev
            self._remember_identity(dev)

            if simple_uid not in self.devices_by_type:
                self.devices_by_type[simple_uid] = set()
            self.devices_by_type[simple_uid].add(full_system_uid)
            self.previous_system_uids.add(full_system_uid)

            logger.info(
                "  - %s %s ('%s')",
                dev.vendor_name or "Unknown",
                dev.device_name or "Unknown",
                dev.full_system_uid,
            )

    async def run(self, callback: Callable[[str, USBDeviceSnapshot], Awaitable[None]] | None = None):
        self._callback = callback
        await self.init_tracking()

        try:
            while not self._shutdown_event.is_set():
                current_devices_list = await self.get_current_devices()
                self._refresh_known_devices(current_devices_list)
                current_system_uids = {dev.full_system_uid for dev in current_devices_list}

                new_system_uids = current_system_uids - self.previous_system_uids
                if new_system_uids:
                    new_devices = [
                        dev
                        for dev in current_devices_list
                        if dev.full_system_uid in new_system_uids
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
        self, callback: Callable[[str, USBDeviceSnapshot], Awaitable[None]] | None = None
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

    def get_all_devices(self) -> dict[str, USBDeviceSnapshot]:
        return self.device_registry.copy()

    def get_connected_devices(self) -> list[USBDeviceSnapshot]:
        return [dev for dev in self.device_registry.values() if dev.is_connected]

    def get_disconnected_devices(self) -> list[USBDeviceSnapshot]:
        return [dev for dev in self.device_registry.values() if not dev.is_connected]

    def get_devices_by_type(self, simple_uid: str) -> list[USBDeviceSnapshot]:
        return [
            self.device_registry[full_uid]
            for full_uid in self.devices_by_type[simple_uid]
            if full_uid in self.device_registry
        ]

    def get_connected_devices_by_type(self, simple_uid: str) -> list[USBDeviceSnapshot]:
        return [dev for dev in self.get_devices_by_type(simple_uid) if dev.is_connected]

    def get_device_by_full_uid(self, full_system_uid: str) -> USBDeviceSnapshot | None:
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
                    if self.device_registry.get(uid) is not None
                    and self.device_registry[uid].is_connected
                )
                total_count = len(full_uids)

                summary[simple_uid] = {
                    "vendor_id": sample_device.vendor_id,
                    "device_id": sample_device.device_id,
                    "vendor_name": sample_device.vendor_name or "Unknown",
                    "device_name": sample_device.device_name or "Unknown",
                    "connected_count": connected_count,
                    "total_seen_count": total_count,
                    "disconnected_count": total_count - connected_count,
                }

        return summary
