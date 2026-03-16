"""Setup validation workflow: exercise each IR mode and verify camera-parsed state.

Initiated from the captive portal after camera placement is complete.
When no status_service is provided (camera disabled), returns a fully-skipped report.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from smartblaster.hardware.ir import IrService
from smartblaster.ir.command import MideaFan, MideaIrCommand, MideaMode, MideaPreset, MideaSwing
from smartblaster.services.thermostat_status import StatusAttemptOutcome, ThermostatStatusService
from smartblaster.vision.models import DisplayMode, ThermostatDisplayState

# Map each Midea mode to expected (power_on, DisplayMode) after command is sent
_EXPECTED: dict[MideaMode, tuple[bool, DisplayMode]] = {
    MideaMode.COOL: (True, DisplayMode.COOL),
    MideaMode.HEAT: (True, DisplayMode.HEAT),
    MideaMode.DRY: (True, DisplayMode.DRY),
    MideaMode.FAN_ONLY: (True, DisplayMode.FAN_ONLY),
    MideaMode.AUTO: (True, DisplayMode.AUTO),
    MideaMode.OFF: (False, DisplayMode.OFF),
}

@dataclass(frozen=True)
class ValidationCommandSpec:
    command_name: str
    command: MideaIrCommand
    required_for_pass: bool
    expected_set_temperature_c: float | None = None


# Exercise each non-OFF mode then finish with OFF so the unit is left powered down.
#
# Required-for-pass steps are safety/core-control checks.
# Optional steps are informative and should not fail setup if unsupported.
_VALIDATION_SEQUENCE: list[ValidationCommandSpec] = [
    ValidationCommandSpec(
        command_name="cool_26",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=26),
        required_for_pass=True,
        expected_set_temperature_c=26.0,
    ),
    ValidationCommandSpec(
        command_name="cool_24",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24),
        required_for_pass=True,
        expected_set_temperature_c=24.0,
    ),
    ValidationCommandSpec(
        command_name="auto",
        command=MideaIrCommand(mode=MideaMode.AUTO, temperature_c=24),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="heat",
        command=MideaIrCommand(mode=MideaMode.HEAT, temperature_c=24),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="dry",
        command=MideaIrCommand(mode=MideaMode.DRY, temperature_c=24),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="fan_only",
        command=MideaIrCommand(mode=MideaMode.FAN_ONLY, temperature_c=24),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="fan_low",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, fan=MideaFan.LOW),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="fan_medium",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, fan=MideaFan.MEDIUM),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="fan_high",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, fan=MideaFan.HIGH),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="fan_silent",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, fan=MideaFan.SILENT),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="fan_turbo",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, fan=MideaFan.TURBO),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="swing_vertical",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, swing=MideaSwing.VERTICAL),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="swing_both",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, swing=MideaSwing.BOTH),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="preset_sleep",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, preset=MideaPreset.SLEEP),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="preset_eco",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, preset=MideaPreset.ECO),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="preset_boost",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, preset=MideaPreset.BOOST),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="follow_me",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, follow_me_c=22),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="beeper",
        command=MideaIrCommand(mode=MideaMode.COOL, temperature_c=24, beeper=True),
        required_for_pass=False,
    ),
    ValidationCommandSpec(
        command_name="off",
        command=MideaIrCommand(mode=MideaMode.OFF),
        required_for_pass=True,
    ),
]


class ValidationStepOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    CAMERA_ERROR = "camera_error"


@dataclass
class ValidationStepResult:
    command_name: str
    mode: str
    command_payload: dict[str, object]
    required_for_pass: bool
    outcome: ValidationStepOutcome
    confidence: float | None = None
    parsed_power_on: bool | None = None
    parsed_mode: str | None = None
    parsed_set_temperature_c: float | None = None
    error_message: str | None = None


@dataclass
class ValidationReport:
    profile_id: str
    ran_at_utc: str
    camera_enabled: bool
    skipped: bool
    overall_pass: bool
    required_step_failures: int
    optional_step_failures: int
    steps: list[ValidationStepResult]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SetupValidator:
    """Runs a sequence of IR commands and checks the display state for each.

    Args:
        ir: Hardware IR service used to transmit commands.
        status_service: Camera-backed status reader. Pass ``None`` when the camera
            is disabled; ``run()`` will return a skipped report in that case.
        profile_id: Thermostat profile identifier included in the report.
        settle_seconds: How long to wait after sending each IR command before
            reading the display (allows the thermostat LCD to update).
        sleep_fn: Injected sleep callable; override in tests to avoid real delays.
    """

    def __init__(
        self,
        *,
        ir: IrService,
        status_service: ThermostatStatusService | None,
        profile_id: str = "midea_kjr_12b_dp_t",
        settle_seconds: float = 3.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.ir = ir
        self.status_service = status_service
        self.profile_id = profile_id
        self.settle_seconds = settle_seconds
        self._sleep = sleep_fn

    def run(self) -> ValidationReport:
        """Execute the full validation sequence and return a report."""
        ran_at = datetime.now(timezone.utc).isoformat()
        camera_enabled = self.status_service is not None

        if not camera_enabled:
            return ValidationReport(
                profile_id=self.profile_id,
                ran_at_utc=ran_at,
                camera_enabled=False,
                skipped=True,
                overall_pass=True,
                steps=[
                    ValidationStepResult(
                        command_name=spec.command_name,
                        mode=spec.command.mode.value,
                        command_payload=spec.command.to_payload(),
                        required_for_pass=spec.required_for_pass,
                        outcome=ValidationStepOutcome.SKIP,
                    )
                    for spec in _VALIDATION_SEQUENCE
                ],
                required_step_failures=0,
                optional_step_failures=0,
            )

        steps: list[ValidationStepResult] = []
        for spec in _VALIDATION_SEQUENCE:
            step = self._run_step(spec)
            steps.append(step)

        required_failures = sum(
            1
            for s in steps
            if s.required_for_pass and s.outcome in (ValidationStepOutcome.FAIL, ValidationStepOutcome.CAMERA_ERROR)
        )
        optional_failures = sum(
            1
            for s in steps
            if (not s.required_for_pass) and s.outcome in (ValidationStepOutcome.FAIL, ValidationStepOutcome.CAMERA_ERROR)
        )
        return ValidationReport(
            profile_id=self.profile_id,
            ran_at_utc=ran_at,
            camera_enabled=True,
            skipped=False,
            overall_pass=(required_failures == 0),
            required_step_failures=required_failures,
            optional_step_failures=optional_failures,
            steps=steps,
        )

    def _run_step(self, spec: ValidationCommandSpec) -> ValidationStepResult:
        assert self.status_service is not None

        command_name = spec.command_name
        command = spec.command

        self.ir.send_midea_command(command)
        self._sleep(self.settle_seconds)
        result = self.status_service.attempt_status()

        expected_power_on, expected_display_mode = _EXPECTED[command.mode]

        if result.outcome == StatusAttemptOutcome.CAMERA_UNAVAILABLE:
            return ValidationStepResult(
                command_name=command_name,
                mode=command.mode.value,
                command_payload=command.to_payload(),
                required_for_pass=spec.required_for_pass,
                outcome=ValidationStepOutcome.CAMERA_ERROR,
                error_message=result.error_message,
            )

        if result.outcome == StatusAttemptOutcome.PARSE_FAILED or result.state is None:
            return ValidationStepResult(
                command_name=command_name,
                mode=command.mode.value,
                command_payload=command.to_payload(),
                required_for_pass=spec.required_for_pass,
                outcome=ValidationStepOutcome.FAIL,
                error_message=result.error_message or "parse failed",
            )

        state = result.state
        confidence = _overall_confidence(state)

        # OFF: accept power_on=False or mode=OFF (thermostats vary)
        if command.mode == MideaMode.OFF:
            passed = state.power_on is False or state.mode == DisplayMode.OFF
        else:
            passed = state.power_on is True and state.mode == expected_display_mode

        if passed and spec.expected_set_temperature_c is not None:
            parsed = state.set_temperature
            passed = parsed is not None and abs(parsed - spec.expected_set_temperature_c) <= 0.6

        error_msg: str | None = None
        if not passed:
            temp_expectation = ""
            if spec.expected_set_temperature_c is not None:
                temp_expectation = f" set_temperature_c={spec.expected_set_temperature_c}"
            error_msg = (
                f"expected power_on={expected_power_on} mode={expected_display_mode.value}{temp_expectation}, "
                f"got power_on={state.power_on} mode={state.mode.value} set_temperature_c={state.set_temperature}"
            )

        return ValidationStepResult(
            command_name=command_name,
            mode=command.mode.value,
            command_payload=command.to_payload(),
            required_for_pass=spec.required_for_pass,
            outcome=ValidationStepOutcome.PASS if passed else ValidationStepOutcome.FAIL,
            confidence=confidence,
            parsed_power_on=state.power_on,
            parsed_mode=state.mode.value,
            parsed_set_temperature_c=state.set_temperature,
            error_message=error_msg,
        )


def _overall_confidence(state: ThermostatDisplayState) -> float | None:
    if not state.confidence_by_field:
        return None
    return round(sum(state.confidence_by_field.values()) / len(state.confidence_by_field), 3)
