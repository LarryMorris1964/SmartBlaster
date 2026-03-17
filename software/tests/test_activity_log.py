"""Tests for the structured activity logging module."""

from __future__ import annotations

from pathlib import Path

import pytest
import structlog
import structlog.testing

from smartblaster.services.activity_log import ActivityLogger, configure_logging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _logger(name: str = "Test Device") -> ActivityLogger:
    return ActivityLogger(device_name=name)


# ---------------------------------------------------------------------------
# ActivityLogger event shape tests (using capture_logs)
# ---------------------------------------------------------------------------

def test_runtime_started_event() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().runtime_started(profile_id="midea_kjr_12b_dp_t", camera_enabled=True, dry_run=False)

    assert len(logs) == 1
    ev = logs[0]
    assert ev["event"] == "runtime_started"
    assert ev["profile_id"] == "midea_kjr_12b_dp_t"
    assert ev["camera_enabled"] is True
    assert ev["dry_run"] is False
    assert ev["device"] == "Test Device"


def test_runtime_stopped_default_reason() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().runtime_stopped()

    assert logs[0]["event"] == "runtime_stopped"
    assert logs[0]["reason"] == "shutdown"


def test_runtime_stopped_custom_reason() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().runtime_stopped(reason="keyboard_interrupt")

    assert logs[0]["reason"] == "keyboard_interrupt"


def test_state_changed_event() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().state_changed(from_state="idle", to_state="cooling", trigger="cool_requested")

    ev = logs[0]
    assert ev["event"] == "state_changed"
    assert ev["from_state"] == "idle"
    assert ev["to_state"] == "cooling"
    assert ev["trigger"] == "cool_requested"


def test_schedule_event_default_source() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().schedule_event(trigger="cool_requested")

    ev = logs[0]
    assert ev["event"] == "schedule_event"
    assert ev["trigger"] == "cool_requested"
    assert ev["source"] == "weekly_schedule"


def test_schedule_event_custom_source() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().schedule_event(trigger="cool_requested", source="ir_receive")

    assert logs[0]["source"] == "ir_receive"


def test_async_event_with_extra_fields() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().async_event(trigger="solar_surplus_started", source="inverter", surplus_w=2400)

    ev = logs[0]
    assert ev["event"] == "async_event"
    assert ev["trigger"] == "solar_surplus_started"
    assert ev["source"] == "inverter"
    assert ev["surplus_w"] == 2400


def test_ir_command_sent_event() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().ir_command_sent(
            request_id="req-001",
            command_name="set_mode",
            criticality="high",
            max_attempts=3,
            dry_run=True,
        )

    ev = logs[0]
    assert ev["event"] == "ir_command_sent"
    assert ev["request_id"] == "req-001"
    assert ev["command_name"] == "set_mode"
    assert ev["criticality"] == "high"
    assert ev["max_attempts"] == 3
    assert ev["dry_run"] is True


def test_ir_command_verified_event() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().ir_command_verified(
            request_id="req-002",
            confidence=0.93,
            parsed_mode="cool",
            parsed_temperature=24.0,
        )

    ev = logs[0]
    assert ev["event"] == "ir_command_verified"
    assert ev["confidence"] == pytest.approx(0.93)
    assert ev["parsed_mode"] == "cool"
    assert ev["parsed_temperature"] == pytest.approx(24.0)


def test_ir_command_verified_optional_fields_absent() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().ir_command_verified(request_id="req-003", confidence=0.5)

    ev = logs[0]
    assert ev["parsed_mode"] is None
    assert ev["parsed_temperature"] is None


def test_ir_command_verification_failed_is_warning() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().ir_command_verification_failed(request_id="req-004", reason="parse_error")

    ev = logs[0]
    assert ev["event"] == "ir_command_verification_failed"
    assert ev["log_level"] == "warning"
    assert ev["reason"] == "parse_error"


def test_home_automation_command_ifttt() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().home_automation_command(integration="ifttt", command="cool_on")

    ev = logs[0]
    assert ev["event"] == "home_automation_command"
    assert ev["integration"] == "ifttt"
    assert ev["command"] == "cool_on"


def test_home_automation_command_with_payload() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().home_automation_command(
            integration="alexa", command="set_temperature", value=22
        )

    ev = logs[0]
    assert ev["integration"] == "alexa"
    assert ev["value"] == 22


def test_reference_offload_run_event() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().reference_offload_run(scanned=10, offloaded=8, failed=2)

    ev = logs[0]
    assert ev["event"] == "reference_offload_run"
    assert ev["scanned"] == 10
    assert ev["offloaded"] == 8
    assert ev["failed"] == 2


def test_setup_saved_event() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().setup_saved(device_name="Bedroom", profile_id="midea_kjr_12b_dp_t")

    ev = logs[0]
    assert ev["event"] == "setup_saved"
    assert ev["device_name"] == "Bedroom"


def test_network_failover_is_warning() -> None:
    with structlog.testing.capture_logs() as logs:
        _logger().network_failover(reason="nmcli_disconnected")

    ev = logs[0]
    assert ev["event"] == "network_failover"
    assert ev["log_level"] == "warning"


def test_device_name_bound_to_all_events() -> None:
    log = ActivityLogger(device_name="Kitchen Unit")
    with structlog.testing.capture_logs() as logs:
        log.runtime_stopped()
        log.schedule_event(trigger="stop_requested")

    for ev in logs:
        assert ev["device"] == "Kitchen Unit"


# ---------------------------------------------------------------------------
# configure_logging smoke test
# ---------------------------------------------------------------------------

def test_configure_logging_creates_file(tmp_path: Path) -> None:
    log_file = tmp_path / "activity_log.jsonl"
    configure_logging(log_level="DEBUG", activity_log_file=log_file)
    assert log_file.parent.exists()


def test_configure_logging_no_file_does_not_raise() -> None:
    configure_logging(log_level="WARNING", activity_log_file=None)
