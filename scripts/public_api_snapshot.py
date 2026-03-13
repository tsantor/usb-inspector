#!/usr/bin/env python3
"""Generate or verify a symbol-level public API snapshot for xapp-core."""

from __future__ import annotations

import argparse
import importlib
import json
import logging
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
logger = logging.getLogger(__name__)


def load_contract(contract_file: Path) -> dict[str, list[str]]:
    data = json.loads(contract_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "modules" not in data:
        msg = f"Invalid contract file format: {contract_file}"
        raise ValueError(msg)

    modules = data["modules"]
    if not isinstance(modules, dict) or not modules:
        msg = f"Contract modules must be a non-empty object: {contract_file}"
        raise ValueError(msg)

    contract: dict[str, list[str]] = {}
    for module_name, symbols in modules.items():
        if not isinstance(module_name, str) or not module_name.strip():
            msg = "Contract module names must be non-empty strings"
            raise ValueError(msg)
        if not isinstance(symbols, list) or not symbols:
            msg = f"Contract module '{module_name}' must have a non-empty symbol list"
            raise ValueError(msg)
        contract[module_name] = sorted({str(name) for name in symbols})

    return contract


def verify_contract_symbols(contract: dict[str, list[str]]) -> dict[str, list[str]]:
    verified: dict[str, list[str]] = {}
    for module_name, symbols in contract.items():
        module = importlib.import_module(module_name)
        missing = [symbol for symbol in symbols if not hasattr(module, symbol)]
        if missing:
            missing_str = ", ".join(missing)
            msg = f"Contract mismatch in {module_name}; missing symbols: {missing_str}"
            raise ValueError(msg)
        verified[module_name] = symbols
    return verified


def build_snapshot(contract: dict[str, list[str]]) -> dict[str, Any]:
    verified = verify_contract_symbols(contract)
    return {
        "schema_version": SCHEMA_VERSION,
        "modules": dict(sorted(verified.items())),
    }


def write_snapshot(snapshot: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def check_snapshot(snapshot: dict[str, Any], output: Path) -> int:
    if not output.exists():
        logger.error("Snapshot file not found: %s", output)
        logger.error("Run: just api-snapshot")
        return 1

    existing = json.loads(output.read_text(encoding="utf-8"))
    if existing == snapshot:
        logger.info("Public API snapshot is up to date: %s", output)
        return 0

    new_text = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    tmp_file = output.with_suffix(".new.json")
    tmp_file.write_text(new_text, encoding="utf-8")
    logger.error("Public API changed: %s", output)
    logger.error("Wrote proposed snapshot: %s", tmp_file)
    logger.error("Review changes and run: just api-snapshot")
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract-file",
        default="api/public_api.contract.json",
        help="Path to module->symbols public API contract JSON.",
    )
    parser.add_argument(
        "--output",
        default="api/public_api.json",
        help="Path to API snapshot JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if snapshot differs from output file.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    contract_file = Path(args.contract_file)
    output = Path(args.output)

    contract = load_contract(contract_file)
    snapshot = build_snapshot(contract)

    if args.check:
        return check_snapshot(snapshot, output)

    write_snapshot(snapshot, output)
    logger.info("Wrote public API snapshot: %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
