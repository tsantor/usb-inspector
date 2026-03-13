from usb_inspector.usb.infrastructure.factory import create_usb_monitoring_service
from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository
from usb_inspector.usb.infrastructure.repository import USBDatabaseMaintenanceRepository


def get_monitoring_service(poll_interval: float = 1.0):
    return create_usb_monitoring_service(poll_interval=poll_interval)


def get_details_repository():
    return SQLiteUSBDetailsRepository()


def get_maintenance_repository():
    return USBDatabaseMaintenanceRepository()
