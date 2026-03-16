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
from smartblaster.ir.command import MideaIrCommand, MideaMode
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

# Exercise each non-OFF mode then finish with OFF so the unit is left powered down
_VALIDATION_SEQUENCE: list[tuple[str, MideaIrCommand]] = [
    ("cool", MideaIrCommand(mode=MideaMode.COOL, temperature_c=24)),
    ("heat", MideaIrCommand(mode=MideaMode.HEAT, temperature_c=24)),
    ("dry", MideaIrCommand(mode=MideaMode.DRY, temperature_c=24)),
    ("fan_only", MideaIrCommand(mode=MideaMode.FAN_ONLY, temperature_c=24)),
    ("off", MideaIrCommand(mode=MideaMode.OFF)),
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
    outcome: ValidationStepOutcome
    confidence: float | None = None
    parsed_power_on: bool | None = None
    parsed_mode: str | None = None
    error_message: str | None = None


@dataclass
class ValidationReport:
    profile_id: str
    ran_at_utc: str
    camera_enabled: bool
    skipped: bool
    overall_pass: bool
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
                        command_name=name,
                        mode=cmd.mode.value,
                        outcome=ValidationStepOutcome.SKIP,
                    )
                    for name, cmd in _VALIDATION_SEQUENCE
                ],
            )

        steps: list[ValidationStepResult] = []
        for command_name, command in _VALIDATION_SEQUENCE:
            step = self._run_step(command_name, command)
            steps.append(step)

        any_failures = any(
            s.outcome in (ValidationStepOutcome.FAIL, ValidationStepOutcome.CAMERA_ERROR)
            for s in steps
        )
        return ValidationReport(
            profile_id=self.profile_id,
            ran_at_utc=ran_at,
            camera_enabled=True,
            skipped=False,
            overall_pass=not any_failures,
            steps=steps,
        )

    def _run_step(self, command_name: str, command: MideaIrCommand) -> ValidationStepResult:
        assert self.status_service is not None

        self.ir.send_midea_command(command)
        self._sleep(self.settle_seconds)
        result = self.status_service.attempt_status()

        expected_power_on, expected_display_mode = _EXPECTED[command.mode]

        if result.outcome == StatusAttemptOutcome.CAMERA_UNAVAILABLE:
            return ValidationStepResult(
                command_name=command_name,
                mode=command.mode.value,
                outcome=ValidationStepOutcome.CAMERA_ERROR,
                error_message=result.error_message,
            )

        if result.outcome == StatusAttemptOutcome.PARSE_FAILED or result.state is None:
            return ValidationStepResult(
                command_name=command_name,
                mode=command.mode.value,
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

        error_msg: str | None = None
        if not passed:
            error_msg = (
                f"expected power_on={expected_power_on} mode={expected_display_mode.value}, "
                f"got power_on={state.power_on} mode={state.mode.value}"
            )

        return ValidationStepResult(
            command_name=command_name,
            mode=command.mode.value,
            outcome=ValidationStepOutcome.PASS if passed else ValidationStepOutcome.FAIL,
            confidence=confidence,
            parsed_power_on=state.power_on,
            parsed_mode=state.mode.value,
            error_message=error_msg,
        )


def _overall_confidence(state: ThermostatDisplayState) -> float | None:
    if not state.confidence_by_field:
        return None
    return round(sum(state.confidence_by_field.values()) / len(state.confidence_by_field), 3)
