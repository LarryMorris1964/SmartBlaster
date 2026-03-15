"""Infrared control abstraction."""

from __future__ import annotations

import uuid

from smartblaster.ir.command import MideaIrCommand
from smartblaster.ir.esp32_schema import encode_command_message


class IrService:
    def __init__(self, tx_gpio: int, rx_gpio: int, dry_run: bool = True) -> None:
        self.tx_gpio = tx_gpio
        self.rx_gpio = rx_gpio
        self.dry_run = dry_run

    def send(self, code: str) -> None:
        # TODO: replace with real waveform transmission
        if self.dry_run:
            print(f"[dry-run] IR send on GPIO {self.tx_gpio}: {code}")

    def send_midea_command(self, command: MideaIrCommand) -> str:
        request_id = str(uuid.uuid4())
        frame = encode_command_message(command, request_id=request_id)
        self.send(frame.strip())
        return request_id

    def listen(self) -> str | None:
        # TODO: decode incoming IR signal from rx pin
        return None
