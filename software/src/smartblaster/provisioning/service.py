"""Captive portal provisioning logic (framework-agnostic core)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

from smartblaster.ir.command import MideaFan, MideaPreset, MideaSwing
from smartblaster.provisioning.network import WifiConfigurator
from smartblaster.provisioning.state import persist_setup_state
from smartblaster.thermostats.library import get_profile, list_profiles


@dataclass(frozen=True)
class SetupRequest:
    wifi_ssid: str
    wifi_password: str
    thermostat_profile_id: str
    camera_enabled: bool
    device_name: str = "SmartBlaster"
    daily_on_time: str = "10:00"
    daily_off_time: str = "15:00"
    solar_weekly_schedule: dict[str, dict[str, str]] | None = None
    target_temperature_c: float = 26.0
    timezone: str = "UTC"
    active_days: list[str] | None = None
    fan_mode: str = "auto"
    swing_mode: str = "off"
    preset_mode: str = "none"
    thermostat_temperature_unit: str = "C"
    inverter_source_enabled: bool = False
    inverter_source_type: str = "none"
    inverter_surplus_start_w: int = 0
    inverter_surplus_stop_w: int = 0
    status_history_file: str = "data/thermostat_status_history.log"
    status_diagnostic_mode: bool = False
    status_image_dir: str = "data/status_images"
    reference_image_dir: str = "data/reference_images"
    reference_capture_on_parse_failure: bool = True
    training_mode_enabled: bool = False
    training_capture_interval_minutes: int = 60
    validate_capabilities_enabled: bool = False
    reference_offload_enabled: bool = False
    reference_offload_interval_minutes: int = 15
    reference_offload_batch_size: int = 25
    config_schema_version: int = 1


@dataclass(frozen=True)
class SetupResult:
    ok: bool
    message: str
    profile_id: str | None = None


class ProvisioningService:
    """Stores setup choices and validates minimum launch constraints.

    Notes:
    - Real Wi-Fi verification should be implemented via NetworkManager (`nmcli`) integration.
    - This service keeps logic reusable by both a captive web portal and future BLE app flow.
    """

    def __init__(
        self,
        *,
        state_file: Path | None = None,
        wifi_configurator: WifiConfigurator | None = None,
    ) -> None:
        self.state_file = state_file or Path("data/device_setup.json")
        self.wifi_configurator = wifi_configurator

    def available_thermostats(self) -> list[dict[str, object]]:
        return [asdict(p) for p in list_profiles()]

    def apply_setup(self, request: SetupRequest) -> SetupResult:
        self._validate_request(request)

        if not self._verify_wifi_credentials(request.wifi_ssid, request.wifi_password):
            return SetupResult(ok=False, message="Wi-Fi verification failed")

        self._persist_setup(request)
        return SetupResult(
            ok=True,
            message="Setup saved. Device can exit captive portal mode.",
            profile_id=request.thermostat_profile_id,
        )

    def _validate_request(self, request: SetupRequest) -> None:
        if not request.device_name.strip():
            raise ValueError("device_name is required")
        if not request.wifi_ssid.strip():
            raise ValueError("wifi_ssid is required")
        if len(request.wifi_password) < 8:
            raise ValueError("wifi_password must be at least 8 characters")

        if not _is_valid_hhmm(request.daily_on_time):
            raise ValueError("daily_on_time must be HH:MM (24-hour)")
        if not _is_valid_hhmm(request.daily_off_time):
            raise ValueError("daily_off_time must be HH:MM (24-hour)")

        _validate_weekly_schedule(request.solar_weekly_schedule)

        if not (16.0 <= request.target_temperature_c <= 30.0):
            raise ValueError("target_temperature_c must be between 16 and 30")

        if not request.timezone.strip():
            raise ValueError("timezone is required")

        active_days = request.active_days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        _validate_active_days(active_days)

        MideaFan(request.fan_mode)
        MideaSwing(request.swing_mode)
        MideaPreset(request.preset_mode)

        if request.thermostat_temperature_unit.strip().upper() not in {"C", "F"}:
            raise ValueError("thermostat_temperature_unit must be C or F")

        if request.inverter_surplus_start_w < 0 or request.inverter_surplus_stop_w < 0:
            raise ValueError("inverter surplus thresholds must be non-negative")
        if request.inverter_surplus_start_w < request.inverter_surplus_stop_w:
            raise ValueError("inverter_surplus_start_w must be >= inverter_surplus_stop_w")
        if request.inverter_source_enabled and request.inverter_source_type.strip().lower() == "none":
            raise ValueError("inverter_source_type is required when inverter_source_enabled is true")
        if not request.status_history_file.strip():
            raise ValueError("status_history_file is required")
        if not request.status_image_dir.strip():
            raise ValueError("status_image_dir is required")
        if not request.reference_image_dir.strip():
            raise ValueError("reference_image_dir is required")
        if request.training_capture_interval_minutes < 1:
            raise ValueError("training_capture_interval_minutes must be >= 1")
        if request.reference_offload_interval_minutes < 1:
            raise ValueError("reference_offload_interval_minutes must be >= 1")
        if request.reference_offload_batch_size < 1:
            raise ValueError("reference_offload_batch_size must be >= 1")
        if request.config_schema_version < 1:
            raise ValueError("config_schema_version must be >= 1")

        profile = get_profile(request.thermostat_profile_id)
        selected_unit = request.thermostat_temperature_unit.strip().upper()
        if selected_unit not in profile.supported_temperature_units:
            raise ValueError(
                f"thermostat profile {request.thermostat_profile_id} does not support temperature unit {selected_unit}"
            )
        if request.camera_enabled and not profile.camera_supported:
            raise ValueError(
                f"camera routines are not yet available for profile {request.thermostat_profile_id}"
            )

    def _verify_wifi_credentials(self, ssid: str, password: str) -> bool:
        if self.wifi_configurator is not None:
            return self.wifi_configurator.connect_to_home_wifi(ssid, password)

        # Fallback placeholder check when no system connector is wired in.
        return bool(ssid.strip()) and len(password) >= 8

    def _persist_setup(self, request: SetupRequest) -> None:
        payload = {
            "device_name": request.device_name.strip(),
            "wifi_ssid": request.wifi_ssid,
            "thermostat_profile_id": request.thermostat_profile_id,
            "camera_enabled": request.camera_enabled,
            "daily_on_time": request.daily_on_time,
            "daily_off_time": request.daily_off_time,
            # The simple daily fields remain for backward compatibility and to preload the
            # simple UI, but runtime scheduling is driven from the per-weekday map below.
            "solar_weekly_schedule": _normalize_weekly_schedule(request.solar_weekly_schedule),
            "target_temperature_c": request.target_temperature_c,
            "timezone": request.timezone,
            "active_days": _normalize_active_days(request.active_days),
            "fan_mode": request.fan_mode,
            "swing_mode": request.swing_mode,
            "preset_mode": request.preset_mode,
            "thermostat_temperature_unit": request.thermostat_temperature_unit.strip().upper(),
            "inverter_source_enabled": request.inverter_source_enabled,
            "inverter_source_type": request.inverter_source_type,
            "inverter_surplus_start_w": request.inverter_surplus_start_w,
            "inverter_surplus_stop_w": request.inverter_surplus_stop_w,
            "status_history_file": request.status_history_file,
            "status_diagnostic_mode": request.status_diagnostic_mode,
            "status_image_dir": request.status_image_dir,
            "reference_image_dir": request.reference_image_dir,
            "reference_capture_on_parse_failure": request.reference_capture_on_parse_failure,
            "training_mode_enabled": request.training_mode_enabled,
            "training_capture_interval_minutes": request.training_capture_interval_minutes,
            "validate_capabilities_enabled": request.validate_capabilities_enabled,
            "reference_offload_enabled": request.reference_offload_enabled,
            "reference_offload_interval_minutes": request.reference_offload_interval_minutes,
            "reference_offload_batch_size": request.reference_offload_batch_size,
            "config_schema_version": request.config_schema_version,
        }
        persist_setup_state(self.state_file, payload)


def _is_valid_hhmm(value: str) -> bool:
    if not re.match(r"^\d{2}:\d{2}$", value):
        return False
    hour, minute = value.split(":", maxsplit=1)
    return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59


def _normalize_active_days(active_days: list[str] | None) -> list[str]:
    if not active_days:
        return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return [item.strip().lower() for item in active_days if item.strip()]


def _validate_active_days(active_days: list[str]) -> None:
    valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    normalized = _normalize_active_days(active_days)
    if not normalized:
        raise ValueError("active_days must include at least one day")
    invalid = [item for item in normalized if item not in valid_days]
    if invalid:
        raise ValueError(f"active_days has invalid values: {', '.join(invalid)}")


def _normalize_weekly_schedule(schedule: dict[str, dict[str, str]] | None) -> dict[str, dict[str, str]]:
    if not schedule:
        return {}
        # Persist the canonical schedule shape as explicit weekday entries. The simple UI
        # also saves into this structure after copying one shared time across all days.
    normalized: dict[str, dict[str, str]] = {}
    for day, entry in schedule.items():
        normalized[str(day).strip().lower()] = {
            "on_time": str(entry.get("on_time", "")).strip(),
            "off_time": str(entry.get("off_time", "")).strip(),
        }
    return normalized


def _validate_weekly_schedule(schedule: dict[str, dict[str, str]] | None) -> None:
    if not schedule:
        return

    valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    for raw_day, raw_entry in schedule.items():
        day = str(raw_day).strip().lower()
        if day not in valid_days:
            raise ValueError(f"solar_weekly_schedule has invalid day: {raw_day}")
        if not isinstance(raw_entry, dict):
            raise ValueError(f"solar_weekly_schedule.{day} must be an object")

        on_time = str(raw_entry.get("on_time", "")).strip()
        off_time = str(raw_entry.get("off_time", "")).strip()
        if not _is_valid_hhmm(on_time):
            raise ValueError(f"solar_weekly_schedule.{day}.on_time must be HH:MM")
        if not _is_valid_hhmm(off_time):
            raise ValueError(f"solar_weekly_schedule.{day}.off_time must be HH:MM")
