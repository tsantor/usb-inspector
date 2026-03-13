import logging
from typing import TYPE_CHECKING

from .data_utils import data_file
from .paths import usb_db

# Basic logger setup; users of this package can configure logging as needed
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

if not usb_db.exists():  # pragma: no cover
    # If the database does not exist, create it by updating from usb.ids
    from usb_inspector.update import update_usb_db

    update_usb_db()

if TYPE_CHECKING:
    from .monitor import USBDeviceMonitor


def __getattr__(name: str):
    if name == "USBDeviceMonitor":
        from .monitor import USBDeviceMonitor

        return USBDeviceMonitor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "0.2.2"

__all__ = ["USBDeviceMonitor"]
