# USB Inspector

![Coverage](https://img.shields.io/badge/coverage-0%25-brightgreen)

## Overview

A simple python package to gather host information from Windows, Mac and Linux. Returns host data as dicts to be used internally or sent to front-end dashboard applications as JSON.

## Installation

Install Host Info:

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

```python
from usb_inspector import get_device_info
from usb_inspector import get_health_info

print(get_device_info())
print(get_health_info())

# You can also call individual methods:
from usb_inspector import get_cpu_info
from usb_inspector import get_datetime_info
from usb_inspector import get_disk_info
from usb_inspector import get_gpu_info
from usb_inspector import get_mem_info
from usb_inspector import get_network_info
from usb_inspector import get_os_info
from usb_inspector import get_platform_info
from usb_inspector import get_uptime_info
```

## Use with Caution!

To control system services we need to allow passwordless use of specific executables. You should know the security implications of doing this so **use at your own risk**.

### Linux (Ubuntu)

Use `sudo visudo` to add the following lines:

```ini
%sudo ALL=(ALL) NOPASSWD: /usr/sbin/ufw
%sudo ALL=(ALL) NOPASSWD: /usr/sbin/dmidecode
```

Save and exit the file (`:wq!`). Then do:
