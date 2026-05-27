import asyncio
import importlib
import json
from unittest.mock import MagicMock

from click.testing import CliRunner

from usb_inspector.usb.application.service import USBMonitoringService
from usb_inspector.usb.infrastructure.repository import SQLiteUSBDetailsRepository
from usb_inspector.usb.infrastructure.repository import USBDatabaseMaintenanceRepository

# presentation/__init__.py binds 'cli' to the Click group, shadowing the cli.py
# module on attribute lookup — use importlib to get the actual module.
cli_module = importlib.import_module("usb_inspector.usb.presentation.cli")


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


def test_cli_imports_infrastructure_directly():
    assert cli_module.create_usb_monitoring_service is not None
    assert cli_module.SQLiteUSBDetailsRepository is SQLiteUSBDetailsRepository
    assert cli_module.USBDatabaseMaintenanceRepository is USBDatabaseMaintenanceRepository


def test_create_usb_monitoring_service_returns_service():
    service = cli_module.create_usb_monitoring_service()
    assert isinstance(service, USBMonitoringService)


def test_interface_package_exports_cli():
    import usb_inspector.usb.presentation as presentation_package  # noqa: PLC0415

    assert presentation_package.cli is not None


def test_lookup_command_outputs_json(monkeypatch):
    fake_details_repo = MagicMock()
    fake_details_repo.lookup.return_value = {
        "vendor_id": "1a40",
        "vendor_name": "Terminus Technology Inc.",
        "device_id": "0801",
        "device_name": "USB 2.0 Hub",
    }
    monkeypatch.setattr(cli_module, "SQLiteUSBDetailsRepository", lambda: fake_details_repo)

    result = CliRunner().invoke(cli_module.cli, ["lookup", "-v", "1A40", "-d", "0801"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["vendor_name"] == "Terminus Technology Inc."


def test_lookup_command_not_found_message(monkeypatch):
    fake_details_repo = MagicMock()
    fake_details_repo.lookup.return_value = None
    monkeypatch.setattr(cli_module, "SQLiteUSBDetailsRepository", lambda: fake_details_repo)

    result = CliRunner().invoke(cli_module.cli, ["lookup", "-v", "0000"])

    assert result.exit_code == 0
    assert "No details found" in result.output


def test_update_delete_commands_invoke_maintenance_repo(monkeypatch):
    maintenance = MagicMock()
    monkeypatch.setattr(cli_module, "USBDatabaseMaintenanceRepository", lambda: maintenance)
    runner = CliRunner()

    assert runner.invoke(cli_module.cli, ["update-db"]).exit_code == 0
    assert runner.invoke(cli_module.cli, ["delete-db"]).exit_code == 0
    assert runner.invoke(cli_module.cli, ["delete-data"]).exit_code == 0

    maintenance.update_usb_db.assert_called_once()
    maintenance.delete_usb_db.assert_called_once()
    maintenance.delete_data_file.assert_called_once()


def test_monitor_command_handles_cancelled_loop(monkeypatch):
    fake_loop = _FakeLoop()
    fake_service = MagicMock()
    monkeypatch.setattr(cli_module.asyncio, "get_event_loop", lambda: fake_loop)
    monkeypatch.setattr(cli_module, "create_usb_monitoring_service", lambda poll_interval=1.0: fake_service)

    result = CliRunner().invoke(cli_module.cli, ["monitor"])

    assert result.exit_code == 0
    assert fake_loop.closed is True
