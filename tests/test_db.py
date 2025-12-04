from unittest.mock import patch

from usb_inspector.db import delete_data_file
from usb_inspector.db import delete_usb_db
from usb_inspector.db import lookup_usb_details


def test_delete_usb_db(tmp_path):
    """Test deleting the USB database file."""
    db_file = tmp_path / "usb_inspector.db"
    db_file.touch()

    # Patch the usb_db variable in the usb_inspector.db module
    with patch("usb_inspector.db.usb_db", str(db_file)):
        assert db_file.exists()
        delete_usb_db()
        assert not db_file.exists()


def test_delete_data_file(tmp_path):
    """Test deleting the usb.ids data file."""
    data_file = tmp_path / "usb.ids"
    data_file.touch()

    # Patch the data_file variable in the usb_inspector.db module
    with patch("usb_inspector.db.data_file", str(data_file)):
        assert data_file.exists()
        delete_data_file()
        assert not data_file.exists()


def test_lookup_usb_details():
    """Test the lookup_usb_details method."""
    details = lookup_usb_details("1a40", "0801")
    assert details["vendor_name"] == "Terminus Technology Inc."
    assert details["device_name"] == "USB 2.0 Hub"


def test_lookup_usb_details_with_vendor_id():
    """Test the lookup_usb_details method."""
    details = lookup_usb_details("1a40")
    assert details["vendor_name"] == "Terminus Technology Inc."
    assert details["device_id"] is None
    assert details["device_name"] is None


def test_lookup_usb_details_with_invalid_vendor_id():
    """Test the lookup_usb_details method."""
    details = lookup_usb_details("0000")
    assert details is None
