from dataclasses import dataclass

USB_HEX_ID_LENGTH = 4


@dataclass(frozen=True)
class VendorId:
    value: str

    def __post_init__(self):
        normalized = str(self.value).lower()
        if len(normalized) != USB_HEX_ID_LENGTH:
            msg = "Vendor ID must be 4 hex characters"
            raise ValueError(msg)
        int(normalized, 16)
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class DeviceId:
    value: str

    def __post_init__(self):
        normalized = str(self.value).lower()
        if len(normalized) != USB_HEX_ID_LENGTH:
            msg = "Device ID must be 4 hex characters"
            raise ValueError(msg)
        int(normalized, 16)
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class SimpleUid:
    value: str


@dataclass(frozen=True)
class FullSystemUid:
    value: str


@dataclass(frozen=True)
class PortPath:
    value: str
