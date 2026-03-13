class USBDomainError(Exception):
    """Base exception for USB domain errors."""


class InvalidVendorIdError(USBDomainError):
    """Raised when a vendor id is invalid."""


class InvalidDeviceIdError(USBDomainError):
    """Raised when a device id is invalid."""
