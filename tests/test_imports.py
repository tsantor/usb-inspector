def test_package_import_exposes_usb_device_monitor():
    import usb_inspector  # noqa: PLC0415

    assert usb_inspector.USBDeviceMonitor is not None
