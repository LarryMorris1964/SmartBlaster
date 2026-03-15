from smartblaster.control.state_machine import HvacStateMachine
from smartblaster.ir.command import MideaFan, MideaMode, MideaPreset, MideaSwing


def test_state_transitions_idle_to_cooling() -> None:
    sm = HvacStateMachine()
    assert sm.handle_event("cool_requested") == "cooling"


def test_state_transitions_cooling_to_idle() -> None:
    sm = HvacStateMachine(state="cooling")
    assert sm.handle_event("stop_requested") == "idle"


def test_state_transitions_to_heating() -> None:
    sm = HvacStateMachine()
    assert sm.handle_event("heat_requested") == "heating"


def test_build_command_cooling() -> None:
    sm = HvacStateMachine(state="cooling")
    command = sm.build_command(target_temperature_c=23)
    assert command.mode == MideaMode.COOL
    assert command.temperature_c == 23


def test_build_command_idle_is_off() -> None:
    sm = HvacStateMachine(state="idle")
    command = sm.build_command()
    assert command.mode == MideaMode.OFF


def test_build_command_includes_hvac_options() -> None:
    sm = HvacStateMachine(state="cooling")
    command = sm.build_command(
        target_temperature_c=22,
        fan=MideaFan.HIGH,
        swing=MideaSwing.VERTICAL,
        preset=MideaPreset.ECO,
    )
    assert command.fan == MideaFan.HIGH
    assert command.swing == MideaSwing.VERTICAL
    assert command.preset == MideaPreset.ECO
