"""Tests for the setup validation workflow."""

from __future__ import annotations

from pathlib import Path

from smartblaster.hardware.ir import IrService
from smartblaster.services.setup_validation import (
    SetupValidator,
    _VALIDATION_SEQUENCE,
    ValidationReport,
    ValidationStepOutcome,
)
from smartblaster.services.thermostat_status import (
    StatusAttemptOutcome,
    StatusAttemptResult,
    ThermostatStatusService,
)
from smartblaster.vision.models import (
    DisplayMode,
    FanSpeedLevel,
    ThermostatDisplayState,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeIr:
    """Records IR commands sent during validation."""

    dry_run = True

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send_midea_command(self, command) -> str:
        self.sent.append(command.mode.value)
        return f"req-{len(self.sent)}"


class FakeStatusService:
    """Returns preconfigured AttemptResult for each call."""

    def __init__(self, results: list[StatusAttemptResult]) -> None:
        self._results = list(results)
        self._index = 0

    def attempt_status(self) -> StatusAttemptResult:
        result = self._results[self._index % len(self._results)]
        self._index += 1
        return result


def _display_state(mode: DisplayMode, power_on: bool = True) -> ThermostatDisplayState:
    return ThermostatDisplayState(
        model_id="midea_kjr_12b_dp_t",
        power_on=power_on,
        mode=mode,
        set_temperature=24.0,
        fan_speed=FanSpeedLevel.AUTO,
    )


def _success(mode: DisplayMode, power_on: bool = True) -> StatusAttemptResult:
    return StatusAttemptResult(
        outcome=StatusAttemptOutcome.SUCCESS,
        state=_display_state(mode, power_on=power_on),
    )


_STEP_COUNT = len(_VALIDATION_SEQUENCE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validator(
    ir: FakeIr,
    status_service: FakeStatusService | None,
) -> SetupValidator:
    return SetupValidator(
        ir=ir,  # type: ignore[arg-type]
        status_service=status_service,  # type: ignore[arg-type]
        settle_seconds=0,
        sleep_fn=lambda _s: None,
    )


# ---------------------------------------------------------------------------
# No-camera (skipped) path
# ---------------------------------------------------------------------------


def test_no_camera_returns_skipped_report() -> None:
    ir = FakeIr()
    validator = _make_validator(ir, status_service=None)
    report = validator.run()

    assert report.skipped is True
    assert report.camera_enabled is False
    assert report.overall_pass is True
    assert len(report.steps) == _STEP_COUNT
    assert all(s.outcome == ValidationStepOutcome.SKIP for s in report.steps)


def test_no_camera_sends_no_ir_commands() -> None:
    ir = FakeIr()
    _make_validator(ir, status_service=None).run()
    assert ir.sent == []


def test_no_camera_report_includes_profile_id() -> None:
    ir = FakeIr()
    report = _make_validator(ir, status_service=None).run()
    assert report.profile_id == "midea_kjr_12b_dp_t"


# ---------------------------------------------------------------------------
# All-pass path
# ---------------------------------------------------------------------------


def _all_passing_results() -> list[StatusAttemptResult]:
    results: list[StatusAttemptResult] = []
    for spec in _VALIDATION_SEQUENCE:
        if spec.command.mode == DisplayMode.OFF.value:
            results.append(_success(DisplayMode.OFF, power_on=False))
        else:
            parsed_temp = spec.expected_set_temperature_c
            if parsed_temp is None:
                parsed_temp = spec.command.temperature_c
            state = ThermostatDisplayState(
                model_id="midea_kjr_12b_dp_t",
                power_on=True,
                mode=DisplayMode(spec.command.mode.value),
                set_temperature=parsed_temp,
                fan_speed=FanSpeedLevel.AUTO,
            )
            results.append(StatusAttemptResult(outcome=StatusAttemptOutcome.SUCCESS, state=state))
    return results


def test_all_pass_overall_pass_is_true() -> None:
    ir = FakeIr()
    service = FakeStatusService(_all_passing_results())
    report = _make_validator(ir, service).run()

    assert report.overall_pass is True
    assert report.skipped is False
    assert report.camera_enabled is True
    assert all(s.outcome == ValidationStepOutcome.PASS for s in report.steps)


def test_all_pass_sends_five_commands() -> None:
    ir = FakeIr()
    service = FakeStatusService(_all_passing_results())
    _make_validator(ir, service).run()
    assert len(ir.sent) == _STEP_COUNT
    assert ir.sent[0] == "cool"
    assert ir.sent[-1] == "off"


def test_all_pass_step_command_names() -> None:
    ir = FakeIr()
    service = FakeStatusService(_all_passing_results())
    report = _make_validator(ir, service).run()
    names = [s.command_name for s in report.steps]
    assert names == [spec.command_name for spec in _VALIDATION_SEQUENCE]


def test_all_pass_parsed_mode_recorded() -> None:
    ir = FakeIr()
    service = FakeStatusService(_all_passing_results())
    report = _make_validator(ir, service).run()
    cool_step = report.steps[0]
    assert cool_step.parsed_mode == "cool"
    assert cool_step.parsed_power_on is True
    assert cool_step.parsed_set_temperature_c == 26
    assert cool_step.command_payload["mode"] == "cool"
    assert cool_step.command_payload["temperature_c"] == 26


# ---------------------------------------------------------------------------
# Partial failure paths
# ---------------------------------------------------------------------------


def test_wrong_mode_outcome_is_fail() -> None:
    """Thermostat acks COOL command but reports HEAT mode."""
    ir = FakeIr()
    results = _all_passing_results()
    results[0] = _success(DisplayMode.HEAT)  # cool_26 command -> wrong mode returned
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()

    assert report.overall_pass is False
    assert report.steps[0].outcome == ValidationStepOutcome.FAIL
    assert report.steps[0].error_message is not None
    # Rest should still pass
    assert all(s.outcome == ValidationStepOutcome.PASS for s in report.steps[1:])


def test_optional_heat_failure_does_not_fail_overall() -> None:
    """Optional steps should not fail the overall validation."""
    ir = FakeIr()
    results = _all_passing_results()
    heat_index = next(i for i, spec in enumerate(_VALIDATION_SEQUENCE) if spec.command_name == "heat")
    results[heat_index] = _success(DisplayMode.COOL)
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()

    heat_step = report.steps[heat_index]
    assert heat_step.command_name == "heat"
    assert heat_step.required_for_pass is False
    assert heat_step.outcome == ValidationStepOutcome.FAIL
    assert report.optional_step_failures == 1
    assert report.required_step_failures == 0
    assert report.overall_pass is True


def test_parse_failed_outcome_is_fail() -> None:
    ir = FakeIr()
    results = _all_passing_results()
    results[0] = StatusAttemptResult(outcome=StatusAttemptOutcome.PARSE_FAILED, error_message="no parse")
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()

    assert report.overall_pass is False
    assert report.steps[0].outcome == ValidationStepOutcome.FAIL
    assert "no parse" in (report.steps[0].error_message or "")


def test_camera_unavailable_outcome_is_camera_error() -> None:
    ir = FakeIr()
    results = _all_passing_results()
    results[0] = StatusAttemptResult(
        outcome=StatusAttemptOutcome.CAMERA_UNAVAILABLE,
        error_message="camera did not return a frame",
    )
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()

    assert report.overall_pass is False
    assert report.steps[0].outcome == ValidationStepOutcome.CAMERA_ERROR


def test_required_failure_counts_mark_overall_fail() -> None:
    ir = FakeIr()
    results = _all_passing_results()
    cool_index = next(i for i, spec in enumerate(_VALIDATION_SEQUENCE) if spec.command_name == "cool_26")
    results[cool_index] = _success(DisplayMode.HEAT)
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()

    assert report.required_step_failures == 1
    assert report.overall_pass is False


# ---------------------------------------------------------------------------
# OFF command special logic
# ---------------------------------------------------------------------------


def test_off_passes_when_power_on_is_false() -> None:
    ir = FakeIr()
    results = _all_passing_results()
    off_index = next(i for i, spec in enumerate(_VALIDATION_SEQUENCE) if spec.command_name == "off")
    results[off_index] = _success(DisplayMode.UNKNOWN, power_on=False)
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()
    off_step = report.steps[off_index]
    assert off_step.outcome == ValidationStepOutcome.PASS


def test_off_passes_when_mode_is_off_regardless_of_power_on() -> None:
    ir = FakeIr()
    results = _all_passing_results()
    off_index = next(i for i, spec in enumerate(_VALIDATION_SEQUENCE) if spec.command_name == "off")
    results[off_index] = _success(DisplayMode.OFF, power_on=True)
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()
    off_step = report.steps[off_index]
    assert off_step.outcome == ValidationStepOutcome.PASS


def test_off_fails_when_power_on_true_and_mode_not_off() -> None:
    ir = FakeIr()
    results = _all_passing_results()
    off_index = next(i for i, spec in enumerate(_VALIDATION_SEQUENCE) if spec.command_name == "off")
    results[off_index] = _success(DisplayMode.COOL, power_on=True)
    service = FakeStatusService(results)
    report = _make_validator(ir, service).run()
    off_step = report.steps[off_index]
    assert off_step.outcome == ValidationStepOutcome.FAIL


# ---------------------------------------------------------------------------
# Report serialisation
# ---------------------------------------------------------------------------


def test_report_to_dict_is_json_compatible() -> None:
    import json

    ir = FakeIr()
    service = FakeStatusService(_all_passing_results())
    report = _make_validator(ir, service).run()
    d = report.to_dict()
    # Should round-trip through JSON without error
    json.dumps(d)
    assert d["overall_pass"] is True
    assert len(d["steps"]) == _STEP_COUNT


# ---------------------------------------------------------------------------
# sleep_fn injection
# ---------------------------------------------------------------------------


def test_sleep_fn_called_once_per_step() -> None:
    sleep_calls: list[float] = []
    ir = FakeIr()
    service = FakeStatusService(_all_passing_results())
    validator = SetupValidator(
        ir=ir,  # type: ignore[arg-type]
        status_service=service,  # type: ignore[arg-type]
        settle_seconds=7.5,
        sleep_fn=sleep_calls.append,
    )
    validator.run()
    assert len(sleep_calls) == _STEP_COUNT
    assert all(s == 7.5 for s in sleep_calls)


def test_sequence_exercises_extended_ir_variants() -> None:
    names = {spec.command_name for spec in _VALIDATION_SEQUENCE}
    assert "cool_26" in names
    assert "cool_24" in names
    assert "auto" in names
    assert "fan_turbo" in names
    assert "swing_both" in names
    assert "preset_sleep" in names
    assert "follow_me" in names
    assert "beeper" in names


def test_required_temperature_mismatch_fails_overall() -> None:
    results = _all_passing_results()
    cool24_index = next(i for i, spec in enumerate(_VALIDATION_SEQUENCE) if spec.command_name == "cool_24")
    bad_state = ThermostatDisplayState(
        model_id="midea_kjr_12b_dp_t",
        power_on=True,
        mode=DisplayMode.COOL,
        set_temperature=26.0,
        fan_speed=FanSpeedLevel.AUTO,
    )
    results[cool24_index] = StatusAttemptResult(outcome=StatusAttemptOutcome.SUCCESS, state=bad_state)

    report = _make_validator(FakeIr(), FakeStatusService(results)).run()
    assert report.overall_pass is False
    assert report.steps[cool24_index].outcome == ValidationStepOutcome.FAIL
