import asyncio
import json
from unittest.mock import MagicMock

from click.testing import CliRunner

import usb_inspector.usb.interface.dependencies as deps
from usb_inspector.usb.application.service import USBMonitoringService
from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository
from usb_inspector.usb.infrastructure.repository import USBDatabaseMaintenanceRepository
from usb_inspector.usb.interface import router


class _FakeLoop:
    def __init__(self):
        self.closed = False
        self.stopped = False

    def add_signal_handler(self, *_args, **_kwargs):
        return None

    def run_until_complete(self, _coroutine):
        _coroutine.close()
        raise asyncio.CancelledError

    def close(self):
        self.closed = True

    def stop(self):
        self.stopped = True


class _FakeEnumerator:
    def iter_devices(self):
        return []


class _FakeLookup:
    def lookup(self, _vendor_id, _device_id=None):
        return None


def test_dependencies_return_expected_types():
    monitoring = deps.get_monitoring_service()
    details = deps.get_details_repository()
    maintenance = deps.get_maintenance_repository()

    assert isinstance(monitoring, USBMonitoringService)
    assert isinstance(details, SQLiteUSBDetailsRepository)
    assert isinstance(maintenance, USBDatabaseMaintenanceRepository)


def test_interface_package_exports_cli():
    import usb_inspector.usb.interface as interface_package  # noqa: PLC0415

    assert interface_package.cli is not None


def test_lookup_command_outputs_json(monkeypatch):
    fake_details_repo = MagicMock()
    fake_details_repo.lookup.return_value = {
        "vendor_id": "1a40",
        "vendor_name": "Terminus Technology Inc.",
        "device_id": "0801",
        "device_name": "USB 2.0 Hub",
    }
    monkeypatch.setattr(router, "get_details_repository", lambda: fake_details_repo)

    result = CliRunner().invoke(router.cli, ["lookup", "-v", "1A40", "-d", "0801"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["vendor_name"] == "Terminus Technology Inc."


def test_lookup_command_not_found_message(monkeypatch):
    fake_details_repo = MagicMock()
    fake_details_repo.lookup.return_value = None
    monkeypatch.setattr(router, "get_details_repository", lambda: fake_details_repo)

    result = CliRunner().invoke(router.cli, ["lookup", "-v", "0000"])

    assert result.exit_code == 0
    assert "No details found" in result.output


def test_update_delete_commands_invoke_maintenance_repo(monkeypatch):
    maintenance = MagicMock()
    monkeypatch.setattr(router, "get_maintenance_repository", lambda: maintenance)
    runner = CliRunner()

    assert runner.invoke(router.cli, ["update-db"]).exit_code == 0
    assert runner.invoke(router.cli, ["delete-db"]).exit_code == 0
    assert runner.invoke(router.cli, ["delete-data"]).exit_code == 0

    maintenance.update_usb_db.assert_called_once()
    maintenance.delete_usb_db.assert_called_once()
    maintenance.delete_data_file.assert_called_once()


def test_monitor_command_handles_cancelled_loop(monkeypatch):
    fake_loop = _FakeLoop()
    fake_service = MagicMock()
    monkeypatch.setattr(router.asyncio, "get_event_loop", lambda: fake_loop)
    monkeypatch.setattr(router, "get_monitoring_service", lambda poll_interval=1.0: fake_service)

    result = CliRunner().invoke(router.cli, ["monitor"])

    assert result.exit_code == 0
    assert fake_loop.closed is True
