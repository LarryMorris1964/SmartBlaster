"""Thermostat status request pipeline: capture -> parse -> log (+ optional image)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
import json
from pathlib import Path

from smartblaster.hardware.camera import CameraService
from smartblaster.services.reference_images import ReferenceImageStore
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
        reference_capture_on_parse_failure: bool = False,
        reference_image_dir: Path | None = None,
        reference_image_store: ReferenceImageStore | None = None,
    ) -> None:
        self.camera = camera
        self.parser = parser
        self.history_file = history_file
        self.diagnostic_save_images = diagnostic_save_images
        self.diagnostic_image_dir = diagnostic_image_dir or Path("data/status_images")
        self.manage_camera_lifecycle = manage_camera_lifecycle
        self.reference_capture_on_parse_failure = reference_capture_on_parse_failure
        self.reference_image_store = reference_image_store or ReferenceImageStore(
            reference_image_dir or Path("data/reference_images")
        )

    def request_status(self) -> ThermostatDisplayState:
        if self.manage_camera_lifecycle:
            self.camera.start()
        try:
            frame = self.camera.capture_frame()
            if frame is None:
                self._capture_failure_reference(
                    frame=None,
                    reason="camera_no_frame",
                    error=RuntimeError("camera did not return a frame"),
                )
                raise RuntimeError("camera did not return a frame")

            try:
                state = self.parser.parse(frame)
            except Exception as ex:
                self._capture_failure_reference(frame=frame, reason="runtime_parse_failure", error=ex)
                raise

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

    def _capture_failure_reference(self, *, frame: bytes | None, reason: str, error: Exception) -> None:
        if not self.reference_capture_on_parse_failure:
            return

        overlay_frame = None
        if frame is not None and hasattr(self.parser, "debug_overlays"):
            try:
                overlays = self.parser.debug_overlays(frame)  # type: ignore[attr-defined]
                image = (
                    overlays.get("rois_selected")
                    or overlays.get("original_bounds")
                    or next(iter(overlays.values()), None)
                )
                if image is not None:
                    buffer = BytesIO()
                    image.save(buffer, format="JPEG", quality=85)
                    overlay_frame = buffer.getvalue()
            except Exception:
                overlay_frame = None

        self.reference_image_store.save_capture(
            frame=frame,
            profile_id=self.parser.model_id,
            phase=reason,
            label=type(error).__name__,
            metadata={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "history_file": str(self.history_file),
                "diagnostic_save_images": self.diagnostic_save_images,
                "diagnostic_image_dir": str(self.diagnostic_image_dir),
                "manage_camera_lifecycle": self.manage_camera_lifecycle,
                "parser_model_id": self.parser.model_id,
            },
            overlay_frame=overlay_frame,
        )


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
