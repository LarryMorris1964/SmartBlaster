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
from smartblaster.services.reference_images import ReferenceImageStore
from smartblaster.services.reference_offload import NoopReferenceOffloadTransport, ReferenceOffloadService
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
        reference_offload_service: ReferenceOffloadService | None = None,
        reference_offload_interval_minutes: int = 15,
        camera_health_required: bool = False,
        camera_health_probe_interval_minutes: int = 5,
        reference_image_store: ReferenceImageStore | None = None,
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
        self.reference_offload_service = reference_offload_service
        self.reference_offload_interval_minutes = max(1, int(reference_offload_interval_minutes))
        self.camera_health_required = camera_health_required
        self.camera_health_probe_interval_minutes = max(1, int(camera_health_probe_interval_minutes))
        self.reference_image_store = reference_image_store
        self._camera_alert_active = False
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
        reference_offload_service: ReferenceOffloadService | None = None
        reference_image_store: ReferenceImageStore | None = None
        if cfg.camera_enabled:
            reference_image_store = ReferenceImageStore(Path(cfg.reference_image_dir))
            status_service = ThermostatStatusService(
                camera=camera,
                parser=create_parser_for_model(profile.id),
                history_file=Path(cfg.status_history_file),
                diagnostic_save_images=cfg.status_diagnostic_mode,
                diagnostic_image_dir=Path(cfg.status_image_dir),
                reference_capture_on_parse_failure=cfg.reference_capture_on_parse_failure,
                reference_image_dir=Path(cfg.reference_image_dir),
                reference_image_store=reference_image_store,
                manage_camera_lifecycle=False,
            )
            if cfg.reference_offload_enabled:
                reference_offload_service = ReferenceOffloadService(
                    store=reference_image_store,
                    transport=NoopReferenceOffloadTransport(),
                    batch_size=cfg.reference_offload_batch_size,
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
            reference_offload_service=reference_offload_service,
            reference_offload_interval_minutes=cfg.reference_offload_interval_minutes,
            camera_health_required=cfg.camera_enabled,
            camera_health_probe_interval_minutes=cfg.camera_health_probe_interval_minutes,
            reference_image_store=reference_image_store,
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
        last_offload_monotonic = time.monotonic()
        last_camera_probe_monotonic = time.monotonic()
        self._probe_camera_health()
        try:
            while True:
                scheduled_event = self.event_source.poll()
                if scheduled_event:
                    last_state = self._apply_event(scheduled_event, last_state=last_state)

                external_event = self.ir.listen()
                if external_event:
                    last_state = self._apply_event(external_event, last_state=last_state)

                if self.reference_offload_service is not None:
                    now = time.monotonic()
                    interval_s = self.reference_offload_interval_minutes * 60
                    if (now - last_offload_monotonic) >= interval_s:
                        result = self.reference_offload_service.run_once()
                        if result.scanned > 0:
                            print(
                                "reference_offload "
                                f"scanned={result.scanned} "
                                f"offloaded={result.offloaded} "
                                f"failed={result.failed}"
                            )
                        last_offload_monotonic = now

                if self.camera_health_required:
                    now = time.monotonic()
                    probe_interval_s = self.camera_health_probe_interval_minutes * 60
                    if (now - last_camera_probe_monotonic) >= probe_interval_s:
                        self._probe_camera_health()
                        last_camera_probe_monotonic = now

                time.sleep(self.loop_interval_ms / 1000)
        except KeyboardInterrupt:
            print("Stopping SmartBlaster runtime")
        finally:
            self.camera.stop()

    def _probe_camera_health(self) -> bool:
        if not self.camera_health_required:
            return True

        frame_ok = False
        error_message = "camera did not return a frame"
        try:
            frame = self.camera.capture_frame()
            frame_ok = frame is not None and len(frame) > 0
        except Exception as ex:
            error_message = str(ex)

        if frame_ok:
            if self._camera_alert_active:
                print("camera_health RECOVERED")
            self._camera_alert_active = False
            return True

        if not self._camera_alert_active:
            print(f"ALERT camera_expected_but_unavailable detail={error_message}")
            if self.reference_image_store is not None:
                self.reference_image_store.save_capture(
                    frame=None,
                    profile_id="camera_health",
                    phase="camera_expected_unavailable",
                    label="runtime_probe",
                    metadata={
                        "message": error_message,
                        "camera_health_required": self.camera_health_required,
                        "probe_interval_minutes": self.camera_health_probe_interval_minutes,
                    },
                )
            self._camera_alert_active = True

        return False


def _parse_active_days(active_days_csv: str) -> list[str]:
    days = [item.strip().lower() for item in active_days_csv.split(",") if item.strip()]
    if not days:
        return ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    return days
