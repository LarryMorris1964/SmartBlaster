"""Known thermostat profiles and IR/camera support metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThermostatProfile:
    id: str
    make: str
    model: str
    ir_protocol: str
    camera_supported: bool
    supported_temperature_units: tuple[str, ...]
    default_temperature_unit: str
    notes: str


_PROFILES: dict[str, ThermostatProfile] = {
    "midea_kjr_12b_dp_t": ThermostatProfile(
        id="midea_kjr_12b_dp_t",
        make="Midea",
        model="KJR-12B-DP-T",
        ir_protocol="midea",
        camera_supported=True,
        supported_temperature_units=("C", "F"),
        default_temperature_unit="C",
        notes="Primary launch profile. Supports IR control now and first camera routines.",
    ),
}


def list_profiles() -> list[ThermostatProfile]:
    return list(_PROFILES.values())


def get_profile(profile_id: str) -> ThermostatProfile:
    profile = _PROFILES.get(profile_id)
    if profile is None:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(f"unknown thermostat profile '{profile_id}'. known: {known}")
    return profile
