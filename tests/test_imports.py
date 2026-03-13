def test_package_import_exposes_usb_device_monitor():
    import usb_inspector  # noqa: PLC0415

    assert usb_inspector.USBDeviceMonitor is not None


def test_legacy_monitor_import_emits_warning():
    import importlib  # noqa: PLC0415
    import sys  # noqa: PLC0415
    import warnings  # noqa: PLC0415

    from usb_inspector._compat_warnings import LegacyImportWarning  # noqa: PLC0415

    sys.modules.pop("usb_inspector.monitor", None)

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        importlib.import_module("usb_inspector.monitor")

    assert any(
        isinstance(record.message, LegacyImportWarning) for record in records
    )
