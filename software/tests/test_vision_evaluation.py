from __future__ import annotations

import json
from pathlib import Path

from smartblaster.vision.evaluation import evaluate_dataset
from smartblaster.vision.models import (
    DisplayMode,
    DisplayTemperatureUnit,
    FanSpeedLevel,
    ThermostatDisplayState,
)


class FakeParser:
    model_id = "midea_kjr_12b_dp_t"

    def parse(self, frame: bytes) -> ThermostatDisplayState:
        marker = frame[:1]
        if marker == b"A":
            return ThermostatDisplayState(
                model_id=self.model_id,
                mode=DisplayMode.COOL,
                set_temperature=24.0,
                temperature_unit=DisplayTemperatureUnit.C,
                fan_speed=FanSpeedLevel.HIGH,
                timer_set=True,
                follow_me_enabled=True,
                power_on=True,
            )
        return ThermostatDisplayState(
            model_id=self.model_id,
            mode=DisplayMode.HEAT,
            set_temperature=72.0,
            temperature_unit=DisplayTemperatureUnit.F,
            fan_speed=FanSpeedLevel.OFF,
            timer_set=False,
            follow_me_enabled=False,
            power_on=True,
        )


def test_evaluate_dataset_writes_report(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True)

    (images_dir / "img1.jpg").write_bytes(b"A-image")
    (images_dir / "img2.jpg").write_bytes(b"B-image")

    labels_file = tmp_path / "labels.jsonl"
    labels_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "filename": "img1.jpg",
                        "expected": {
                            "mode": "cool",
                            "set_temperature": 24.0,
                            "temperature_unit": "C",
                            "fan_speed": "high",
                            "timer_set": True,
                            "follow_me_enabled": True,
                            "power_on": True,
                        },
                    }
                ),
                json.dumps(
                    {
                        "filename": "img2.jpg",
                        "expected": {
                            "mode": "heat",
                            "set_temperature": 72.0,
                            "temperature_unit": "F",
                            "fan_speed": "off",
                            "timer_set": False,
                            "follow_me_enabled": False,
                            "power_on": True,
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    report_file = tmp_path / "report.json"
    summary = evaluate_dataset(
        parser=FakeParser(),
        images_dir=images_dir,
        labels_file=labels_file,
        output_report=report_file,
    )

    assert summary["images"] == 2
    assert summary["all_correct_images"] == 2
    assert report_file.exists()

    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["field_accuracy"]["mode"] == 1.0
