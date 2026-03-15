"""SmartBlaster CLI for sending Midea commands to the ESP32 bridge."""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import TextIO

from smartblaster.ir.command import MideaFan, MideaIrCommand, MideaMode, MideaPreset, MideaSwing
from smartblaster.ir.transport import Esp32IrBridgeClient


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smartblaster-cli", description="Send SmartBlaster IR commands")
    parser.add_argument("--serial-port", default="COM3", help="Serial port (e.g. COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")

    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Send HVAC state command")
    set_cmd.add_argument("--mode", choices=[m.value for m in MideaMode], required=True)
    set_cmd.add_argument("--temp", type=float, dest="temperature_c")
    set_cmd.add_argument("--fan", choices=[f.value for f in MideaFan], default=MideaFan.AUTO.value)
    set_cmd.add_argument("--swing", choices=[s.value for s in MideaSwing], default=MideaSwing.OFF.value)
    set_cmd.add_argument("--preset", choices=[p.value for p in MideaPreset], default=MideaPreset.NONE.value)
    set_cmd.add_argument("--follow-me", type=float, dest="follow_me_c")
    set_cmd.add_argument("--beeper", action="store_true")

    sub.add_parser("off", help="Power off HVAC")

    return parser


def build_command_from_args(args: argparse.Namespace) -> MideaIrCommand:
    if args.command == "off":
        return MideaIrCommand(mode=MideaMode.OFF)

    return MideaIrCommand(
        mode=MideaMode(args.mode),
        temperature_c=args.temperature_c,
        fan=MideaFan(args.fan),
        swing=MideaSwing(args.swing),
        preset=MideaPreset(args.preset),
        follow_me_c=args.follow_me_c,
        beeper=args.beeper,
    )


def _open_serial_as_text(port: str, baud: int) -> TextIO:
    try:
        import serial  # type: ignore
    except ImportError as ex:
        raise RuntimeError("pyserial is required for CLI serial transport") from ex

    ser = serial.Serial(port=port, baudrate=baud, timeout=0.1)
    return ser  # pyserial object provides read/write/flush/readline compatible APIs


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    command = build_command_from_args(args)

    request_id = str(uuid.uuid4())
    stream = _open_serial_as_text(args.serial_port, args.baud)
    client = Esp32IrBridgeClient(stream)

    ack = client.send_command(command, request_id=request_id)
    if not ack.get("ok", False):
        print(f"FAILED: {ack}")
        return 2

    print(f"OK request_id={request_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
