import logging
from importlib import resources
from pathlib import Path

import platformdirs

# Basic logger setup; users of this package can configure logging as needed
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


data_file = resources.files("usb_inspector.data") / "usb.ids"
# usb_db = resources.files("usb_inspector.data") / "usb_data.db"

data_dir = Path(
    platformdirs.user_data_dir(
        appname="usb-inspector",
        appauthor="xstudios",
        ensure_exists=True,
    )
)
usb_db = data_dir / "usb_data.db"
# click.echo(f"Using USB database at: {usb_db}")

if not usb_db.exists():
    # If the database does not exist, create it by updating from usb.ids
    from usb_inspector.update import update_usb_db

    update_usb_db()


__version__ = "0.1.4"
