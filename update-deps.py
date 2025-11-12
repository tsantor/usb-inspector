import subprocess
import tomllib
from pathlib import Path


def update_pyproject_toml():
    """
    UV needs to have a method like this.  Not sure why it doesn't.

    When running the these uv commands, it doesn't actually update the
    pyproject.toml to the latest versions of the packages installed.

        uv lock --upgrade
        uv sync --all-groups
    """
    with Path("pyproject.toml").open("rb") as file:
        pyproject = tomllib.load(file)

    dependencies = pyproject["project"]["dependencies"]
    for dependency in dependencies:
        package_name = dependency.split(">")[0].split("=")[0].split("<")[0].strip()
        subprocess.run(["uv", "remove", package_name], check=False)  # noqa: S603, S607
        subprocess.run(["uv", "add", package_name], check=False)  # noqa: S603, S607

    dependencies = pyproject["dependency-groups"]["dev"]
    for dependency in dependencies:
        package_name = dependency.split(">")[0].split("=")[0].split("<")[0].strip()
        subprocess.run(["uv", "remove", package_name, "--group", "dev"], check=False)  # noqa: S603, S607
        subprocess.run(["uv", "add", package_name, "--group", "dev"], check=False)  # noqa: S603, S607

    dependencies = pyproject["dependency-groups"]["test"]
    for dependency in dependencies:
        package_name = dependency.split(">")[0].split("=")[0].split("<")[0].strip()
        subprocess.run(["uv", "remove", package_name, "--group", "test"], check=False)  # noqa: S603, S607
        subprocess.run(["uv", "add", package_name, "--group", "test"], check=False)  # noqa: S603, S607


update_pyproject_toml()
