from usb_inspector.usb.application.ports import USBDatabaseMaintenancePort


class USBMaintenanceService:
    def __init__(self, maintenance: USBDatabaseMaintenancePort):
        self._maintenance = maintenance

    def update_db(self) -> bool:
        return self._maintenance.update_usb_db()

    def delete_db(self) -> None:
        self._maintenance.delete_usb_db()

    def delete_data_file(self) -> None:
        self._maintenance.delete_data_file()
