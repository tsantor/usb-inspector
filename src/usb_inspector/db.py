import logging
import sqlite3
from pathlib import Path

import click

from usb_inspector import data_file
from usb_inspector import usb_db

logger = logging.getLogger(__name__)


def lookup_usb_details(vendor_id, device_id=None) -> dict | None:
    """
    Looks up vendor and device details in the SQLite database using normalized
    tables.

    :param vendor_id: The 4-digit hexadecimal Vendor ID (e.g., '03e7').
    :param device_id: The 4-digit hexadecimal Device ID (e.g., '2150').
    :return: A dictionary containing the details or None if not found.
    """
    vendor_id = str(vendor_id).lower()
    device_id = str(device_id).lower() if device_id else None

    conn = None
    try:
        conn = sqlite3.connect(usb_db)
        cursor = conn.cursor()

        if device_id:
            # Try to find an exact match for both vendor and device using JOIN
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
        else:
            # Only vendor_id provided - lookup in vendors table
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

        # No vendor match found at all
        return None

    except sqlite3.Error:
        logger.exception("Database error during USB lookup")
        return None
    finally:
        if conn:
            conn.close()


def delete_usb_db():
    """Deletes the existing USB database file."""
    file = Path(usb_db)
    if file.exists():
        file.unlink()


def delete_data_file():
    """Deletes the existing usb.ids file if it exists."""
    file = Path(data_file)
    if file.exists():
        file.unlink()
