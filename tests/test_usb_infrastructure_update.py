from pathlib import Path

import pandas as pd
import pytest

from usb_inspector.usb.infrastructure.repository import USBDatabaseMaintenanceRepository
import usb_inspector.usb.infrastructure.repository as repository_module


@pytest.fixture
def maintenance_repo(tmp_path, monkeypatch):
    db_path = tmp_path / "usb_data.db"
    data_path = tmp_path / "usb.ids"
    monkeypatch.setattr(repository_module, "usb_db", str(db_path))
    monkeypatch.setattr(repository_module, "data_file", data_path)
    return USBDatabaseMaintenanceRepository(), db_path, data_path


def test_create_database_schema_creates_tables(maintenance_repo):
    repo, db_path, _ = maintenance_repo

    repo.create_database_schema()

    assert db_path.exists()
    conn = repository_module.sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vendors'")
    assert cur.fetchone() is not None
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    assert cur.fetchone() is not None
    conn.close()


def test_parse_usb_ids_to_dataframes_parses_vendor_and_device(maintenance_repo):
    repo, _, _ = maintenance_repo
    data = """\
# comment
1A40  Terminus Technology Inc.
\t0801  USB 2.0 Hub
"""

    vendors_df, devices_df = repo.parse_usb_ids_to_dataframes(data)

    assert vendors_df.to_dict("records") == [
        {"vendor_id": "1A40", "vendor_name": "Terminus Technology Inc."}
    ]
    assert devices_df.to_dict("records") == [
        {
            "device_id": "0801",
            "device_name": "USB 2.0 Hub",
            "vendor_id": "1A40",
        }
    ]


def test_update_existing_database_inserts_only_new_rows(maintenance_repo):
    repo, db_path, _ = maintenance_repo
    repo.create_database_schema()

    vendors_df = pd.DataFrame(
        [
            {"vendor_id": "1A40", "vendor_name": "Terminus Technology Inc."},
            {"vendor_id": "abcd", "vendor_name": "Example Vendor"},
        ]
    )
    devices_df = pd.DataFrame(
        [
            {
                "device_id": "0801",
                "device_name": "USB 2.0 Hub",
                "vendor_id": "1A40",
            },
            {
                "device_id": "0001",
                "device_name": "Example Device",
                "vendor_id": "abcd",
            },
        ]
    )

    repo.update_existing_database(vendors_df, devices_df)
    repo.update_existing_database(vendors_df, devices_df)

    conn = repository_module.sqlite3.connect(db_path)
    vendors = pd.read_sql("SELECT * FROM vendors", conn)
    devices = pd.read_sql("SELECT * FROM devices", conn)
    conn.close()

    assert len(vendors) == 2
    assert len(devices) == 2


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


def test_update_usb_db_download_and_persist_success(maintenance_repo, monkeypatch):
    repo, db_path, data_path = maintenance_repo
    sample_usb_ids = b"1A40  Terminus Technology Inc.\n\t0801  USB 2.0 Hub\n"

    def _fake_get(_url, timeout):
        assert timeout == 5
        return _FakeResponse(sample_usb_ids)

    monkeypatch.setattr(repository_module.requests, "get", _fake_get)

    result = repo.update_usb_db()

    assert result is True
    assert data_path.exists()
    assert db_path.exists()


def test_update_usb_db_returns_false_on_download_error(maintenance_repo, monkeypatch):
    repo, _, _ = maintenance_repo

    def _raise_request_error(_url, timeout):
        raise repository_module.requests.exceptions.RequestException("network down")

    monkeypatch.setattr(repository_module.requests, "get", _raise_request_error)

    result = repo.update_usb_db()

    assert result is False
