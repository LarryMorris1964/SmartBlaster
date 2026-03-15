from smartblaster.cli import build_command_from_args, create_parser
from smartblaster.ir.command import MideaMode


def test_cli_off_command_builds_off_mode() -> None:
    parser = create_parser()
    args = parser.parse_args(["off"])
    cmd = build_command_from_args(args)
    assert cmd.mode == MideaMode.OFF


def test_cli_set_command_builds_payload_fields() -> None:
    parser = create_parser()
    args = parser.parse_args([
        "set",
        "--mode",
        "cool",
        "--temp",
        "24",
        "--fan",
        "medium",
        "--swing",
        "vertical",
        "--preset",
        "boost",
        "--follow-me",
        "23",
        "--beeper",
    ])
    cmd = build_command_from_args(args)
    payload = cmd.to_payload()

    assert payload["mode"] == "cool"
    assert payload["temperature_c"] == 24
    assert payload["fan"] == "medium"
    assert payload["swing"] == "vertical"
    assert payload["preset"] == "boost"
    assert payload["follow_me_c"] == 23
    assert payload["beeper"] is True
