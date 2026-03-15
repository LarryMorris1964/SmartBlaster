from smartblaster.hardware.camera import CameraService
from smartblaster.ir.command import MideaMode
from smartblaster.events.sources import QueueEventSource
from smartblaster.services.runtime import SmartBlasterRuntime


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
