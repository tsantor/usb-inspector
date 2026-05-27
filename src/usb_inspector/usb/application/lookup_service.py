from usb_inspector.usb.application.ports import USBDetailsLookupPort


class USBLookupService:
    def __init__(self, details_lookup: USBDetailsLookupPort):
        self._details_lookup = details_lookup

    def lookup(self, vendor_id: str, device_id: str | None = None) -> dict | None:
        return self._details_lookup.lookup(vendor_id, device_id)
