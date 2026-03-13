#!/usr/bin/env python3
"""Build artifact smoke test: install built wheel in a clean venv and import package."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PACKAGE_DIR = "usb_inspector"


def run(cmd: list[str]) -> None:
    # Commands are constructed internally and not user supplied.
    subprocess.run(cmd, check=True)  # noqa: S603


def newest_wheel(dist_dir: Path) -> Path:
    wheels = sorted(
        dist_dir.glob("*.whl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not wheels:
        msg = f"No wheel found in {dist_dir}. Run `make dist` first."
        raise FileNotFoundError(msg)
    return wheels[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist-dir", default="dist", help="Directory containing wheels"
    )
    parser.add_argument(
        "--venv-dir",
        default=".tmp/release-wheel-smoke",
        help="Temporary venv path",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    dist_dir = Path(args.dist_dir)
    venv_dir = Path(args.venv_dir)

    wheel = newest_wheel(dist_dir)

    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    run([sys.executable, "-m", "venv", str(venv_dir)])

    if sys.platform == "win32":
        python_bin = venv_dir / "Scripts" / "python"
        pip_bin = venv_dir / "Scripts" / "pip"
    else:
        python_bin = venv_dir / "bin" / "python"
        pip_bin = venv_dir / "bin" / "pip"

    run([str(pip_bin), "install", "--upgrade", "pip"])
    run([str(pip_bin), "install", str(wheel)])

    run(
        [
            str(python_bin),
            "-c",
            f"import {PACKAGE_DIR}; print({PACKAGE_DIR}.__version__)",
        ]
    )
    logger.info("Wheel smoke test passed: %s", wheel.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
