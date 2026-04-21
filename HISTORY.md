# History

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

## 0.3.1 (2026-04-21)
- CHANGED updated build backend and release tooling configuration.
- CHANGED refreshed Justfile workflows for environment, testing, and release checks.
- CHANGED updated packaging/verification helper scripts and dependency lock maintenance.
- CHANGED updated pre-commit toolchain versions.

## 0.3.0 (2026-03-13)
- CHANGED refactored package internals to a layered DDD structure under `usb_inspector.usb` (domain/application/infrastructure/interface).
- CHANGED internal legacy modules `db.py`, `update.py`, and `cli.py` were removed; CLI entry point now resolves to `usb_inspector.usb.interface.router:cli`.
- CHANGED `usb_inspector.monitor` remains available as a compatibility shim for `USBDeviceMonitor`.
- FIXED circular import issues in package initialization/import flow.
- ADDED layered test coverage for application and infrastructure modules plus import regression coverage.

## 0.2.2 (2025-12-04)
- ADDED tox and more test coverage

## 0.2.1 (2025-11-21)
- ADDED `port` to the device info
- CHANGED cleaned up logging on connect/disconnect descriptions

## 0.2.0 (2025-11-21)
- FIXED Connecting/Disconnecting the same physical device to the same port now correctly identifies the device as the same device on Windows/Linux.

## 0.1.9 (2025-11-21)
- FIXED Cached sql db lookup so it occurs only once.

## 0.1.8 (2025-11-20)
- FIXED turned default packaged logging to `ERROR`. Was `INFO`...Sorry!

## 0.1.7 (2025-11-13)
- FIXED `is_connected` bug introduced in last patch.
- ADDED improved tracking of devices allowing multiple of the same vendor/device ID to be connected.

## 0.1.6 (2025-11-13)
- FIXED `last_seen` timestamp for each device, only updates when connected/disonnected.

## 0.1.5 (2025-11-05)
- Locked `pandas` to version 2.3.3 for Raspberry Pi compatability (it pulls the pre-built wheel from piwheels.org)

## 0.1.4 (2025-11-05)
- Added `last_seen` timestamp for each device.

## 0.1.4 (2025-10-31)

- `update-db` cli command only adds new Vendors and Devices to the existing DB rather than requiring deletion and recreation of the DB.
- Track which devices are connected/disconnected.

## 0.1.2 (2025-10-30)

- Fix lookup error

## 0.1.1 (2025-10-30)

- Added `start` as an alias for `monitor`.

## 0.1.0 (2025-10-30)

- First release
