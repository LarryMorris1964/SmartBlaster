"""Device bootstrap: choose setup portal vs runtime mode."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import threading
import time

import uvicorn

from smartblaster.provisioning.ap_mode import ApModeController
from smartblaster.provisioning.service import ProvisioningService
from smartblaster.provisioning.state import load_setup_state, persist_setup_state
from smartblaster.provisioning.system import network_connected_best_effort, request_reboot, reboot_commands_from_env
from smartblaster.provisioning.web import create_provisioning_app
from smartblaster.services.activity_log import ActivityLogger
from smartblaster.services.runtime import RuntimeNetworkUnavailable, SmartBlasterRuntime


def _setup_state_exists(state_file: Path) -> bool:
    return state_file.exists()


def _resolve_mode(requested_mode: str, *, state_exists: bool, setup_state: dict[str, object] | None = None) -> str:
    requested = requested_mode.lower().strip()
    if requested not in {"auto", "setup", "run"}:
        raise ValueError("mode must be one of: auto, setup, run")

    if requested == "auto":
        if state_exists and isinstance(setup_state, dict) and setup_state.get("force_setup_on_next_boot") is True:
            return "setup"
        return "run" if state_exists else "setup"
    return requested


def _load_setup_state(state_file: Path) -> dict[str, object]:
    return load_setup_state(state_file)


def _apply_setup_state_to_env(setup: dict[str, object]) -> None:
    device_name = setup.get("device_name")
    if isinstance(device_name, str) and device_name.strip():
        os.environ.setdefault("SMARTBLASTER_DEVICE_NAME", device_name.strip())

    profile_id = setup.get("thermostat_profile_id")
    if isinstance(profile_id, str) and profile_id:
        os.environ.setdefault("SMARTBLASTER_THERMOSTAT_PROFILE_ID", profile_id)

    camera_enabled = setup.get("camera_enabled")
    if isinstance(camera_enabled, bool):
        os.environ.setdefault("SMARTBLASTER_CAMERA_ENABLED", "true" if camera_enabled else "false")

    daily_on_time = setup.get("daily_on_time")
    if isinstance(daily_on_time, str) and _is_valid_hhmm(daily_on_time):
        os.environ.setdefault("SMARTBLASTER_DAILY_ON_TIME", daily_on_time)

    daily_off_time = setup.get("daily_off_time")
    if isinstance(daily_off_time, str) and _is_valid_hhmm(daily_off_time):
        os.environ.setdefault("SMARTBLASTER_DAILY_OFF_TIME", daily_off_time)

    weekly_schedule = setup.get("solar_weekly_schedule")
    if isinstance(weekly_schedule, dict) and weekly_schedule:
        os.environ.setdefault("SMARTBLASTER_SOLAR_WEEKLY_SCHEDULE_JSON", json.dumps(weekly_schedule))

    target_temperature_c = setup.get("target_temperature_c")
    if isinstance(target_temperature_c, (int, float)) and math.isfinite(float(target_temperature_c)):
        os.environ.setdefault("SMARTBLASTER_TARGET_TEMPERATURE_C", str(float(target_temperature_c)))

    timezone = setup.get("timezone")
    if isinstance(timezone, str) and timezone.strip():
        os.environ.setdefault("SMARTBLASTER_TIMEZONE", timezone)

    active_days = setup.get("active_days")
    if isinstance(active_days, list):
        normalized_days = [str(item).strip().lower() for item in active_days if str(item).strip()]
        if normalized_days:
            os.environ.setdefault("SMARTBLASTER_ACTIVE_DAYS", ",".join(normalized_days))

    fan_mode = setup.get("fan_mode")
    if isinstance(fan_mode, str) and fan_mode:
        os.environ.setdefault("SMARTBLASTER_FAN_MODE", fan_mode)

    swing_mode = setup.get("swing_mode")
    if isinstance(swing_mode, str) and swing_mode:
        os.environ.setdefault("SMARTBLASTER_SWING_MODE", swing_mode)

    preset_mode = setup.get("preset_mode")
    if isinstance(preset_mode, str) and preset_mode:
        os.environ.setdefault("SMARTBLASTER_PRESET_MODE", preset_mode)

    thermostat_temperature_unit = setup.get("thermostat_temperature_unit")
    if isinstance(thermostat_temperature_unit, str) and thermostat_temperature_unit.strip().upper() in {"C", "F"}:
        os.environ.setdefault("SMARTBLASTER_THERMOSTAT_TEMPERATURE_UNIT", thermostat_temperature_unit.strip().upper())

    inverter_source_enabled = setup.get("inverter_source_enabled")
    if isinstance(inverter_source_enabled, bool):
        os.environ.setdefault(
            "SMARTBLASTER_INVERTER_SOURCE_ENABLED",
            "true" if inverter_source_enabled else "false",
        )

    inverter_source_type = setup.get("inverter_source_type")
    if isinstance(inverter_source_type, str) and inverter_source_type.strip():
        os.environ.setdefault("SMARTBLASTER_INVERTER_SOURCE_TYPE", inverter_source_type)

    inverter_surplus_start_w = setup.get("inverter_surplus_start_w")
    if isinstance(inverter_surplus_start_w, int):
        os.environ.setdefault("SMARTBLASTER_INVERTER_SURPLUS_START_W", str(inverter_surplus_start_w))

    inverter_surplus_stop_w = setup.get("inverter_surplus_stop_w")
    if isinstance(inverter_surplus_stop_w, int):
        os.environ.setdefault("SMARTBLASTER_INVERTER_SURPLUS_STOP_W", str(inverter_surplus_stop_w))

    status_history_file = setup.get("status_history_file")
    if isinstance(status_history_file, str) and status_history_file.strip():
        os.environ.setdefault("SMARTBLASTER_STATUS_HISTORY_FILE", status_history_file)

    status_diagnostic_mode = setup.get("status_diagnostic_mode")
    if isinstance(status_diagnostic_mode, bool):
        os.environ.setdefault(
            "SMARTBLASTER_STATUS_DIAGNOSTIC_MODE",
            "true" if status_diagnostic_mode else "false",
        )

    status_image_dir = setup.get("status_image_dir")
    if isinstance(status_image_dir, str) and status_image_dir.strip():
        os.environ.setdefault("SMARTBLASTER_STATUS_IMAGE_DIR", status_image_dir)

    reference_image_dir = setup.get("reference_image_dir")
    if isinstance(reference_image_dir, str) and reference_image_dir.strip():
        os.environ.setdefault("SMARTBLASTER_REFERENCE_IMAGE_DIR", reference_image_dir)

    reference_capture_on_parse_failure = setup.get("reference_capture_on_parse_failure")
    if isinstance(reference_capture_on_parse_failure, bool):
        os.environ.setdefault(
            "SMARTBLASTER_REFERENCE_CAPTURE_ON_PARSE_FAILURE",
            "true" if reference_capture_on_parse_failure else "false",
        )

    training_mode_enabled = setup.get("training_mode_enabled")
    if isinstance(training_mode_enabled, bool):
        os.environ.setdefault(
            "SMARTBLASTER_TRAINING_MODE_ENABLED",
            "true" if training_mode_enabled else "false",
        )

    training_capture_interval_minutes = setup.get("training_capture_interval_minutes")
    if isinstance(training_capture_interval_minutes, int) and training_capture_interval_minutes >= 1:
        os.environ.setdefault(
            "SMARTBLASTER_TRAINING_CAPTURE_INTERVAL_MINUTES",
            str(training_capture_interval_minutes),
        )

    validate_capabilities_enabled = setup.get("validate_capabilities_enabled")
    if isinstance(validate_capabilities_enabled, bool):
        os.environ.setdefault(
            "SMARTBLASTER_VALIDATE_CAPABILITIES_ENABLED",
            "true" if validate_capabilities_enabled else "false",
        )

    reference_offload_enabled = setup.get("reference_offload_enabled")
    if isinstance(reference_offload_enabled, bool):
        os.environ.setdefault(
            "SMARTBLASTER_REFERENCE_OFFLOAD_ENABLED",
            "true" if reference_offload_enabled else "false",
        )

    reference_offload_interval_minutes = setup.get("reference_offload_interval_minutes")
    if isinstance(reference_offload_interval_minutes, int) and reference_offload_interval_minutes >= 1:
        os.environ.setdefault(
            "SMARTBLASTER_REFERENCE_OFFLOAD_INTERVAL_MINUTES",
            str(reference_offload_interval_minutes),
        )

    reference_offload_batch_size = setup.get("reference_offload_batch_size")
    if isinstance(reference_offload_batch_size, int) and reference_offload_batch_size >= 1:
        os.environ.setdefault(
            "SMARTBLASTER_REFERENCE_OFFLOAD_BATCH_SIZE",
            str(reference_offload_batch_size),
        )

    config_schema_version = setup.get("config_schema_version")
    if isinstance(config_schema_version, int) and config_schema_version >= 1:
        os.environ.setdefault("SMARTBLASTER_CONFIG_SCHEMA_VERSION", str(config_schema_version))


def _is_valid_hhmm(value: str) -> bool:
    if not re.match(r"^\d{2}:\d{2}$", value):
        return False
    hour, minute = value.split(":", maxsplit=1)
    return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59


def _run_setup_server(
    state_file: Path,
    host: str,
    port: int,
    *,
    enable_ap_mode: bool,
    ap_use_sudo: bool,
    ap_start_script: str,
    ap_stop_script: str,
    setup_auto_recover_enabled: bool,
) -> int:
    print("mode=setup (captive portal scaffold)")

    if setup_auto_recover_enabled:
        _start_setup_auto_recover_thread()

    ap_controller: ApModeController | None = None
    if enable_ap_mode:
        prefix = ["sudo"] if ap_use_sudo else []
        ap_controller = ApModeController(
            start_command=prefix + [ap_start_script],
            stop_command=prefix + [ap_stop_script],
        )
        started = ap_controller.start()
        print(f"ap_mode_started={started}")

    service = ProvisioningService(state_file=state_file)
    app = create_provisioning_app(service, reboot_action=request_reboot)
    try:
        uvicorn.run(app, host=host, port=port)
    finally:
        if ap_controller is not None:
            stopped = ap_controller.stop()
            print(f"ap_mode_stopped={stopped}")

    return 0


def _run_runtime(state_file: Path) -> int:
    print("mode=run")
    setup = _load_setup_state(state_file)
    _apply_setup_state_to_env(setup)
    runtime = SmartBlasterRuntime.from_env()
    try:
        runtime.run_forever()
    except RuntimeNetworkUnavailable as ex:
        setup["force_setup_on_next_boot"] = True
        persist_setup_state(state_file, setup)
        ActivityLogger().network_failover(reason=str(ex))
        request_reboot()
        return 75
    return 0


def _start_setup_auto_recover_thread() -> None:
    grace_seconds = max(0, int(os.getenv("SMARTBLASTER_SETUP_AUTO_RECOVER_GRACE_SECONDS", "120")))
    check_seconds = max(30, int(os.getenv("SMARTBLASTER_SETUP_AUTO_RECOVER_CHECK_SECONDS", "300")))

    worker = threading.Thread(
        target=_setup_auto_recover_loop,
        kwargs={
            "grace_seconds": grace_seconds,
            "check_seconds": check_seconds,
            "network_checker": network_connected_best_effort,
            "reboot_action": request_reboot,
        },
        daemon=True,
    )
    worker.start()


def _setup_auto_recover_loop(
    *,
    grace_seconds: int,
    check_seconds: int,
    network_checker,
    reboot_action,
) -> None:
    if grace_seconds > 0:
        time.sleep(grace_seconds)

    while True:
        if network_checker():
            print("setup_auto_recover_network_connected=true")
            reboot_action()
            return
        time.sleep(check_seconds)


def _reboot_commands_from_env() -> list[list[str]]:
    return reboot_commands_from_env()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SmartBlaster device bootstrap")
    parser.add_argument("--mode", default="auto", help="auto|setup|run")
    parser.add_argument("--state-file", default="data/device_setup.json")
    parser.add_argument("--setup-host", default="0.0.0.0")
    parser.add_argument("--setup-port", type=int, default=8080)
    parser.add_argument("--enable-ap-mode", action="store_true")
    parser.add_argument("--ap-use-sudo", action="store_true")
    parser.add_argument("--ap-start-script", default="./deploy/ap/start_ap_mode.sh")
    parser.add_argument("--ap-stop-script", default="./deploy/ap/stop_ap_mode.sh")
    args = parser.parse_args(argv)

    state_file = Path(args.state_file)
    setup_state = _load_setup_state(state_file) if _setup_state_exists(state_file) else None
    mode = _resolve_mode(args.mode, state_exists=_setup_state_exists(state_file), setup_state=setup_state)
    setup_auto_recover_enabled = False

    if mode == "setup" and isinstance(setup_state, dict) and setup_state.get("force_setup_on_next_boot") is True:
        setup_auto_recover_enabled = True
        setup_state["force_setup_on_next_boot"] = False
        persist_setup_state(state_file, setup_state)

    if mode == "setup":
        return _run_setup_server(
            state_file=state_file,
            host=args.setup_host,
            port=args.setup_port,
            enable_ap_mode=args.enable_ap_mode,
            ap_use_sudo=args.ap_use_sudo,
            ap_start_script=args.ap_start_script,
            ap_stop_script=args.ap_stop_script,
            setup_auto_recover_enabled=setup_auto_recover_enabled,
        )
    return _run_runtime(state_file=state_file)


if __name__ == "__main__":
    raise SystemExit(main())
