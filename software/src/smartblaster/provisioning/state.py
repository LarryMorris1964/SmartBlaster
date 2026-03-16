"""Setup state persistence and migration helpers."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
from typing import Any

SETUP_STATE_VERSION = 1
CONFIG_SCHEMA_VERSION_DEFAULT = 1
DEFAULT_DEVICE_NAME = "SmartBlaster"


def software_version() -> str:
    try:
        return version("smartblaster")
    except PackageNotFoundError:
        return "dev"


def migrate_setup_state(state: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(state)

    setup_state_version = migrated.get("setup_state_version")
    if not isinstance(setup_state_version, int) or setup_state_version < 1:
        migrated["setup_state_version"] = SETUP_STATE_VERSION

    config_schema_version = migrated.get("config_schema_version")
    if not isinstance(config_schema_version, int) or config_schema_version < 1:
        migrated["config_schema_version"] = CONFIG_SCHEMA_VERSION_DEFAULT

    device_name = migrated.get("device_name")
    if not isinstance(device_name, str) or not device_name.strip():
        migrated["device_name"] = DEFAULT_DEVICE_NAME

    if "saved_by_software_version" not in migrated:
        migrated["saved_by_software_version"] = software_version()

    return migrated


def load_setup_state(state_file: Path) -> dict[str, Any]:
    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return migrate_setup_state({})
    except Exception:
        return migrate_setup_state({})

    if not isinstance(raw, dict):
        return migrate_setup_state({})
    return migrate_setup_state(raw)


def persist_setup_state(state_file: Path, payload: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    final_payload = migrate_setup_state(payload)
    final_payload["setup_state_version"] = SETUP_STATE_VERSION
    final_payload["saved_by_software_version"] = software_version()

    tmp_file = state_file.with_suffix(f"{state_file.suffix}.tmp")
    with tmp_file.open("w", encoding="utf-8") as handle:
        json.dump(final_payload, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_file.replace(state_file)
