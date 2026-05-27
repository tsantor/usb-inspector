import importlib

import pytest


def test_package_exposes_application_service():
    import usb_inspector  # noqa: PLC0415

    assert usb_inspector.USBMonitoringService is not None


def test_package_exposes_details_lookup_port():
    import usb_inspector  # noqa: PLC0415

    assert usb_inspector.USBDetailsLookupPort is not None


def test_package_exposes_factory():
    import usb_inspector  # noqa: PLC0415

    assert usb_inspector.create_usb_monitoring_service is not None


def test_legacy_monitor_import_is_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("usb_inspector.monitor")
