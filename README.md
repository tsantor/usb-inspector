# USB Inspector

![Coverage](https://img.shields.io/badge/coverage-82.27%25-green)

## Overview

A simple package that leverages `pyusb` and allows you to lookup USB vendor and device IDs and get back a human readable vendor and device name.
It includes ability to manually update the USB DB without installing a new version of `usb-inspector`.

## Installation

```bash
uv add usb-inspector
# via pip
python3 -m pip install usb-inspector
```

**IMPORTANT**: On Windows ensure you have `libusb-1.0.dll` (64bit) in `C:\Windows\System32` or you will get a `NoBackendError`. You can get it from [here](https://libusb.info/).

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
import asyncio

from usb_inspector.monitor import USBDeviceMonitor

async def main():
    usb_monitor = USBDeviceMonitor(poll_interval=1.0)
    monitor_task = asyncio.create_task(usb_monitor.run())  # or usb_monitor.start()
    await asyncio.sleep(10)
    await usb_monitor.stop()
    await monitor_task

asyncio.run(main())
```

## Issues

If you experience any issues, please create an [issue](https://bitbucket.org/xstudios/usb-inspector/issues) on Bitbucket.


## Development

To get a list of all commands with descriptions simply run `just`.

```bash
just env
just pip-install-editable
```

## Testing

```bash
just pytest
just coverage
just open-coverage
```
