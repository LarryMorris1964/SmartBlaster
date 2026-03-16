from smartblaster.bootstrap import _apply_setup_state_to_env, _resolve_mode


def test_resolve_mode_auto_without_state_uses_setup() -> None:
    assert _resolve_mode("auto", state_exists=False) == "setup"


def test_resolve_mode_auto_with_state_uses_run() -> None:
    assert _resolve_mode("auto", state_exists=True) == "run"


def test_resolve_mode_explicit_run() -> None:
    assert _resolve_mode("run", state_exists=False) == "run"


def test_apply_setup_state_to_env_sets_expected_values(monkeypatch) -> None:
    keys = [
        "SMARTBLASTER_THERMOSTAT_PROFILE_ID",
        "SMARTBLASTER_CAMERA_ENABLED",
        "SMARTBLASTER_DAILY_ON_TIME",
        "SMARTBLASTER_DAILY_OFF_TIME",
        "SMARTBLASTER_TARGET_TEMPERATURE_C",
        "SMARTBLASTER_TIMEZONE",
        "SMARTBLASTER_ACTIVE_DAYS",
        "SMARTBLASTER_FAN_MODE",
        "SMARTBLASTER_SWING_MODE",
        "SMARTBLASTER_PRESET_MODE",
        "SMARTBLASTER_THERMOSTAT_TEMPERATURE_UNIT",
        "SMARTBLASTER_INVERTER_SOURCE_ENABLED",
        "SMARTBLASTER_INVERTER_SOURCE_TYPE",
        "SMARTBLASTER_INVERTER_SURPLUS_START_W",
        "SMARTBLASTER_INVERTER_SURPLUS_STOP_W",
        "SMARTBLASTER_STATUS_HISTORY_FILE",
        "SMARTBLASTER_STATUS_DIAGNOSTIC_MODE",
        "SMARTBLASTER_STATUS_IMAGE_DIR",
        "SMARTBLASTER_REFERENCE_IMAGE_DIR",
        "SMARTBLASTER_REFERENCE_CAPTURE_ON_PARSE_FAILURE",
        "SMARTBLASTER_TRAINING_MODE_ENABLED",
        "SMARTBLASTER_TRAINING_CAPTURE_INTERVAL_MINUTES",
        "SMARTBLASTER_VALIDATE_CAPABILITIES_ENABLED",
        "SMARTBLASTER_CONFIG_SCHEMA_VERSION",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)

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
            "status_history_file": "data/thermostat_status_history.log",
            "status_diagnostic_mode": True,
            "status_image_dir": "data/status_images",
            "reference_image_dir": "data/reference_images",
            "reference_capture_on_parse_failure": True,
            "training_mode_enabled": True,
            "training_capture_interval_minutes": 60,
            "validate_capabilities_enabled": True,
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
    assert os.environ["SMARTBLASTER_STATUS_HISTORY_FILE"] == "data/thermostat_status_history.log"
    assert os.environ["SMARTBLASTER_STATUS_DIAGNOSTIC_MODE"] == "true"
    assert os.environ["SMARTBLASTER_STATUS_IMAGE_DIR"] == "data/status_images"
    assert os.environ["SMARTBLASTER_REFERENCE_IMAGE_DIR"] == "data/reference_images"
    assert os.environ["SMARTBLASTER_REFERENCE_CAPTURE_ON_PARSE_FAILURE"] == "true"
    assert os.environ["SMARTBLASTER_TRAINING_MODE_ENABLED"] == "true"
    assert os.environ["SMARTBLASTER_TRAINING_CAPTURE_INTERVAL_MINUTES"] == "60"
    assert os.environ["SMARTBLASTER_VALIDATE_CAPABILITIES_ENABLED"] == "true"
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
