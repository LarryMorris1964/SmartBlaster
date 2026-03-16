from pathlib import Path

from smartblaster.hardware.camera import CameraService
from smartblaster.ir.command import MideaMode
from smartblaster.events.sources import QueueEventSource
from smartblaster.services.reference_images import ReferenceImageStore
from smartblaster.services.runtime import SmartBlasterRuntime
from smartblaster.vision.models import DisplayMode, ThermostatDisplayState


class FakeIrService:
    def __init__(self, events: list[str]) -> None:
        self._events = events
        self.sent_modes: list[MideaMode] = []
        self.sent_temps_c: list[float | None] = []

    def listen(self) -> str | None:
        if not self._events:
            raise KeyboardInterrupt()
        return self._events.pop(0)

    def send_midea_command(self, command):
        self.sent_modes.append(command.mode)
        self.sent_temps_c.append(command.temperature_c)
        return "req-test"


class FakeCamera(CameraService):
    def start(self) -> None:
        return

    def stop(self) -> None:
        return


class SequenceCamera(CameraService):
    def __init__(self, frames: list[bytes | None]) -> None:
        super().__init__()
        self._frames = frames

    def start(self) -> None:
        return

    def stop(self) -> None:
        return

    def capture_frame(self) -> bytes | None:
        if not self._frames:
            return None
        return self._frames.pop(0)


def test_runtime_dispatches_command_on_state_change() -> None:
    ir = FakeIrService(events=["cool_requested", "stop_requested"])
    runtime = SmartBlasterRuntime(
        loop_interval_ms=0,
        target_temperature_c=24,
        ir=ir,
        camera=FakeCamera(),
        event_source=QueueEventSource(),
    )

    runtime.run_forever()

    assert ir.sent_modes == [MideaMode.COOL, MideaMode.OFF]


def test_runtime_quantizes_target_for_fahrenheit_thermostat() -> None:
    ir = FakeIrService(events=["cool_requested"])
    runtime = SmartBlasterRuntime(
        loop_interval_ms=0,
        target_temperature_c=24.2,
        ir=ir,
        camera=FakeCamera(),
        event_source=QueueEventSource(),
        thermostat_temperature_unit="F",
    )

    runtime.run_forever()

    assert ir.sent_modes == [MideaMode.COOL]
    assert round(ir.sent_temps_c[0], 2) == 24.44


def test_runtime_status_request_uses_status_service() -> None:
    class FakeStatusService:
        def request_status(self) -> ThermostatDisplayState:
            return ThermostatDisplayState(
                model_id="midea_kjr_12b_dp_t",
                mode=DisplayMode.COOL,
                power_on=True,
            )

    runtime = SmartBlasterRuntime(
        loop_interval_ms=0,
        target_temperature_c=24,
        ir=FakeIrService(events=[]),
        camera=FakeCamera(),
        event_source=QueueEventSource(),
        status_service=FakeStatusService(),
    )

    status = runtime.request_thermostat_status()
    assert status.power_on is True
    assert status.mode == DisplayMode.COOL


def test_runtime_camera_health_probe_records_alert_when_expected_missing(tmp_path: Path) -> None:
    store = ReferenceImageStore(tmp_path / "refs")
    runtime = SmartBlasterRuntime(
        loop_interval_ms=0,
        target_temperature_c=24,
        ir=FakeIrService(events=[]),
        camera=SequenceCamera(frames=[None]),
        event_source=QueueEventSource(),
        camera_health_required=True,
        reference_image_store=store,
    )

    ok = runtime._probe_camera_health()

    assert ok is False
    alert_dir = tmp_path / "refs" / "camera_expected_unavailable"
    metadata_files = list(alert_dir.glob("*.json"))
    assert len(metadata_files) == 1


def test_runtime_camera_health_probe_clears_alert_after_recovery(tmp_path: Path) -> None:
    store = ReferenceImageStore(tmp_path / "refs")
    runtime = SmartBlasterRuntime(
        loop_interval_ms=0,
        target_temperature_c=24,
        ir=FakeIrService(events=[]),
        camera=SequenceCamera(frames=[None, b"ok"]),
        event_source=QueueEventSource(),
        camera_health_required=True,
        reference_image_store=store,
    )

    first = runtime._probe_camera_health()
    second = runtime._probe_camera_health()

    assert first is False
    assert second is True
    assert runtime._camera_alert_active is False
