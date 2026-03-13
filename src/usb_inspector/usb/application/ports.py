from collections.abc import Iterable
from typing import Any
from typing import Protocol


class USBEnumeratorPort(Protocol):
    def iter_devices(self) -> Iterable[Any]:
        """Return all currently visible USB devices."""


class USBDetailsLookupPort(Protocol):
    def lookup(self, vendor_id: str, device_id: str | None = None) -> dict | None:
        """Lookup vendor/device details."""


class USBDatabaseMaintenancePort(Protocol):
    def delete_usb_db(self) -> None:
        """Delete USB sqlite DB."""

    def delete_data_file(self) -> None:
        """Delete downloaded usb.ids file."""

    def update_usb_db(self) -> bool:
        """Update USB sqlite DB from usb.ids data."""
