from pathlib import Path

import platformdirs

data_dir = Path(
    platformdirs.user_data_dir(
        appname="usb-inspector",
        appauthor="xstudios",
        ensure_exists=True,
    )
)
usb_db = data_dir / "usb_data.db"
