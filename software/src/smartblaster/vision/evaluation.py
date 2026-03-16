"""Offline evaluation for thermostat display parsers."""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
import json
from pathlib import Path

from smartblaster.vision.dataset import load_labels_manifest
from smartblaster.vision.models import ThermostatDisplayState
from smartblaster.vision.parser import ThermostatDisplayParser

EVAL_FIELDS = (
    "mode",
    "set_temperature",
    "set_temp",
    "temperature_unit",
    "fan_speed",
    "timer_set",
    "follow_me_enabled",
    "power_on",
)


def evaluate_dataset(
    *,
    parser: ThermostatDisplayParser,
    images_dir: Path,
    labels_file: Path,
    output_report: Path,
) -> dict[str, object]:
    labels = load_labels_manifest(labels_file)

    per_field_total = {field: 0 for field in EVAL_FIELDS}
    per_field_correct = {field: 0 for field in EVAL_FIELDS}
    image_results: list[dict[str, object]] = []

    for filename, expected in labels.items():
        image_file = images_dir / filename
        frame = image_file.read_bytes()
        parsed = parser.parse(frame)

        parsed_flat = _state_to_comparable_map(parsed)
        mismatches: dict[str, dict[str, object]] = {}

        for field in EVAL_FIELDS:
            if field not in expected:
                continue
            per_field_total[field] += 1
            expected_value = expected[field]
            actual_value = parsed_flat.get(field)
            if actual_value == expected_value:
                per_field_correct[field] += 1
            else:
                mismatches[field] = {
                    "expected": expected_value,
                    "actual": actual_value,
                }

        image_results.append(
            {
                "filename": filename,
                "ok": len(mismatches) == 0,
                "mismatches": mismatches,
                "parsed": parsed_flat,
            }
        )

    field_accuracy: dict[str, float] = {}
    for field in EVAL_FIELDS:
        total = per_field_total[field]
        field_accuracy[field] = 1.0 if total == 0 else per_field_correct[field] / total

    summary = {
        "images": len(labels),
        "field_accuracy": field_accuracy,
        "all_correct_images": sum(1 for item in image_results if item["ok"]),
        "results": image_results,
    }

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _state_to_comparable_map(state: ThermostatDisplayState) -> dict[str, object]:
    payload = asdict(state)

    # flatten enum-like values
    for field in ("mode", "fan_speed", "temperature_unit"):
        value = payload.get(field)
        if isinstance(value, Enum):
            payload[field] = value.value

    # Derived indicator not modeled as a first-class ThermostatDisplayState field.
    payload["set_temp"] = bool(payload.get("raw_indicators", {}).get("set_temp", False))
    return payload
