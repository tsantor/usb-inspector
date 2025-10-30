import usb.core


def test_win():
    # Find all USB devices
    devices = usb.core.find(find_all=True)

    if devices is None:
        assert devices is not None, (
            "No USB devices found (PyUSB might not be configured correctly with libusb backend)."
        )
    else:
        print("Connected USB Devices (Vendor ID: Product ID):")  # noqa: T201
        for dev in devices:
            # Print Vendor ID and Product ID in hexadecimal format
            print(f"- 0x{dev.idVendor:04x}:0x{dev.idProduct:04x}")  # noqa: T201
