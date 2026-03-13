set shell := ["bash", "-cu"]
# set shell := ["powershell.exe", "-NoLogo", "-Command"]

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

python_version := "3.13.1"
aws_profile := "xstudios"
s3_bucket := "xstudios-pypi"
package_name := "usb_inspector"
# wheel_name := `ls dist/*.whl 2>/dev/null | head -n 1 | xargs -n 1 basename`
# package_url := "https://" + s3_bucket + ".s3.amazonaws.com/" + wheel_name

# DO NOT EDIT BELOW THIS LINE - auto-generated from template
# -----------------------------------------------------------------------------
# Default - list all recipes
# -----------------------------------------------------------------------------

# List all available recipes
[group('help')]
default:
    @just --list

# -----------------------------------------------------------------------------
# Versioning
# -----------------------------------------------------------------------------

# Show current package version
[group('versioning')]
version-show:
    @uv run python -c "import {{package_name}} as pkg; print(pkg.__version__)"

# Set explicit version (strict SemVer: X.Y.Z)
[group('versioning')]
version-set new_version:
    @uv run python -c "import pathlib, re, sys; v='{{new_version}}'; p=pathlib.Path('src/{{package_name}}/__init__.py'); t=p.read_text(encoding='utf-8'); assert re.fullmatch(r'\\d+\\.\\d+\\.\\d+', v), f'Invalid version: {v}. Use X.Y.Z'; n,c=re.subn(r'__version__\\s*=\\s*\"[^\"]+\"', f'__version__ = \"{v}\"', t, count=1); assert c==1, 'Could not update __version__'; p.write_text(n, encoding='utf-8'); print(v)"

# Bump patch version (X.Y.Z -> X.Y.Z+1)
[group('versioning')]
version-bump-patch:
    @v=$$(uv run python -c "import re, pathlib; t=pathlib.Path('src/{{package_name}}/__init__.py').read_text(encoding='utf-8'); m=re.search(r'__version__\\s*=\\s*\"([0-9]+)\\.([0-9]+)\\.([0-9]+)\"', t); assert m, 'Current __version__ is not strict X.Y.Z'; print(f'{m.group(1)}.{m.group(2)}.{int(m.group(3))+1}')"); just version-set "$$v"

# Bump minor version (X.Y.Z -> X.Y+1.0)
[group('versioning')]
version-bump-minor:
    @v=$$(uv run python -c "import re, pathlib; t=pathlib.Path('src/{{package_name}}/__init__.py').read_text(encoding='utf-8'); m=re.search(r'__version__\\s*=\\s*\"([0-9]+)\\.([0-9]+)\\.([0-9]+)\"', t); assert m, 'Current __version__ is not strict X.Y.Z'; print(f'{m.group(1)}.{int(m.group(2))+1}.0')"); just version-set "$$v"

# Bump major version (X.Y.Z -> X+1.0.0)
[group('versioning')]
version-bump-major:
    @v=$$(uv run python -c "import re, pathlib; t=pathlib.Path('src/{{package_name}}/__init__.py').read_text(encoding='utf-8'); m=re.search(r'__version__\\s*=\\s*\"([0-9]+)\\.([0-9]+)\\.([0-9]+)\"', t); assert m, 'Current __version__ is not strict X.Y.Z'; print(f'{int(m.group(1))+1}.0.0')"); just version-set "$$v"

# Validate a bumped version with full quality gates
[group('versioning')]
version-verify: ci

# Print suggested git tag for current version
[group('versioning')]
version-tag-dryrun:
    @uv run python -c "import {{package_name}} as pkg; print(f'v{pkg.__version__}')"

# Create local annotated git tag for current version
[group('versioning')]
version-tag:
    @test -z "$$(git status --porcelain)" || { echo "Working tree is not clean. Commit or stash changes before tagging."; exit 1; }
    @tag=$$(just version-tag-dryrun); \
    [[ "$$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$$ ]] || { echo "Invalid tag format: $$tag"; exit 1; }; \
    git rev-parse "$$tag" >/dev/null 2>&1 && { echo "Tag already exists: $$tag"; exit 1; } || true; \
    git tag -a "$$tag" -m "Release $$tag"; \
    echo "Created tag $$tag"

# Push current version tag to origin
[group('versioning')]
version-tag-push:
    @test -z "$$(git status --porcelain)" || { echo "Working tree is not clean. Commit or stash changes before pushing tags."; exit 1; }
    @tag=$$(just version-tag-dryrun); \
    [[ "$$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$$ ]] || { echo "Invalid tag format: $$tag"; exit 1; }; \
    git rev-parse "$$tag" >/dev/null 2>&1 || { echo "Tag does not exist locally: $$tag. Run 'just version-tag' first."; exit 1; }; \
    git push origin "$$tag"

# -----------------------------------------------------------------------------
# Workflow
# -----------------------------------------------------------------------------

# Run fast local quality checks
[group('workflow')]
check: uv-lock-check ruff-check api-check pytest-cov-gate

# Apply automatic fixes and re-run checks
[group('workflow')]
fix: ruff-format ruff-check-fix check

# Mirror CI/release gate locally
[group('workflow')]
ci: release-check

# Show toolchain and environment diagnostics
[group('workflow')]
doctor:
    uv --version
    uv run python --version
    uv pip list --strict
    uv lock --check

# Show outdated dependencies across all groups
[group('workflow')]
outdated:
    uv tree --outdated --all-groups

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------

# Create virtual environment (uses `uv`)
[group('environment')]
env:
    uv venv --python {{python_version}}

# Remove virtual environment
[group('environment')]
env-remove:
    rm -rf .venv/

# Recreate environment from scratch
[group('environment')]
env-recreate: env-remove env pip-install-editable

# -----------------------------------------------------------------------------
# Pip
# -----------------------------------------------------------------------------

# Install in editable mode
[group('uv')]
pip-install-editable:
    uv sync --all-groups
    uv pip install -e .

# Add dev dependencies
[group('uv')]
uv-add-dev-dependencies:
    uv add twine wheel build setuptools ruff pipdeptree pre-commit --group dev

# Add test dependencies
[group('uv')]
uv-add-test-dependencies:
    uv add pytest pytest-cov pytest-mock pytest-asyncio coverage --group test

# Run pip list
[group('uv')]
pip-list:
    uv pip list

# Run pip tree
[group('pip')]
pip-tree:
    uv pip tree

# Run pipdeptree
[group('uv')]
pipdeptree:
    uv run pipdeptree

# Sync dependencies from lock file
[group('uv')]
uv-sync:
    uv sync

# Sync dependencies [production, dev, test]
[group('uv')]
uv-install-dev:
    uv sync --no-default-groups --group test --group dev

# Match lock file to current dependencies in pyproject.toml
[group('uv')]
uv-lock:
    uv lock

# Upgrade dependencies and update lock file
[group('uv')]
uv-lock-upgrade:
    uv lock --upgrade

# Check if lock file is up to date
[group('uv')]
uv-lock-check:
    uv lock --check

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

# Run tests
[group('testing')]
pytest:
    uv run pytest -vx --cov --cov-report=html

# Run tests in verbose mode
[group('testing')]
pytest-verbose:
    uv run pytest -vvs --cov --cov-report=html

# Run tests with coverage
[group('testing')]
coverage:
    uv run pytest -q --cov={{package_name}} --cov-report=term-missing --cov-report=html

# Run tests with coverage in verbose mode
[group('testing')]
coverage-verbose:
    uv run pytest -vss --cov={{package_name}} --cov-report=term-missing --cov-report=html

# Run tests with coverage and skip covered
[group('testing')]
coverage-skip:
    uv run pytest -vs --cov={{package_name}} --cov-report=term-missing:skip-covered --cov-report=html

# Update README coverage badge from current test coverage
[group('testing')]
coverage-badge:
    uv run pytest -q --cov={{package_name}} --cov-report=json
    uv run python scripts/update_coverage_badge.py --coverage-json coverage.json --readme README.md
    rm -f coverage.json

# Open coverage report
[group('testing')]
open-coverage:
    open htmlcov/index.html

# Run tests with coverage threshold gate
[group('testing')]
pytest-cov-gate cov_fail_under="50":
    uv run pytest -q --cov={{package_name}} --cov-report=term-missing --cov-fail-under={{cov_fail_under}}

# Generate public API lockfile snapshot
[group('testing')]
api-snapshot:
    uv run python scripts/public_api_snapshot.py --output api/public_api.json --contract-file api/public_api.contract.json

# Verify public API lockfile is up to date
[group('testing')]
api-check:
    uv run python scripts/public_api_snapshot.py --check --output api/public_api.json --contract-file api/public_api.contract.json

# Run tox
[group('testing')]
tox:
    uv run tox

# -----------------------------------------------------------------------------
# Linting
# -----------------------------------------------------------------------------

# Run ruff format
[group('linting')]
ruff-format:
    uv run ruff format

# Run ruff check
[group('linting')]
ruff-check:
    uv run ruff check

# Run ruff check with autofix
[group('linting')]
ruff-check-fix:
    uv run ruff check --fix

# Run ruff clean
[group('linting')]
ruff-clean:
    uv run ruff clean

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

# Remove build artifacts
[group('cleanup')]
clean-build:
    rm -fr build/ dist/ .eggs/
    find . -name '*.egg-info' -o -name '*.egg' -exec rm -fr {} +

# Remove python file artifacts
[group('cleanup')]
clean-pyc:
    find . \( -name '*.pyc' -o -name '*.pyo' -o -name '*~' -o -name '__pycache__' \) -exec rm -fr {} +

# Remove all build and python artifacts
[group('cleanup')]
clean: clean-build clean-pyc

# Clear pytest cache
[group('cleanup')]
clean-pytest-cache:
    rm -rf .pytest_cache

# Clear ruff cache
[group('cleanup')]
clean-ruff-cache:
    rm -rf .ruff_cache

# Clear tox cache
[group('cleanup')]
clean-tox-cache:
    rm -rf .tox

# Clear coverage cache
[group('cleanup')]
clean-coverage:
    rm .coverage
    rm -rf htmlcov

# Clear pytest, ruff, tox, and coverage caches
[group('cleanup')]
clean-tests: clean-pytest-cache clean-ruff-cache clean-tox-cache clean-coverage

# Full cleanup
[group('cleanup')]
clean-all: clean clean-tests

# -----------------------------------------------------------------------------
# Miscellaneous
# -----------------------------------------------------------------------------

# Show directory tree
[group('misc')]
tree:
    tree src -I 'node_modules|__pycache__|*.egg-info'

# ----------------------------------------------------------------------------
# Deploy
# -----------------------------------------------------------------------------

# Build source and wheel package
[group('deploy')]
dist: clean
    uv run python3 -m build

# Install wheel in a clean venv and verify imports
[group('deploy')]
wheel-smoke: dist
    uv run python scripts/wheel_smoke_test.py --dist-dir dist --venv-dir .tmp/release-wheel-smoke

# Run full release quality gates
[group('deploy')]
release-check: ruff-check api-check pytest-cov-gate dist
    uv run python scripts/verify_dist_artifacts.py
    uv run python scripts/wheel_smoke_test.py --dist-dir dist --venv-dir .tmp/release-wheel-smoke
    uv run twine check dist/*

# Upload package to pypi test
[group('deploy')]
twine-upload-test: dist
    uv run twine upload dist/* -r pypitest

# Package and upload a release
[group('deploy')]
twine-upload: dist
    uv run twine upload dist/*

# Twine check
[group('deploy')]
twine-check: dist
    uv run twine check dist/*

# Fix twine issues
[group('deploy')]
twine-fix:
    uv pip install -U twine pkginfo

# -----------------------------------------------------------------------------
# X Studios S3 PyPi
# -----------------------------------------------------------------------------

# Push distro to S3 bucket
# [group('s3')]
# push-to-s3:
#     aws s3 sync --profile={{aws_profile}} --acl public-read ./dist/ s3://{{s3_bucket}}/ \
#         --exclude "*" --include "*.whl"
#     echo "{{package_url}}"

# DO NOT EDIT ABOVE THIS LINE - auto-generated from template
# -----------------------------------------------------------------------------
# Project Specific
# -----------------------------------------------------------------------------

user := "pi"
host := "192.168.1.48"
remote_dir := "/home/pi/Sandbox/Python/my-pypi-packages/xapp-core"

# Sync files to Raspberry Pi
[group('project')]
rsync-to-pi:
    rsync -avz . {{user}}@{{host}}:{{remote_dir}} --delete \
        --exclude=".DS_Store" --exclude='.git' --exclude='.venv' \
        --exclude=".coverage" --exclude='htmlcov' --exclude='__pycache__' \
        --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='.tox' \
        --exclude='.vscode' --exclude='node_modules' --exclude='dist' \
        --exclude='*.egg-info' --exclude=".tmp"



# Install basic dependencies
[group('project')]
uv-add-basic:
    uv add click pydantic rich toml sentry-sdk psutil

# Install async dependencies
[group('project')]
uv-add-async:
    uv add aiomqtt httpx aiofiles

# Install Raspberry Pi specific dependencies
[group('project')]
uv-add-rpi:
    uv add RPi.GPIO

# Upgrade all dependencies and sync
[group('project')]
uv-upgrade-and-sync:
    uv lock --upgrade
    uv sync --all-groups

# Install uv
[group('project')]
install-uv:
    curl -LsSf https://astral.sh/uv/install.sh | sh
