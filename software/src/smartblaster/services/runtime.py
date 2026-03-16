"""Runtime composition and main loop."""

from __future__ import annotations

import time
from pathlib import Path

from smartblaster.config import from_env
from smartblaster.control.state_machine import HvacStateMachine
from smartblaster.events.sources import CompositeEventSource, DailyTimeEventSource, EventSource
from smartblaster.hardware.camera import CameraService, NoCameraService
from smartblaster.hardware.ir import IrService
from smartblaster.ir.command import MideaFan, MideaPreset, MideaSwing
from smartblaster.services.thermostat_status import ThermostatStatusService
from smartblaster.temperature import quantize_program_setpoint_for_thermostat, thermostat_to_program_celsius
from smartblaster.thermostats.library import get_profile
from smartblaster.vision.models import ThermostatDisplayState
from smartblaster.vision.registry import create_parser_for_model


class SmartBlasterRuntime:
    def __init__(
        self,
        *,
        loop_interval_ms: int,
        target_temperature_c: float,
        ir: IrService,
        camera: CameraService,
        event_source: EventSource,
        status_service: ThermostatStatusService | None = None,
        fan_mode: MideaFan = MideaFan.AUTO,
        swing_mode: MideaSwing = MideaSwing.OFF,
        preset_mode: MideaPreset = MideaPreset.NONE,
        thermostat_temperature_unit: str = "C",
    ) -> None:
        self.loop_interval_ms = loop_interval_ms
        self.target_temperature_c = target_temperature_c
        self.fan_mode = fan_mode
        self.swing_mode = swing_mode
        self.preset_mode = preset_mode
        self.thermostat_temperature_unit = thermostat_temperature_unit
        self.ir = ir
        self.camera = camera
        self.event_source = event_source
        self.status_service = status_service
        self.state_machine = HvacStateMachine()

    @classmethod
    def from_env(cls) -> "SmartBlasterRuntime":
        cfg = from_env()
        profile = get_profile(cfg.thermostat_profile_id)
        if profile.ir_protocol != "midea":
            raise ValueError(
                f"thermostat profile {profile.id} uses unsupported IR protocol {profile.ir_protocol}"
            )

        ir = IrService(tx_gpio=cfg.ir_tx_gpio, rx_gpio=cfg.ir_rx_gpio, dry_run=cfg.dry_run)
        camera: CameraService = CameraService() if cfg.camera_enabled else NoCameraService()

        if cfg.camera_enabled and not profile.camera_supported:
            raise ValueError(
                f"camera routines are not yet available for thermostat profile {profile.id}"
            )

        event_source = CompositeEventSource(
            sources=[
                DailyTimeEventSource(
                    on_time=cfg.daily_on_time,
                    off_time=cfg.daily_off_time,
                    active_days=tuple(_parse_active_days(cfg.active_days_csv)),
                    timezone=cfg.timezone,
                ),
            ]
        )

        status_service: ThermostatStatusService | None = None
        if cfg.camera_enabled:
            status_service = ThermostatStatusService(
                camera=camera,
                parser=create_parser_for_model(profile.id),
                history_file=Path(cfg.status_history_file),
                diagnostic_save_images=cfg.status_diagnostic_mode,
                diagnostic_image_dir=Path(cfg.status_image_dir),
                reference_capture_on_parse_failure=cfg.reference_capture_on_parse_failure,
                reference_image_dir=Path(cfg.reference_image_dir),
                manage_camera_lifecycle=False,
            )

        return cls(
            loop_interval_ms=cfg.loop_interval_ms,
            target_temperature_c=cfg.target_temperature_c,
            fan_mode=MideaFan(cfg.fan_mode),
            swing_mode=MideaSwing(cfg.swing_mode),
            preset_mode=MideaPreset(cfg.preset_mode),
            thermostat_temperature_unit=cfg.thermostat_temperature_unit,
            ir=ir,
            camera=camera,
            event_source=event_source,
            status_service=status_service,
        )

    def _target_setpoint_c_for_thermostat(self) -> float:
        return quantize_program_setpoint_for_thermostat(
            self.target_temperature_c,
            self.thermostat_temperature_unit,
        )

    def normalize_thermostat_temperature_to_program_c(self, reading: float) -> float:
        return thermostat_to_program_celsius(reading, self.thermostat_temperature_unit)

    def request_thermostat_status(self) -> ThermostatDisplayState:
        if self.status_service is None:
            raise RuntimeError("camera status request unavailable: camera is disabled")
        return self.status_service.request_status()

    def _apply_event(self, event: str, *, last_state: str) -> str:
        new_state = self.state_machine.handle_event(event)
        print(f"state={new_state}")

        if new_state != last_state:
            command = self.state_machine.build_command(
                target_temperature_c=self._target_setpoint_c_for_thermostat(),
                fan=self.fan_mode,
                swing=self.swing_mode,
                preset=self.preset_mode,
            )
            request_id = self.ir.send_midea_command(command)
            print(f"sent midea command request_id={request_id}")

        return new_state

    def run_forever(self) -> None:
        self.camera.start()
        last_state = self.state_machine.state
        try:
            while True:
                scheduled_event = self.event_source.poll()
                if scheduled_event:
                    last_state = self._apply_event(scheduled_event, last_state=last_state)

                external_event = self.ir.listen()
                if external_event:
                    last_state = self._apply_event(external_event, last_state=last_state)

                time.sleep(self.loop_interval_ms / 1000)
        except KeyboardInterrupt:
            print("Stopping SmartBlaster runtime")
        finally:
            self.camera.stop()


def _parse_active_days(active_days_csv: str) -> list[str]:
    days = [item.strip().lower() for item in active_days_csv.split(",") if item.strip()]
    if not days:
        return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return days
