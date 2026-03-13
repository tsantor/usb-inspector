from importlib import resources

# Path to the usb.ids data file inside the package
# Usage: from usb_inspector.data_utils import data_file

data_file = resources.files("usb_inspector.data") / "usb.ids"
