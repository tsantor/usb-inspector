import logging
from importlib import resources

# Basic logger setup; users of this package can configure logging as needed
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

__version__ = "0.1.1"

data_file = resources.files("usb_inspector.data") / "usb.ids"
usb_db = resources.files("usb_inspector.data") / "usb_data.db"
