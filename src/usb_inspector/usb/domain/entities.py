from dataclasses import dataclass


@dataclass
class USBDeviceSnapshot:
    vendor_id: str
    device_id: str
    version: int | None
    bus: int | None
    address: int | None
    uid: str
    full_system_uid: str
    is_connected: bool
    last_seen: str
    port: str | None = None
    vendor_name: str | None = None
    vendor_name_short: str | None = None
    device_name: str | None = None
    serial: str | None = None
    topology_key: str | None = None

    def mark_connected(self, timestamp: str, bus: int | None, address: int | None):
        self.is_connected = True
        self.last_seen = timestamp
        self.bus = bus
        self.address = address

    def mark_disconnected(self, timestamp: str):
        self.is_connected = False
        self.last_seen = timestamp
