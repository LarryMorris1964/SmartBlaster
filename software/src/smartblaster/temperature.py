"""Temperature unit normalization for thermostat adapters.

Program standard: Celsius.
"""

from __future__ import annotations

from typing import Final

PROGRAM_TEMPERATURE_UNIT: Final[str] = "C"


def normalize_unit(unit: str) -> str:
    normalized = unit.strip().upper()
    if normalized not in {"C", "F"}:
        raise ValueError("temperature unit must be 'C' or 'F'")
    return normalized


def thermostat_to_program_celsius(value: float, thermostat_unit: str) -> float:
    unit = normalize_unit(thermostat_unit)
    if unit == "C":
        return value
    return (value - 32.0) * 5.0 / 9.0


def program_celsius_to_thermostat(value_c: float, thermostat_unit: str) -> float:
    unit = normalize_unit(thermostat_unit)
    if unit == "C":
        return value_c
    return (value_c * 9.0 / 5.0) + 32.0


def quantize_program_setpoint_for_thermostat(value_c: float, thermostat_unit: str) -> float:
    """Round setpoints according to thermostat unit granularity.

    - Celsius thermostats: preserve value.
    - Fahrenheit thermostats: quantize to nearest whole °F, then convert back to °C.
    """
    unit = normalize_unit(thermostat_unit)
    if unit == "C":
        return value_c

    f_value = program_celsius_to_thermostat(value_c, unit)
    f_quantized = round(f_value)
    return thermostat_to_program_celsius(float(f_quantized), unit)
