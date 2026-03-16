"""Model-agnostic parsed thermostat display state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DisplayTemperatureUnit(str, Enum):
    C = "C"
    F = "F"


class DisplayMode(str, Enum):
    AUTO = "auto"
    COOL = "cool"
    DRY = "dry"
    HEAT = "heat"
    FAN_ONLY = "fan_only"
    OFF = "off"
    UNKNOWN = "unknown"


class FanSpeedLevel(str, Enum):
    OFF = "off"
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ThermostatDisplayState:
    """Structured reading extracted from a thermostat LCD image."""

    model_id: str
    power_on: bool | None = None
    mode: DisplayMode = DisplayMode.UNKNOWN
    set_temperature: float | None = None
    temperature_unit: DisplayTemperatureUnit | None = None
    fan_speed: FanSpeedLevel = FanSpeedLevel.UNKNOWN
    timer_set: bool | None = None
    timer_on_enabled: bool | None = None
    timer_off_enabled: bool | None = None
    follow_me_enabled: bool | None = None
    lock_enabled: bool | None = None
    raw_indicators: dict[str, bool] = field(default_factory=dict)
    confidence_by_field: dict[str, float] = field(default_factory=dict)
    unreadable_fields: tuple[str, ...] = ()
