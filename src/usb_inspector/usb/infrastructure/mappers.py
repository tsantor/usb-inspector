def normalize_vendor_id(vendor_id) -> str:
    return str(vendor_id).lower()


def normalize_device_id(device_id) -> str | None:
    return str(device_id).lower() if device_id else None
