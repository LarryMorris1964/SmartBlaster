from pathlib import Path

import smartblaster.bootstrap as bootstrap
import smartblaster.provisioning.system as system
from smartblaster.bootstrap import _apply_setup_state_to_env, _load_setup_state, _resolve_mode
from smartblaster.services.runtime import RuntimeNetworkUnavailable


def test_resolve_mode_auto_without_state_uses_setup() -> None:
    assert _resolve_mode("auto", state_exists=False) == "setup"


def test_resolve_mode_auto_with_state_uses_run() -> None:
    assert _resolve_mode("auto", state_exists=True) == "run"


def test_resolve_mode_auto_with_force_setup_flag_uses_setup() -> None:
    assert (
        _resolve_mode(
            "auto",
            state_exists=True,
            setup_state={"force_setup_on_next_boot": True},
        )
        == "setup"
    )


def test_resolve_mode_explicit_run() -> None:
    assert _resolve_mode("run", state_exists=False) == "run"


def test_apply_setup_state_to_env_sets_expected_values(monkeypatch) -> None:
    keys = [
        "SMARTBLASTER_DEVICE_NAME",
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
        "SMARTBLASTER_REFERENCE_OFFLOAD_ENABLED",
        "SMARTBLASTER_REFERENCE_OFFLOAD_INTERVAL_MINUTES",
        "SMARTBLASTER_REFERENCE_OFFLOAD_BATCH_SIZE",
        "SMARTBLASTER_CONFIG_SCHEMA_VERSION",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    _apply_setup_state_to_env(
        {
            "device_name": "Hallway SmartBlaster",
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
            "reference_offload_enabled": True,
            "reference_offload_interval_minutes": 20,
            "reference_offload_batch_size": 40,
            "config_schema_version": 1,
        }
    )

    import os

    assert os.environ["SMARTBLASTER_DEVICE_NAME"] == "Hallway SmartBlaster"
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
    assert os.environ["SMARTBLASTER_REFERENCE_OFFLOAD_ENABLED"] == "true"
    assert os.environ["SMARTBLASTER_REFERENCE_OFFLOAD_INTERVAL_MINUTES"] == "20"
    assert os.environ["SMARTBLASTER_REFERENCE_OFFLOAD_BATCH_SIZE"] == "40"
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


def test_load_setup_state_migrates_legacy_payload(tmp_path) -> None:
    state_file = tmp_path / "device_setup.json"
    state_file.write_text('{"wifi_ssid":"HomeWiFi"}', encoding="utf-8")

    loaded = _load_setup_state(state_file)

    assert loaded["setup_state_version"] == 1
    assert loaded["config_schema_version"] == 1
    assert loaded["device_name"] == "SmartBlaster"


def test_run_runtime_network_failure_sets_force_setup_and_requests_reboot(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "device_setup.json"
    state_file.write_text('{"wifi_ssid": "HomeWiFi", "config_schema_version": 1}', encoding="utf-8")

    class FakeRuntime:
        def run_forever(self) -> None:
            raise RuntimeNetworkUnavailable("network unavailable")

    class FakeRuntimeFactory:
        @staticmethod
        def from_env() -> FakeRuntime:
            return FakeRuntime()

    reboot_requested = {"called": False}

    def fake_reboot() -> None:
        reboot_requested["called"] = True

    monkeypatch.setattr(bootstrap, "SmartBlasterRuntime", FakeRuntimeFactory)
    monkeypatch.setattr(bootstrap, "request_reboot", fake_reboot)

    code = bootstrap._run_runtime(state_file)

    assert code == 75
    assert reboot_requested["called"] is True
    loaded = bootstrap._load_setup_state(state_file)
    assert loaded["force_setup_on_next_boot"] is True


def test_reboot_commands_from_env_default_is_auto(monkeypatch) -> None:
    monkeypatch.delenv("SMARTBLASTER_REBOOT_COMMAND", raising=False)

    commands = bootstrap._reboot_commands_from_env()

    assert commands == [["systemctl", "reboot"], ["reboot"]]


def test_reboot_commands_from_env_allowlisted_value(monkeypatch) -> None:
    monkeypatch.setenv("SMARTBLASTER_REBOOT_COMMAND", "reboot")

    commands = bootstrap._reboot_commands_from_env()

    assert commands == [["reboot"]]


def test_request_reboot_tries_until_success(monkeypatch) -> None:
    monkeypatch.setenv("SMARTBLASTER_REBOOT_COMMAND", "auto")
    calls: list[list[str]] = []

    class DummyResult:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

    def fake_run(command, check, capture_output, text):  # noqa: ANN001, ARG001
        calls.append(command)
        if command == ["systemctl", "reboot"]:
            return DummyResult(returncode=1)
        return DummyResult(returncode=0)

    monkeypatch.setattr(system.subprocess, "run", fake_run)

    system.request_reboot()

    assert calls == [["systemctl", "reboot"], ["reboot"]]


def test_setup_auto_recover_loop_reboots_when_network_returns(monkeypatch) -> None:
    checks = {"count": 0}
    rebooted = {"called": False}

    def fake_network_checker() -> bool:
        checks["count"] += 1
        return checks["count"] >= 2

    def fake_reboot() -> None:
        rebooted["called"] = True

    monkeypatch.setattr(bootstrap.time, "sleep", lambda _seconds: None)

    bootstrap._setup_auto_recover_loop(
        grace_seconds=0,
        check_seconds=30,
        network_checker=fake_network_checker,
        reboot_action=fake_reboot,
    )

    assert rebooted["called"] is True
