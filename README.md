# USB Inspector

![Coverage](https://img.shields.io/badge/coverage-0%25-brightgreen)

## Overview

A simple package that allows you to lookup USB vendor and device IDs and get back a human readable vendor and device name.
It includes ability to manually update the USB DB without installing a new version of `usb-inspector`.

## Installation

```bash
python3 -m pip install usb-inspector
```

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

## Issues

If you experience any issues, please create an [issue](https://github.com/tsantor/usb-inspector/issues) on Github.

## Example Usage

Command Line:
```bash
usb-inspector lookup --vendor-id 1A40
usb-inspector lookup --vendor-id 1A40 --device-id 0801

usb-inspector update-db
usb-inspector delete-db
```
