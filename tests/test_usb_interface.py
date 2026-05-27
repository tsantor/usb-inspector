import asyncio
import json
from unittest.mock import MagicMock

from click.testing import CliRunner

from usb_inspector.usb.presentation.cli import cli


class _FakeLoop:
    def __init__(self):
        self.closed = False

    def add_signal_handler(self, *_args, **_kwargs):
        return None

    def run_until_complete(self, _coroutine):
        _coroutine.close()
        raise asyncio.CancelledError

    def close(self):
        self.closed = True


def _services(**overrides):
    """Build a minimal services dict for CLI tests."""
    defaults = {
        "lookup_service": MagicMock(),
        "maintenance_service": MagicMock(),
        "monitoring_service": MagicMock(),
    }
    defaults.update(overrides)
    return defaults


def test_interface_package_exports_cli():
    import usb_inspector.usb.presentation as presentation_package  # noqa: PLC0415

    assert presentation_package.cli is not None


def test_lookup_command_outputs_json():
    fake_lookup = MagicMock()
    fake_lookup.lookup.return_value = {
        "vendor_id": "1a40",
        "vendor_name": "Terminus Technology Inc.",
        "device_id": "0801",
        "device_name": "USB 2.0 Hub",
    }

    result = CliRunner().invoke(
        cli, ["lookup", "-v", "1A40", "-d", "0801"], obj=_services(lookup_service=fake_lookup)
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["vendor_name"] == "Terminus Technology Inc."


def test_lookup_command_not_found_message():
    fake_lookup = MagicMock()
    fake_lookup.lookup.return_value = None

    result = CliRunner().invoke(
        cli, ["lookup", "-v", "0000"], obj=_services(lookup_service=fake_lookup)
    )

    assert result.exit_code == 0
    assert "No details found" in result.output


def test_update_delete_commands_invoke_maintenance_service():
    fake_maintenance = MagicMock()
    runner = CliRunner()

    assert runner.invoke(cli, ["update-db"], obj=_services(maintenance_service=fake_maintenance)).exit_code == 0
    assert runner.invoke(cli, ["delete-db"], obj=_services(maintenance_service=fake_maintenance)).exit_code == 0
    assert runner.invoke(cli, ["delete-data"], obj=_services(maintenance_service=fake_maintenance)).exit_code == 0

    fake_maintenance.update_db.assert_called_once()
    fake_maintenance.delete_db.assert_called_once()
    fake_maintenance.delete_data_file.assert_called_once()


def test_monitor_command_handles_cancelled_loop(monkeypatch):
    fake_loop = _FakeLoop()
    fake_service = MagicMock()
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: fake_loop)

    result = CliRunner().invoke(
        cli, ["monitor"], obj=_services(monitoring_service=fake_service)
    )

    assert result.exit_code == 0
    assert fake_loop.closed is True
