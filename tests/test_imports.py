def test_package_import_exposes_usb_device_monitor():
    import usb_inspector

    assert usb_inspector.USBDeviceMonitor is not None
