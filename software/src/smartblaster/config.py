"""Configuration loading for SmartBlaster."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re

_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class RuntimeConfig:
    device_name: str = "SmartBlaster"
    log_level: str = "INFO"
    dry_run: bool = True
    ir_tx_gpio: int = 4
    ir_rx_gpio: int = 17
    loop_interval_ms: int = 500
    daily_on_time: str = "10:00"
    daily_off_time: str = "15:00"
    active_days_csv: str = "mon,tue,wed,thu,fri,sat,sun"
    solar_weekly_schedule: dict[str, dict[str, str]] = field(default_factory=dict)
    timezone: str = "UTC"
    target_temperature_c: float = 26.0
    fan_mode: str = "auto"
    swing_mode: str = "off"
    preset_mode: str = "none"
    camera_enabled: bool = False
    thermostat_profile_id: str = "midea_kjr_12b_dp_t"
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
    activity_log_file: str = "data/activity_log.jsonl"



def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_valid_hhmm(value: str) -> bool:
    if not re.match(r"^\d{2}:\d{2}$", value):
        return False
    hour, minute = value.split(":", maxsplit=1)
    return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59


def _parse_weekly_schedule(raw: str) -> dict[str, dict[str, str]]:
    text = raw.strip()
    if not text:
        return {}

    try:
        data = json.loads(text)
    except Exception as ex:
        raise ValueError("SMARTBLASTER_SOLAR_WEEKLY_SCHEDULE_JSON must be valid JSON") from ex

    if not isinstance(data, dict):
        raise ValueError("SMARTBLASTER_SOLAR_WEEKLY_SCHEDULE_JSON must be an object")

    schedule: dict[str, dict[str, str]] = {}
    for key, value in data.items():
        day = str(key).strip().lower()
        if day not in _WEEKDAY_KEYS:
            raise ValueError(f"invalid weekday in weekly schedule: {key}")
        if not isinstance(value, dict):
            raise ValueError(f"schedule entry for {day} must be an object")

        on_time = str(value.get("on_time", value.get("on", ""))).strip()
        off_time = str(value.get("off_time", value.get("off", ""))).strip()
        if not _is_valid_hhmm(on_time):
            raise ValueError(f"invalid on_time for {day}: {on_time}")
        if not _is_valid_hhmm(off_time):
            raise ValueError(f"invalid off_time for {day}: {off_time}")

        schedule[day] = {"on_time": on_time, "off_time": off_time}
    return schedule



def from_env() -> RuntimeConfig:
    return RuntimeConfig(
        device_name=os.getenv("SMARTBLASTER_DEVICE_NAME", "SmartBlaster"),
        log_level=os.getenv("SMARTBLASTER_LOG_LEVEL", "INFO"),
        dry_run=_env_bool("SMARTBLASTER_DRY_RUN", True),
        ir_tx_gpio=int(os.getenv("SMARTBLASTER_IR_TX_GPIO", "4")),
        ir_rx_gpio=int(os.getenv("SMARTBLASTER_IR_RX_GPIO", "17")),
        loop_interval_ms=int(os.getenv("SMARTBLASTER_LOOP_INTERVAL_MS", "500")),
        daily_on_time=os.getenv("SMARTBLASTER_DAILY_ON_TIME", "10:00"),
        daily_off_time=os.getenv("SMARTBLASTER_DAILY_OFF_TIME", "15:00"),
        active_days_csv=os.getenv("SMARTBLASTER_ACTIVE_DAYS", "mon,tue,wed,thu,fri,sat,sun"),
        solar_weekly_schedule=_parse_weekly_schedule(os.getenv("SMARTBLASTER_SOLAR_WEEKLY_SCHEDULE_JSON", "")),
        timezone=os.getenv("SMARTBLASTER_TIMEZONE", "UTC"),
        target_temperature_c=float(os.getenv("SMARTBLASTER_TARGET_TEMPERATURE_C", "26")),
        fan_mode=os.getenv("SMARTBLASTER_FAN_MODE", "auto"),
        swing_mode=os.getenv("SMARTBLASTER_SWING_MODE", "off"),
        preset_mode=os.getenv("SMARTBLASTER_PRESET_MODE", "none"),
        camera_enabled=_env_bool("SMARTBLASTER_CAMERA_ENABLED", False),
        thermostat_profile_id=os.getenv("SMARTBLASTER_THERMOSTAT_PROFILE_ID", "midea_kjr_12b_dp_t"),
        thermostat_temperature_unit=os.getenv("SMARTBLASTER_THERMOSTAT_TEMPERATURE_UNIT", "C"),
        inverter_source_enabled=_env_bool("SMARTBLASTER_INVERTER_SOURCE_ENABLED", False),
        inverter_source_type=os.getenv("SMARTBLASTER_INVERTER_SOURCE_TYPE", "none"),
        inverter_surplus_start_w=int(os.getenv("SMARTBLASTER_INVERTER_SURPLUS_START_W", "0")),
        inverter_surplus_stop_w=int(os.getenv("SMARTBLASTER_INVERTER_SURPLUS_STOP_W", "0")),
        status_history_file=os.getenv("SMARTBLASTER_STATUS_HISTORY_FILE", "data/thermostat_status_history.log"),
        status_diagnostic_mode=_env_bool("SMARTBLASTER_STATUS_DIAGNOSTIC_MODE", False),
        status_image_dir=os.getenv("SMARTBLASTER_STATUS_IMAGE_DIR", "data/status_images"),
        reference_image_dir=os.getenv("SMARTBLASTER_REFERENCE_IMAGE_DIR", "data/reference_images"),
        reference_capture_on_parse_failure=_env_bool("SMARTBLASTER_REFERENCE_CAPTURE_ON_PARSE_FAILURE", True),
        training_mode_enabled=_env_bool("SMARTBLASTER_TRAINING_MODE_ENABLED", False),
        training_capture_interval_minutes=int(os.getenv("SMARTBLASTER_TRAINING_CAPTURE_INTERVAL_MINUTES", "60")),
        validate_capabilities_enabled=_env_bool("SMARTBLASTER_VALIDATE_CAPABILITIES_ENABLED", False),
        reference_offload_enabled=_env_bool("SMARTBLASTER_REFERENCE_OFFLOAD_ENABLED", False),
        reference_offload_interval_minutes=int(os.getenv("SMARTBLASTER_REFERENCE_OFFLOAD_INTERVAL_MINUTES", "15")),
        reference_offload_batch_size=int(os.getenv("SMARTBLASTER_REFERENCE_OFFLOAD_BATCH_SIZE", "25")),
        config_schema_version=int(os.getenv("SMARTBLASTER_CONFIG_SCHEMA_VERSION", "1")),
        activity_log_file=os.getenv("SMARTBLASTER_ACTIVITY_LOG_FILE", "data/activity_log.jsonl"),
    )
