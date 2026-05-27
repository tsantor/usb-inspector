from usb_inspector.usb.application.lookup_service import USBLookupService
from usb_inspector.usb.application.maintenance_service import USBMaintenanceService
from usb_inspector.usb.application.service import USBMonitoringService
from usb_inspector.usb.infrastructure.repository import PyUSBEnumerator
from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository
from usb_inspector.usb.infrastructure.repository import USBDatabaseMaintenanceRepository


def create_usb_monitoring_service(poll_interval: float = 1.0) -> USBMonitoringService:
    return USBMonitoringService(
        enumerator=PyUSBEnumerator(),
        details_lookup=SQLiteUSBDetailsRepository(),
        poll_interval=poll_interval,
    )


def create_usb_lookup_service() -> USBLookupService:
    return USBLookupService(details_lookup=SQLiteUSBDetailsRepository())


def create_usb_maintenance_service() -> USBMaintenanceService:
    return USBMaintenanceService(maintenance=USBDatabaseMaintenanceRepository())
