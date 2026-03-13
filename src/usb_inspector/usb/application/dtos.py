from dataclasses import dataclass


@dataclass
class USBDeviceDTO:
    device_id: str
    vendor_id: str
    version: int | None
    bus: int | None
    port: str | None
    address: int | None
    uid: str
    full_system_uid: str
    is_connected: bool
    last_seen: str
    vendor_name: str | None = None
    vendor_name_short: str | None = None
    device_name: str | None = None
    serial: str | None = None
