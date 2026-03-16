"""Dataset helpers for offline thermostat display validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALLOWED_EXPECTED_FIELDS = {
    "mode",
    "set_temperature",
    "set_temp",
    "temperature_unit",
    "fan_speed",
    "timer_set",
    "timer_on_enabled",
    "timer_off_enabled",
    "follow_me_enabled",
    "power_on",
    "lock_enabled",
}

ALLOWED_MODES = {"auto", "cool", "dry", "heat", "fan_only", "unknown"}
ALLOWED_FAN_SPEEDS = {"low", "medium", "high", "off", "unknown"}
ALLOWED_TEMPERATURE_UNITS = {"C", "F"}


def validate_labels_manifest(labels_file: Path, *, images_dir: Path | None = None) -> list[str]:
    """Validate JSONL labels and return a list of human-readable issues."""
    errors: list[str] = []
    seen_filenames: set[str] = set()

    with labels_file.open("r", encoding="utf-8") as handle:
        for idx, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue

            try:
                data: Any = json.loads(line)
            except json.JSONDecodeError as ex:
                errors.append(f"labels line {idx}: invalid JSON ({ex.msg})")
                continue

            if not isinstance(data, dict):
                errors.append(f"labels line {idx}: root must be a JSON object")
                continue

            filename = str(data.get("filename", "")).strip()
            expected = data.get("expected")

            if not filename:
                errors.append(f"labels line {idx}: missing filename")
                continue

            if filename in seen_filenames:
                errors.append(f"labels line {idx}: duplicate filename '{filename}'")
            seen_filenames.add(filename)

            if images_dir is not None:
                image_file = images_dir / filename
                if not image_file.exists():
                    errors.append(f"labels line {idx}: image file not found '{filename}'")

            if not isinstance(expected, dict):
                errors.append(f"labels line {idx}: expected must be an object")
                continue

            for field in expected:
                if field not in ALLOWED_EXPECTED_FIELDS:
                    errors.append(f"labels line {idx}: unsupported expected field '{field}'")

            _validate_expected_field_values(expected=expected, line_number=idx, errors=errors)

    return errors


def _validate_expected_field_values(*, expected: dict[str, object], line_number: int, errors: list[str]) -> None:
    mode = expected.get("mode")
    if mode is not None and mode not in ALLOWED_MODES:
        errors.append(
            f"labels line {line_number}: mode must be one of {sorted(ALLOWED_MODES)}"
        )

    fan_speed = expected.get("fan_speed")
    if fan_speed is not None and fan_speed not in ALLOWED_FAN_SPEEDS:
        errors.append(
            f"labels line {line_number}: fan_speed must be one of {sorted(ALLOWED_FAN_SPEEDS)}"
        )

    temp_unit = expected.get("temperature_unit")
    if temp_unit is not None and temp_unit not in ALLOWED_TEMPERATURE_UNITS:
        errors.append(
            f"labels line {line_number}: temperature_unit must be one of {sorted(ALLOWED_TEMPERATURE_UNITS)}"
        )

    set_temperature = expected.get("set_temperature")
    if set_temperature is not None and not isinstance(set_temperature, (int, float)):
        errors.append(f"labels line {line_number}: set_temperature must be a number")

    for bool_field in (
        "set_temp",
        "timer_set",
        "timer_on_enabled",
        "timer_off_enabled",
        "follow_me_enabled",
        "power_on",
        "lock_enabled",
    ):
        value = expected.get(bool_field)
        if value is not None and not isinstance(value, bool):
            errors.append(f"labels line {line_number}: {bool_field} must be true/false")


def load_labels_manifest(labels_file: Path) -> dict[str, dict[str, object]]:
    """Load labels from JSONL manifest.

    Each line must include:
    - filename: relative image filename
    - expected: dict of expected field values
    """
    issues = validate_labels_manifest(labels_file)
    if issues:
        raise ValueError("; ".join(issues))

    records: dict[str, dict[str, object]] = {}
    with labels_file.open("r", encoding="utf-8") as handle:
        for idx, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            data = json.loads(line)
            filename = str(data.get("filename", "")).strip()
            expected = data.get("expected")
            if not filename:
                raise ValueError(f"labels line {idx}: missing filename")
            if not isinstance(expected, dict):
                raise ValueError(f"labels line {idx}: expected must be an object")
            records[filename] = expected
    return records
