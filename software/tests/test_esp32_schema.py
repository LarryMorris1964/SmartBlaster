from smartblaster.ir.command import MideaIrCommand, MideaMode
from smartblaster.ir.esp32_schema import (
    decode_ack_message,
    encode_ack_message,
    encode_command_message,
    parse_command_message,
)


def test_encode_command_message() -> None:
    cmd = MideaIrCommand(mode=MideaMode.COOL, temperature_c=25)
    raw = encode_command_message(cmd, request_id="req-1")

    assert raw.endswith("\n")
    assert '"topic":"midea_ir.command"' in raw
    assert '"request_id":"req-1"' in raw
    assert '"mode":"cool"' in raw


def test_decode_ack_message() -> None:
    ack = decode_ack_message('{"request_id":"req-1","ok":true}')
    assert ack["request_id"] == "req-1"
    assert ack["ok"] is True


def test_parse_command_message() -> None:
    raw = (
        '{"v":1,"topic":"midea_ir.command","request_id":"req-7",'
        '"payload":{"mode":"cool","temperature_c":24}}'
    )
    request_id, command = parse_command_message(raw)
    assert request_id == "req-7"
    assert command.mode == MideaMode.COOL
    assert command.temperature_c == 24


def test_encode_ack_message_error() -> None:
    raw = encode_ack_message(
        "req-err",
        ok=False,
        error_code="invalid_command",
        error_message="temperature_c out of range",
    )
    ack = decode_ack_message(raw)
    assert ack["request_id"] == "req-err"
    assert ack["ok"] is False
    assert ack["error_code"] == "invalid_command"
