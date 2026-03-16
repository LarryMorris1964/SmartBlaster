"""Thermostat status request pipeline: capture -> parse -> log (+ optional image)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path

from smartblaster.hardware.camera import CameraService
from smartblaster.vision.models import ThermostatDisplayState
from smartblaster.vision.parser import ThermostatDisplayParser


class ThermostatStatusService:
    def __init__(
        self,
        *,
        camera: CameraService,
        parser: ThermostatDisplayParser,
        history_file: Path,
        diagnostic_save_images: bool = False,
        diagnostic_image_dir: Path | None = None,
        manage_camera_lifecycle: bool = True,
    ) -> None:
        self.camera = camera
        self.parser = parser
        self.history_file = history_file
        self.diagnostic_save_images = diagnostic_save_images
        self.diagnostic_image_dir = diagnostic_image_dir or Path("data/status_images")
        self.manage_camera_lifecycle = manage_camera_lifecycle

    def request_status(self) -> ThermostatDisplayState:
        if self.manage_camera_lifecycle:
            self.camera.start()
        try:
            frame = self.camera.capture_frame()
            if frame is None:
                raise RuntimeError("camera did not return a frame")

            state = self.parser.parse(frame)
            timestamp = datetime.now(timezone.utc)
            self._append_history(timestamp, state)
            if self.diagnostic_save_images:
                self._save_image(timestamp, frame)
            return state
        finally:
            if self.manage_camera_lifecycle:
                self.camera.stop()

    def _append_history(self, timestamp: datetime, state: ThermostatDisplayState) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts_utc": timestamp.isoformat(),
            **_state_to_jsonable_dict(state),
        }
        with self.history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _save_image(self, timestamp: datetime, frame: bytes) -> None:
        self.diagnostic_image_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{timestamp.strftime('%Y%m%dT%H%M%S.%fZ')}_{self.parser.model_id}.jpg"
        output_file = self.diagnostic_image_dir / filename
        output_file.write_bytes(frame)


def _state_to_jsonable_dict(state: ThermostatDisplayState) -> dict[str, object]:
    payload = asdict(state)

    mode = payload.get("mode")
    if isinstance(mode, Enum):
        payload["mode"] = mode.value

    fan_speed = payload.get("fan_speed")
    if isinstance(fan_speed, Enum):
        payload["fan_speed"] = fan_speed.value

    temperature_unit = payload.get("temperature_unit")
    if isinstance(temperature_unit, Enum):
        payload["temperature_unit"] = temperature_unit.value

    return payload
