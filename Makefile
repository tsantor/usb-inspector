# -----------------------------------------------------------------------------
# Generate help output when running just `make`
# -----------------------------------------------------------------------------
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

PYTHON_VERSION=3.13.1
package_name=usb_inspector
package_version=0.2.1
aws_profile=xstudios
s3_bucket=xstudios-pypi
wheel_name=${package_name}-${package_version}-py3-none-any.whl
package_url=https://${s3_bucket}.s3.amazonaws.com/${wheel_name}

# START - Generic commands
# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------

env:  ## Create virtual environment (uses `uv`)
	uv venv --python ${PYTHON_VERSION}

env_remove:  ## Remove virtual environment
	rm -rf .venv/

env_recreate: env_remove env pip_install_editable pip_install_dev  ## Recreate environment from scratch

# -----------------------------------------------------------------------------
# Pip
# -----------------------------------------------------------------------------

pip_install_editable:  ## Install in editable mode
	uv pip install -e .
	# --extra-index-url https://www.piwheels.org/simple

pip_list:  ## Run pip list
	uv pip list

pip_tree: ## Run pip tree
	uv pip tree

pipdeptree:  ## # Run pipdeptree
	uv run pipdeptree

pip_install_dev:  ## Sync dependencies [production, dev, test]
	uv sync --no-default-groups --group test --group dev

uv_lock:	## Match lock file to current dependencies in pyproject.toml
	uv lock

uv_lock_check:	## Check if lock file is up to date
	uv lock --check

uv_sync:	## Sync dependencies from lock file
	uv sync

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------

pytest:  ## Run tests
	uv run pytest -vx --cov --cov-report=html

pytest_verbose:  ## Run tests in verbose mode
	uv run pytest -vvs --cov --cov-report=html

coverage:  ## Run tests with coverage
	uv run coverage run -m pytest && coverage html

coverage_verbose:  ## Run tests with coverage in verbose mode
	uv run coverage run -m pytest -vss && coverage html

coverage_skip:  ## Run tests with coverage and skip covered
	uv run coverage run -m pytest -vs && coverage html --skip-covered

open_coverage:  ## Open coverage report
	open htmlcov/index.html

# -----------------------------------------------------------------------------
# Ruff
# -----------------------------------------------------------------------------

ruff_format: ## Run ruff format
	uv run ruff format

ruff_check: ## Run ruff check
	uv run ruff check

ruff_clean: ## Run ruff clean
	uv run ruff clean

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

clean_build:  ## Remove build artifacts
	rm -fr build/ dist/ .eggs/
	find . -name '*.egg-info' -o -name '*.egg' -exec rm -fr {} +

clean_pyc:  ## Remove python file artifacts
	find . \( -name '*.pyc' -o -name '*.pyo' -o -name '*~' -o -name '__pycache__' \) -exec rm -fr {} +

clean: clean_build clean_pyc ## Remove all build and python artifacts

clean_pytest_cache:  ## Clear pytest cache
	rm -rf .pytest_cache

clean_ruff_cache:  ## Clear ruff cache
	rm -rf .ruff_cache

clean_tox_cache:  ## Clear tox cache
	rm -rf .tox

clean_coverage:  ## Clear coverage cache
	rm .coverage
	rm -rf htmlcov

clean_tests: clean_pytest_cache clean_ruff_cache clean_tox_cache clean_coverage  ## Clear pytest, ruff, tox, and coverage caches

clean_all: clean clean_tests  ## Full cleanup

# -----------------------------------------------------------------------------
# Miscellaneous
# -----------------------------------------------------------------------------

tree:  ## Show directory tree
	tree -I 'dist|htmlcov|node_modules|__pycache__|*.egg-info|utility-scripts|SCRATCH.md'

# -----------------------------------------------------------------------------
# Deploy
# -----------------------------------------------------------------------------

dist: clean ## Builds source and wheel package
	uv run python3 -m build

twine_upload_test: dist ## Upload package to pypi test
	uv run twine upload dist/* -r pypitest

twine_upload: dist ## Package and upload a release
	uv run twine upload dist/*

twine_check: dist ## Twine check
	uv run twine check dist/*

twine_fix: ## Fix twine issues
	uv pip install -U twine pkginfo

# -----------------------------------------------------------------------------
# X Studios S3 PyPi
# -----------------------------------------------------------------------------

create_latest_copy: dist  ## Create latest copy of distro
	cp dist/*.whl dist/${package_name}-latest-py3-none-any.whl

push_to_s3:  ## Push distro to S3 bucket
	aws s3 sync --profile=${aws_profile} --acl public-read ./dist/ s3://${s3_bucket}/ \
        --exclude "*" --include "*.whl"
	echo "${package_url}"

# END - Generic commands
# -----------------------------------------------------------------------------
# Project Specific
# -----------------------------------------------------------------------------

user=pi
host=raspi3b-2.local
remote_dir=/home/pi/Sandbox/Python/my-pypi-packages/usb-inspector

rsync_to_pi:	## Sync files to Raspberry Pi
	rsync -avz . ${user}@${host}:${remote_dir} --delete \
		--exclude=".DS_Store" --exclude='.git' --exclude='.venv' \
		--exclude=".coverage" --exclude='htmlcov' --exclude='__pycache__' \
		--exclude='.pytest_cache' --exclude='.ruff_cache' \
		--exclude='.vscode' --exclude='node_modules' --exclude='dist' --exclude='*.egg-info'

uv_add_dev_dependencies:  ## Add dev dependencies
	uv add twine wheel build ruff pipdeptree pre-commit --group dev

uv_add_test_dependencies:  ## Add test dependencies
	uv add pytest pytest-cov pytest-mock coverage --group test

uv_add_basic:  ## Install basic dependencies
	uv add click pydantic rich toml sentry-sdk psutil setuptools build

uv_add_async:  ## Install async dependencies
	uv add aiomqtt httpx aiofiles

uv_add_rpi:	## Install Raspberry Pi specific dependencies
	uv add RPi.GPIO

uv_upgrade_and_sync:	## Upgrade all dependencies and sync
	uv lock --upgrade
	uv sync --all-groups

install_uv:	## Install uv
	curl -LsSf https://astral.sh/uv/install.sh | sh

# Add your project specific commands here
