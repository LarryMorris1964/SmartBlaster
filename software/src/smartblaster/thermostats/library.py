"""Known thermostat profiles and IR/camera support metadata."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommandCriticality(str, Enum):
    NORMAL = "normal"
    IMPORTANT = "important"
    CRITICAL = "critical"


@dataclass(frozen=True)
class CommandPolicy:
    criticality: CommandCriticality
    max_attempts: int
    retry_wait_seconds: float


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


_DEFAULT_COMMAND_POLICY = CommandPolicy(
    criticality=CommandCriticality.NORMAL,
    max_attempts=1,
    retry_wait_seconds=0.0,
)


_PROFILE_COMMAND_POLICIES: dict[str, dict[str, CommandPolicy]] = {
    "midea_kjr_12b_dp_t": {
        "default": _DEFAULT_COMMAND_POLICY,
        "power_off": CommandPolicy(
            criticality=CommandCriticality.CRITICAL,
            max_attempts=3,
            retry_wait_seconds=2.0,
        ),
        "power_on": CommandPolicy(
            criticality=CommandCriticality.IMPORTANT,
            max_attempts=2,
            retry_wait_seconds=2.0,
        ),
        "set_mode": CommandPolicy(
            criticality=CommandCriticality.IMPORTANT,
            max_attempts=2,
            retry_wait_seconds=1.5,
        ),
        "set_temperature": CommandPolicy(
            criticality=CommandCriticality.NORMAL,
            max_attempts=2,
            retry_wait_seconds=1.5,
        ),
        "set_fan": CommandPolicy(
            criticality=CommandCriticality.NORMAL,
            max_attempts=1,
            retry_wait_seconds=0.0,
        ),
    },
}


def list_profiles() -> list[ThermostatProfile]:
    return list(_PROFILES.values())


def get_profile(profile_id: str) -> ThermostatProfile:
    profile = _PROFILES.get(profile_id)
    if profile is None:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(f"unknown thermostat profile '{profile_id}'. known: {known}")
    return profile


def get_command_policy(profile_id: str, command_name: str) -> CommandPolicy:
    policies = _PROFILE_COMMAND_POLICIES.get(profile_id)
    if not policies:
        return _DEFAULT_COMMAND_POLICY

    key = command_name.strip().lower()
    return policies.get(key, policies.get("default", _DEFAULT_COMMAND_POLICY))


def list_supported_commands(profile_id: str) -> tuple[str, ...]:
    policies = _PROFILE_COMMAND_POLICIES.get(profile_id)
    if not policies:
        return ()
    return tuple(sorted(k for k in policies.keys() if k != "default"))
