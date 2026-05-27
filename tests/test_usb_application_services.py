from usb_inspector.usb.application.lookup_service import USBLookupService
from usb_inspector.usb.application.maintenance_service import USBMaintenanceService


class _FakeLookup:
    def __init__(self, result):
        self._result = result

    def lookup(self, vendor_id, device_id=None):
        return self._result


class _FakeMaintenance:
    def __init__(self):
        self.updated = False
        self.db_deleted = False
        self.data_deleted = False

    def update_usb_db(self) -> bool:
        self.updated = True
        return True

    def delete_usb_db(self) -> None:
        self.db_deleted = True

    def delete_data_file(self) -> None:
        self.data_deleted = True


def test_lookup_service_returns_result_from_port():
    expected = {"vendor_id": "1a40", "vendor_name": "Terminus Technology Inc."}
    service = USBLookupService(details_lookup=_FakeLookup(expected))
    assert service.lookup("1a40") == expected


def test_lookup_service_returns_none_for_unknown_vendor():
    service = USBLookupService(details_lookup=_FakeLookup(None))
    assert service.lookup("0000") is None


def test_lookup_service_passes_device_id_to_port():
    expected = {"vendor_id": "1a40", "device_id": "0801", "device_name": "USB 2.0 Hub"}
    service = USBLookupService(details_lookup=_FakeLookup(expected))
    assert service.lookup("1a40", "0801") == expected


def test_maintenance_service_update_db_delegates_to_port():
    fake = _FakeMaintenance()
    service = USBMaintenanceService(maintenance=fake)
    result = service.update_db()
    assert result is True
    assert fake.updated is True


def test_maintenance_service_delete_db_delegates_to_port():
    fake = _FakeMaintenance()
    service = USBMaintenanceService(maintenance=fake)
    service.delete_db()
    assert fake.db_deleted is True


def test_maintenance_service_delete_data_file_delegates_to_port():
    fake = _FakeMaintenance()
    service = USBMaintenanceService(maintenance=fake)
    service.delete_data_file()
    assert fake.data_deleted is True
