# History

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).

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
