import logging
from typing import TYPE_CHECKING

from .paths import usb_db

# Basic logger setup; users of this package can configure logging as needed
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if not usb_db.exists():  # pragma: no cover
    # If the database does not exist, create it by updating from usb.ids
    from usb_inspector.usb.infrastructure.repository import update_usb_db

    update_usb_db()

if TYPE_CHECKING:
    from .monitor import USBDeviceMonitor


def __getattr__(name: str):
    if name == "USBDeviceMonitor":
        from .monitor import USBDeviceMonitor  # noqa: PLC0415

        return USBDeviceMonitor
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__version__ = "0.2.2"

__all__ = ["USBDeviceMonitor"]
