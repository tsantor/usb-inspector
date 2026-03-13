from unittest.mock import patch

from usb_inspector.usb.infrastructure.repository import delete_data_file
from usb_inspector.usb.infrastructure.repository import delete_usb_db
from usb_inspector.usb.infrastructure.repository import lookup_usb_details


def test_infrastructure_lookup_smoke():
    details = lookup_usb_details("1a40", "0801")
    assert details is not None
    assert details["vendor_name"] == "Terminus Technology Inc."


def test_infrastructure_delete_functions_smoke(tmp_path):
    db_file = tmp_path / "usb_data.db"
    db_file.touch()
    data_file = tmp_path / "usb.ids"
    data_file.touch()

    with patch("usb_inspector.usb.infrastructure.repository.usb_db", str(db_file)):
        assert delete_usb_db() is None
        assert not db_file.exists()

    with patch("usb_inspector.usb.infrastructure.repository.data_file", data_file):
        assert delete_data_file() is None
        assert not data_file.exists()
