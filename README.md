# USB Inspector

![Coverage](https://img.shields.io/badge/coverage-57%25-brightgreen)

## Overview

A simple package that leverages `pyusb` and allows you to lookup USB vendor and device IDs and get back a human readable vendor and device name.
It includes ability to manually update the USB DB without installing a new version of `usb-inspector`.

## Installation

```bash
python3 -m pip install usb-inspector
```

**IMPORTANT**: On Windows ensure you have `libusb-1.0.dll` in `C:\Windows\System32` or you will get a `NoBackendError`. You can get them from [here](https://libusb.info/).

## Example Usage

Command Line:
```bash
usb-inspector lookup --vendor-id 1A40
usb-inspector lookup --vendor-id 1A40 --device-id 0801

# To manually update the USB DB
usb-inspector delete-data
usb-inspector update-db
```

```python
from usb_inspector.monitor import USBDeviceMonitor

usb_monitor = USBDeviceMonitor(poll_interval=1.0)
usb_monitor.monitor()
# Do stuff
...
usb_monitor.stop()
```

## Issues

If you experience any issues, please create an [issue](https://bitbucket.org/xstudios/usb-inspector/issues) on Bitbucket.


## Development

To get a list of all commands with descriptions simply run `make`.

```bash
make env
make pip_install_editable
```

## Testing

```bash
make pytest
make coverage
make open_coverage
```
