from pathlib import Path

from smartblaster.bootstrap import _apply_setup_state_to_env, _resolve_mode


def test_resolve_mode_auto_without_state_uses_setup() -> None:
    assert _resolve_mode("auto", state_exists=False) == "setup"



def test_resolve_mode_auto_with_state_uses_run() -> None:
    assert _resolve_mode("auto", state_exists=True) == "run"



def test_resolve_mode_explicit_run() -> None:
    assert _resolve_mode("run", state_exists=False) == "run"


def test_apply_setup_state_to_env_sets_expected_values(monkeypatch) -> None:
    monkeypatch.delenv("SMARTBLASTER_THERMOSTAT_PROFILE_ID", raising=False)
    monkeypatch.delenv("SMARTBLASTER_CAMERA_ENABLED", raising=False)
    monkeypatch.delenv("SMARTBLASTER_DAILY_ON_TIME", raising=False)
    monkeypatch.delenv("SMARTBLASTER_DAILY_OFF_TIME", raising=False)
    monkeypatch.delenv("SMARTBLASTER_TARGET_TEMPERATURE_C", raising=False)
    monkeypatch.delenv("SMARTBLASTER_TIMEZONE", raising=False)
    monkeypatch.delenv("SMARTBLASTER_ACTIVE_DAYS", raising=False)
    monkeypatch.delenv("SMARTBLASTER_FAN_MODE", raising=False)
    monkeypatch.delenv("SMARTBLASTER_SWING_MODE", raising=False)
    monkeypatch.delenv("SMARTBLASTER_PRESET_MODE", raising=False)
    monkeypatch.delenv("SMARTBLASTER_THERMOSTAT_TEMPERATURE_UNIT", raising=False)
    monkeypatch.delenv("SMARTBLASTER_INVERTER_SOURCE_ENABLED", raising=False)
    monkeypatch.delenv("SMARTBLASTER_INVERTER_SOURCE_TYPE", raising=False)
    monkeypatch.delenv("SMARTBLASTER_INVERTER_SURPLUS_START_W", raising=False)
    monkeypatch.delenv("SMARTBLASTER_INVERTER_SURPLUS_STOP_W", raising=False)
    monkeypatch.delenv("SMARTBLASTER_CONFIG_SCHEMA_VERSION", raising=False)

    _apply_setup_state_to_env(
        {
            "thermostat_profile_id": "midea_kjr_12b_dp_t",
            "camera_enabled": True,
            "daily_on_time": "09:00",
            "daily_off_time": "18:30",
            "target_temperature_c": 23.0,
            "timezone": "America/Los_Angeles",
            "active_days": ["mon", "tue", "wed"],
            "fan_mode": "auto",
            "swing_mode": "off",
            "preset_mode": "none",
            "thermostat_temperature_unit": "F",
            "inverter_source_enabled": True,
            "inverter_source_type": "modbus-tcp",
            "inverter_surplus_start_w": 1800,
            "inverter_surplus_stop_w": 700,
            "config_schema_version": 1,
        }
    )

    import os

    assert os.environ["SMARTBLASTER_THERMOSTAT_PROFILE_ID"] == "midea_kjr_12b_dp_t"
    assert os.environ["SMARTBLASTER_CAMERA_ENABLED"] == "true"
    assert os.environ["SMARTBLASTER_DAILY_ON_TIME"] == "09:00"
    assert os.environ["SMARTBLASTER_DAILY_OFF_TIME"] == "18:30"
    assert os.environ["SMARTBLASTER_TARGET_TEMPERATURE_C"] == "23.0"
    assert os.environ["SMARTBLASTER_TIMEZONE"] == "America/Los_Angeles"
    assert os.environ["SMARTBLASTER_ACTIVE_DAYS"] == "mon,tue,wed"
    assert os.environ["SMARTBLASTER_FAN_MODE"] == "auto"
    assert os.environ["SMARTBLASTER_SWING_MODE"] == "off"
    assert os.environ["SMARTBLASTER_PRESET_MODE"] == "none"
    assert os.environ["SMARTBLASTER_THERMOSTAT_TEMPERATURE_UNIT"] == "F"
    assert os.environ["SMARTBLASTER_INVERTER_SOURCE_ENABLED"] == "true"
    assert os.environ["SMARTBLASTER_INVERTER_SOURCE_TYPE"] == "modbus-tcp"
    assert os.environ["SMARTBLASTER_INVERTER_SURPLUS_START_W"] == "1800"
    assert os.environ["SMARTBLASTER_INVERTER_SURPLUS_STOP_W"] == "700"
    assert os.environ["SMARTBLASTER_CONFIG_SCHEMA_VERSION"] == "1"


def test_apply_setup_state_to_env_ignores_invalid_values(monkeypatch) -> None:
    monkeypatch.delenv("SMARTBLASTER_DAILY_ON_TIME", raising=False)
    monkeypatch.delenv("SMARTBLASTER_TARGET_TEMPERATURE_C", raising=False)

    _apply_setup_state_to_env(
        {
            "daily_on_time": "99:00",
            "target_temperature_c": "not-a-number",
        }
    )

    import os

    assert "SMARTBLASTER_DAILY_ON_TIME" not in os.environ
    assert "SMARTBLASTER_TARGET_TEMPERATURE_C" not in os.environ
