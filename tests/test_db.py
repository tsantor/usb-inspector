from unittest.mock import patch

from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository
from usb_inspector.usb.infrastructure.repository import USBDatabaseMaintenanceRepository


def test_delete_usb_db(tmp_path):
    """Test deleting the USB database file."""
    db_file = tmp_path / "usb_inspector.db"
    db_file.touch()

    with patch("usb_inspector.usb.infrastructure.repository.usb_db", str(db_file)):
        assert db_file.exists()
        USBDatabaseMaintenanceRepository().delete_usb_db()
        assert not db_file.exists()


def test_delete_data_file(tmp_path):
    """Test deleting the usb.ids data file."""
    data_file = tmp_path / "usb.ids"
    data_file.touch()

    with patch("usb_inspector.usb.infrastructure.repository.data_file", str(data_file)):
        assert data_file.exists()
        USBDatabaseMaintenanceRepository().delete_data_file()
        assert not data_file.exists()


def test_lookup_usb_details():
    """Test the lookup method."""
    details = SQLiteUSBDetailsRepository().lookup("1a40", "0801")
    assert details["vendor_name"] == "Terminus Technology Inc."
    assert details["device_name"] == "USB 2.0 Hub"


def test_lookup_usb_details_with_vendor_id():
    """Test the lookup method with vendor ID only."""
    details = SQLiteUSBDetailsRepository().lookup("1a40")
    assert details["vendor_name"] == "Terminus Technology Inc."
    assert details["device_id"] is None
    assert details["device_name"] is None


def test_lookup_usb_details_with_invalid_vendor_id():
    """Test the lookup method with an unknown vendor ID."""
    details = SQLiteUSBDetailsRepository().lookup("0000")
    assert details is None
