"""Configuration loading for SmartBlaster."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RuntimeConfig:
    log_level: str = "INFO"
    dry_run: bool = True
    ir_tx_gpio: int = 4
    ir_rx_gpio: int = 17
    loop_interval_ms: int = 500
    daily_on_time: str = "10:00"
    daily_off_time: str = "16:00"
    active_days_csv: str = "mon,tue,wed,thu,fri,sat,sun"
    timezone: str = "UTC"
    target_temperature_c: float = 24.0
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
    config_schema_version: int = 1



def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}



def from_env() -> RuntimeConfig:
    return RuntimeConfig(
        log_level=os.getenv("SMARTBLASTER_LOG_LEVEL", "INFO"),
        dry_run=_env_bool("SMARTBLASTER_DRY_RUN", True),
        ir_tx_gpio=int(os.getenv("SMARTBLASTER_IR_TX_GPIO", "4")),
        ir_rx_gpio=int(os.getenv("SMARTBLASTER_IR_RX_GPIO", "17")),
        loop_interval_ms=int(os.getenv("SMARTBLASTER_LOOP_INTERVAL_MS", "500")),
        daily_on_time=os.getenv("SMARTBLASTER_DAILY_ON_TIME", "10:00"),
        daily_off_time=os.getenv("SMARTBLASTER_DAILY_OFF_TIME", "16:00"),
        active_days_csv=os.getenv("SMARTBLASTER_ACTIVE_DAYS", "mon,tue,wed,thu,fri,sat,sun"),
        timezone=os.getenv("SMARTBLASTER_TIMEZONE", "UTC"),
        target_temperature_c=float(os.getenv("SMARTBLASTER_TARGET_TEMPERATURE_C", "24")),
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
        config_schema_version=int(os.getenv("SMARTBLASTER_CONFIG_SCHEMA_VERSION", "1")),
    )
