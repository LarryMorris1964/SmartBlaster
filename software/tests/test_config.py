from smartblaster.config import RuntimeConfig, from_env


def test_default_runtime_config() -> None:
    cfg = RuntimeConfig()
    assert cfg.device_name == "SmartBlaster"
    assert cfg.ir_tx_gpio == 4
    assert cfg.ir_rx_gpio == 17
    assert cfg.loop_interval_ms == 500
    assert cfg.daily_on_time == "10:00"
    assert cfg.daily_off_time == "15:00"
    assert cfg.active_days_csv == "mon,tue,wed,thu,fri,sat,sun"
    assert cfg.solar_weekly_schedule == {}
    assert cfg.timezone == "UTC"
    assert cfg.target_temperature_c == 26.0
    assert cfg.fan_mode == "auto"
    assert cfg.swing_mode == "off"
    assert cfg.preset_mode == "none"
    assert cfg.camera_enabled is False
    assert cfg.thermostat_profile_id == "midea_kjr_12b_dp_t"
    assert cfg.thermostat_temperature_unit == "C"
    assert cfg.inverter_source_enabled is False
    assert cfg.inverter_source_type == "none"
    assert cfg.inverter_surplus_start_w == 0
    assert cfg.inverter_surplus_stop_w == 0
    assert cfg.status_history_file == "data/thermostat_status_history.log"
    assert cfg.status_diagnostic_mode is False
    assert cfg.status_image_dir == "data/status_images"
    assert cfg.reference_image_dir == "data/reference_images"
    assert cfg.reference_capture_on_parse_failure is True
    assert cfg.training_mode_enabled is False
    assert cfg.training_capture_interval_minutes == 60
    assert cfg.validate_capabilities_enabled is False
    assert cfg.reference_offload_enabled is False
    assert cfg.reference_offload_interval_minutes == 15
    assert cfg.reference_offload_batch_size == 25
    assert cfg.config_schema_version == 1


def test_from_env_parses_weekly_schedule(monkeypatch) -> None:
    monkeypatch.setenv(
        "SMARTBLASTER_SOLAR_WEEKLY_SCHEDULE_JSON",
        '{"mon":{"on_time":"09:30","off_time":"15:10"},"sun":{"on":"10:00","off":"14:00"}}',
    )
    cfg = from_env()
    assert cfg.solar_weekly_schedule["mon"]["on_time"] == "09:30"
    assert cfg.solar_weekly_schedule["mon"]["off_time"] == "15:10"
    assert cfg.solar_weekly_schedule["sun"]["on_time"] == "10:00"
    assert cfg.solar_weekly_schedule["sun"]["off_time"] == "14:00"
