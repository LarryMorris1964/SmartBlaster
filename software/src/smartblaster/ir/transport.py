"""Pi-side transport helper for the ESP32 IR bridge contract."""

from __future__ import annotations

import json
import time
from typing import TextIO

from smartblaster.ir.command import MideaIrCommand
from smartblaster.ir.esp32_schema import decode_ack_message, encode_command_message


class Esp32IrBridgeClient:
    """Sends Midea commands and waits for matching ACK frames.

    The stream must be line-oriented JSON (e.g., serial text wrapper or socket file-like object).
    """

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def send_command(self, command: MideaIrCommand, request_id: str, timeout_s: float = 2.0) -> dict[str, object]:
        frame = encode_command_message(command, request_id=request_id)
        self.stream.write(frame)
        self.stream.flush()
        return self.wait_for_ack(request_id=request_id, timeout_s=timeout_s)

    def wait_for_ack(self, request_id: str, timeout_s: float = 2.0) -> dict[str, object]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            line = self.stream.readline()
            if not line:
                continue

            try:
                ack = decode_ack_message(line)
            except (json.JSONDecodeError, ValueError):
                continue

            if ack.get("request_id") != request_id:
                continue
            return ack

        raise TimeoutError(f"Timed out waiting for ACK request_id={request_id}")
