from smartblaster.ir.command import (
    MideaFan,
    MideaIrCommand,
    MideaMode,
    MideaPreset,
    MideaSwing,
)


def test_off_command_allows_no_temperature() -> None:
    cmd = MideaIrCommand(mode=MideaMode.OFF)
    payload = cmd.to_payload()
    assert payload["mode"] == "off"


def test_non_off_requires_temperature() -> None:
    cmd = MideaIrCommand(mode=MideaMode.COOL)
    try:
        cmd.validate()
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "temperature_c is required" in str(ex)


def test_payload_includes_all_fields() -> None:
    cmd = MideaIrCommand(
        mode=MideaMode.COOL,
        temperature_c=24,
        fan=MideaFan.MEDIUM,
        swing=MideaSwing.VERTICAL,
        preset=MideaPreset.BOOST,
        follow_me_c=23,
        beeper=True,
    )
    payload = cmd.to_payload()
    assert payload == {
        "mode": "cool",
        "temperature_c": 24,
        "fan": "medium",
        "swing": "vertical",
        "preset": "boost",
        "follow_me_c": 23,
        "beeper": True,
    }
