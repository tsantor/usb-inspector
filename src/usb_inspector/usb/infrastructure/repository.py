import logging
import re
import sqlite3
from pathlib import Path

import chardet
import pandas as pd
import requests
import usb.core

from usb_inspector.usb.infrastructure.mappers import normalize_device_id
from usb_inspector.usb.infrastructure.mappers import normalize_vendor_id
from usb_inspector.usb.infrastructure.paths import data_file
from usb_inspector.usb.infrastructure.paths import usb_db

logger = logging.getLogger(__name__)


class PyUSBEnumerator:
    def iter_devices(self):
        return usb.core.find(find_all=True)


class SQLiteUSBDetailsRepository:
    def lookup(self, vendor_id, device_id=None) -> dict | None:
        if not usb_db.exists():
            USBDatabaseMaintenanceRepository().update_usb_db()

        vendor_id = normalize_vendor_id(vendor_id)
        device_id = normalize_device_id(device_id)

        conn = None
        try:
            conn = sqlite3.connect(usb_db)
            cursor = conn.cursor()

            if device_id:
                query = """
                SELECT v.vendor_name, d.device_name
                FROM vendors v
                LEFT JOIN devices d ON v.vendor_id = d.vendor_id AND d.device_id = ?
                WHERE v.vendor_id = ?
                LIMIT 1;
                """
                cursor.execute(query, (device_id, vendor_id))
                result = cursor.fetchone()

                if result:
                    return {
                        "vendor_id": vendor_id,
                        "vendor_name": result[0],
                        "device_id": device_id,
                        "device_name": result[1],
                    }

            query = """
            SELECT vendor_name
            FROM vendors
            WHERE vendor_id = ?
            LIMIT 1;
            """
            cursor.execute(query, (vendor_id,))
            result = cursor.fetchone()

            if result:
                return {
                    "vendor_id": vendor_id,
                    "vendor_name": result[0],
                    "device_id": None,
                    "device_name": None,
                }

            return result

        except sqlite3.Error:  # pragma: no cover
            logger.exception("Database error during USB lookup")
            return None
        finally:
            if conn:
                conn.close()


class USBDatabaseMaintenanceRepository:
    def delete_usb_db(self):
        file = Path(usb_db)
        if file.exists():
            file.unlink()

    def delete_data_file(self):
        file = Path(data_file)
        if file.exists():
            file.unlink()

    def create_database_schema(self):
        conn = sqlite3.connect(usb_db)
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                vendor_id TEXT PRIMARY KEY,
                vendor_name TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT NOT NULL,
                device_name TEXT NOT NULL,
                vendor_id TEXT NOT NULL,
                FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id)
            )
            """
        )

        conn.commit()
        conn.close()

    def update_existing_database(
        self, vendors_df: pd.DataFrame, devices_df: pd.DataFrame
    ):
        conn = sqlite3.connect(usb_db)
        conn.execute("PRAGMA foreign_keys = ON")

        existing_vendors = pd.read_sql("SELECT * FROM vendors", conn)
        existing_devices = pd.read_sql("SELECT * FROM devices", conn)

        new_vendors = vendors_df[
            ~vendors_df["vendor_id"].isin(existing_vendors["vendor_id"])
        ]

        new_devices = devices_df[
            ~devices_df[["device_id", "vendor_id"]]
            .apply(tuple, axis=1)
            .isin(existing_devices[["device_id", "vendor_id"]].apply(tuple, axis=1))
        ]

        if not new_vendors.empty:
            new_vendors.to_sql("vendors", conn, if_exists="append", index=False)

        if not new_devices.empty:
            new_devices.to_sql("devices", conn, if_exists="append", index=False)

        conn.commit()
        conn.close()

    def parse_usb_ids_to_dataframes(self, data_string):
        lines = data_string.splitlines()
        vendors = []
        devices = []
        current_vendor_id = None

        vendor_pattern = re.compile(r"^([0-9a-fA-F]{4})\s+(.*)$")
        device_pattern = re.compile(r"^\t([0-9a-fA-F]{4})\s+(.*)$")

        for line in lines:
            if not line or line.startswith("#"):
                continue

            vendor_match = vendor_pattern.match(line)
            if vendor_match:
                current_vendor_id = vendor_match.group(1)
                current_vendor_name = vendor_match.group(2).strip()
                vendors.append(
                    {
                        "vendor_id": current_vendor_id,
                        "vendor_name": current_vendor_name,
                    }
                )
                continue

            if current_vendor_id:
                device_match = device_pattern.match(line)
                if device_match:
                    device_id = device_match.group(1)
                    device_name = device_match.group(2).strip()
                    devices.append(
                        {
                            "device_id": device_id,
                            "device_name": device_name,
                            "vendor_id": current_vendor_id,
                        }
                    )
                    continue

        vendors_df = pd.DataFrame(vendors)
        devices_df = pd.DataFrame(devices)
        return vendors_df, devices_df

    def update_usb_db(self) -> bool:
        url = "http://www.linux-usb.org/usb.ids"

        self.create_database_schema()

        if not data_file.exists():
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                with data_file.open("wb") as f:
                    f.write(response.content)
            except requests.exceptions.RequestException:
                logger.exception("Failed to download usb.ids")
                return False

        with data_file.open("rb") as f:
            raw_data = f.read()
            detected_encoding = chardet.detect(raw_data)["encoding"]

        with data_file.open("r", encoding=detected_encoding) as f:
            data = f.read()

        vendors_df, devices_df = self.parse_usb_ids_to_dataframes(data)
        self.update_existing_database(vendors_df, devices_df)
        return True
