import tarfile
import zipfile
from email import message_from_string
from pathlib import Path

from usb_inspector import __all__ as exported_symbols
from usb_inspector import __version__

DIST_DIR = Path("dist")
PACKAGE_NAME = "usb-inspector"
PACKAGE_DIR = "usb_inspector"


def _latest_artifact(pattern: str) -> Path:
    matches = sorted(DIST_DIR.glob(pattern))
    if not matches:
        msg = f"No artifact found matching: {DIST_DIR / pattern}"
        raise FileNotFoundError(msg)
    return matches[-1]


def _verify_wheel(wheel_path: Path) -> None:
    with zipfile.ZipFile(wheel_path, "r") as wheel:
        names = set(wheel.namelist())
        assert f"{PACKAGE_DIR}/__init__.py" in names

        dist_info_dir = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        ).rsplit("/", maxsplit=1)[0]
        metadata_name = f"{dist_info_dir}/METADATA"
        metadata = message_from_string(wheel.read(metadata_name).decode("utf-8"))
        assert metadata["Name"] == PACKAGE_NAME
        assert metadata["Version"] == __version__

        exported_count = sum(
            1
            for symbol in exported_symbols
            if symbol in wheel.read(f"{PACKAGE_DIR}/__init__.py").decode("utf-8")
        )
        assert exported_count == len(exported_symbols)


def _verify_sdist(sdist_path: Path) -> None:
    with tarfile.open(sdist_path, "r:gz") as sdist:
        names = set(sdist.getnames())
        assert any(name.endswith(f"src/{PACKAGE_DIR}/__init__.py") for name in names)
        assert any(name.endswith("pyproject.toml") for name in names)


def main() -> None:
    wheel_path = _latest_artifact("*.whl")
    sdist_path = _latest_artifact("*.tar.gz")
    _verify_wheel(wheel_path)
    _verify_sdist(sdist_path)


if __name__ == "__main__":
    main()
