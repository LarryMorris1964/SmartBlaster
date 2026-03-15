"""Typed command model for Midea KJR-12B-DP-T style IR control."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class MideaMode(str, Enum):
    OFF = "off"
    AUTO = "auto"
    COOL = "cool"
    HEAT = "heat"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class MideaFan(str, Enum):
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SILENT = "silent"
    TURBO = "turbo"


class MideaSwing(str, Enum):
    OFF = "off"
    VERTICAL = "vertical"
    BOTH = "both"


class MideaPreset(str, Enum):
    NONE = "none"
    SLEEP = "sleep"
    ECO = "eco"
    BOOST = "boost"


@dataclass(frozen=True)
class MideaIrCommand:
    mode: MideaMode
    temperature_c: float | None = None
    fan: MideaFan = MideaFan.AUTO
    swing: MideaSwing = MideaSwing.OFF
    preset: MideaPreset = MideaPreset.NONE
    follow_me_c: float | None = None
    beeper: bool = False

    def validate(self) -> None:
        if self.mode == MideaMode.OFF:
            return

        if self.temperature_c is None:
            raise ValueError("temperature_c is required when mode is not off")

        if not (17 <= self.temperature_c <= 30):
            raise ValueError("temperature_c must be between 17 and 30 for Midea IR")

        if self.follow_me_c is not None and not (0 <= self.follow_me_c <= 37):
            raise ValueError("follow_me_c must be between 0 and 37")

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "MideaIrCommand":
        if "mode" not in payload:
            raise ValueError("payload.mode is required")

        command = cls(
            mode=MideaMode(str(payload["mode"])),
            temperature_c=(float(payload["temperature_c"]) if "temperature_c" in payload else None),
            fan=MideaFan(str(payload.get("fan", MideaFan.AUTO.value))),
            swing=MideaSwing(str(payload.get("swing", MideaSwing.OFF.value))),
            preset=MideaPreset(str(payload.get("preset", MideaPreset.NONE.value))),
            follow_me_c=(float(payload["follow_me_c"]) if "follow_me_c" in payload else None),
            beeper=bool(payload.get("beeper", False)),
        )
        command.validate()
        return command

    def to_payload(self) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "mode": self.mode.value,
            "fan": self.fan.value,
            "swing": self.swing.value,
            "preset": self.preset.value,
            "beeper": self.beeper,
        }
        if self.temperature_c is not None:
            payload["temperature_c"] = self.temperature_c
        if self.follow_me_c is not None:
            payload["follow_me_c"] = self.follow_me_c
        return payload
