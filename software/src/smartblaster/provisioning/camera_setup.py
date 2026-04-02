"""Camera setup helpers for captive portal preview and reference captures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import re
import threading
from typing import Callable

from PIL import Image, ImageDraw

from smartblaster.hardware.camera import CameraService
from smartblaster.services.reference_images import ReferenceImageStore
from smartblaster.vision.parser import ThermostatDisplayParser
from smartblaster.vision.registry import create_parser_for_model


@dataclass(frozen=True)
class CameraSetupStatus:
    frame_available: bool
    display_readable: bool
    focus_score: float
    focus_good: bool
    glare_ratio: float
    glare_low: bool
    exposure_score: float
    parser_confidence: float
    recommended_action: str
    parsed_summary: dict[str, object]


class CameraSetupService:
    def __init__(
        self,
        *,
        camera: CameraService,
        parser_factory: Callable[[str], ThermostatDisplayParser] = create_parser_for_model,
        reference_store: ReferenceImageStore | None = None,
        manage_camera_lifecycle: bool = True,
    ) -> None:
        self.camera = camera
        self.parser_factory = parser_factory
        self.reference_store = reference_store or ReferenceImageStore()
        self.manage_camera_lifecycle = manage_camera_lifecycle
        self._camera_access_lock = threading.Lock()

    def preview_frame(self, profile_id: str, *, overlay: bool = True) -> bytes:
        frame = self._capture_frame()
        if not overlay:
            # Return raw captured frame directly — bypasses PIL processing for a reliable live view.
            return frame
        _status, preview = self._analyze_frame(frame, profile_id=profile_id, overlay=overlay)
        return _encode_jpeg(preview)

    def status(self, profile_id: str) -> CameraSetupStatus:
        frame = self._capture_frame()
        status, _preview = self._analyze_frame(frame, profile_id=profile_id, overlay=False)
        return status

    def capture_reference(
        self,
        *,
        profile_id: str,
        phase: str,
        label: str | None = None,
        include_overlay: bool = True,
        reference_image_dir: Path | None = None,
    ) -> dict[str, object]:
        frame = self._capture_frame()
        status, preview = self._analyze_frame(frame, profile_id=profile_id, overlay=include_overlay)
        overlay_bytes = _encode_jpeg(preview) if include_overlay else None
        store = self.reference_store if reference_image_dir is None else ReferenceImageStore(reference_image_dir)
        return store.save_capture(
            frame=frame,
            profile_id=profile_id,
            phase=phase,
            label=label,
            metadata={
                "status": {
                    "frame_available": status.frame_available,
                    "display_readable": status.display_readable,
                    "focus_score": status.focus_score,
                    "focus_good": status.focus_good,
                    "glare_ratio": status.glare_ratio,
                    "glare_low": status.glare_low,
                    "exposure_score": status.exposure_score,
                    "parser_confidence": status.parser_confidence,
                    "recommended_action": status.recommended_action,
                    "parsed_summary": status.parsed_summary,
                }
            },
            overlay_frame=overlay_bytes,
        )

    def _capture_frame(self) -> bytes:
        with self._camera_access_lock:
            self.camera.start()  # Idempotent: no-op if already running; lazy-starts if not.
            try:
                frame = self.camera.capture_frame()
                if frame is None:
                    raise RuntimeError("camera did not return a frame")
                try:
                    _save_debug_test_image(frame)
                except Exception:
                    pass
                return frame
            finally:
                if self.manage_camera_lifecycle:
                    self.camera.stop()

    def _analyze_frame(self, frame: bytes, *, profile_id: str, overlay: bool) -> tuple[CameraSetupStatus, Image.Image]:
        parser = self.parser_factory(profile_id)
        base_image = Image.open(BytesIO(frame)).convert("RGB")
        gray = base_image.convert("L")

        focus_score = _focus_score(gray)
        focus_good = focus_score >= 0.045
        glare_ratio = _glare_ratio(gray)
        glare_low = glare_ratio <= 0.025
        exposure_score = _exposure_score(gray)

        display_readable = False
        parser_confidence = 0.0
        parsed_summary: dict[str, object] = {}
        preview = base_image.copy()

        try:
            state = parser.parse(frame)
            display_readable = True
            if state.confidence_by_field:
                parser_confidence = sum(state.confidence_by_field.values()) / len(state.confidence_by_field)
            parsed_summary = {
                "mode": state.mode.value,
                "set_temperature": state.set_temperature,
                "power_on": state.power_on,
                "fan_speed": state.fan_speed.value,
            }

            if overlay and hasattr(parser, "debug_overlays"):
                overlays = parser.debug_overlays(frame)  # type: ignore[attr-defined]
                # Use original_bounds: full frame with boundary detection drawn on it.
                # rois_selected is a normalized crop and is not suitable for portal preview.
                preview = (
                    overlays.get("original_bounds")
                    or next(iter(overlays.values()), preview)
                ).convert("RGB")
        except Exception as ex:
            parsed_summary = {"error": str(ex)}

        status = CameraSetupStatus(
            frame_available=True,
            display_readable=display_readable,
            focus_score=round(focus_score, 4),
            focus_good=focus_good,
            glare_ratio=round(glare_ratio, 4),
            glare_low=glare_low,
            exposure_score=round(exposure_score, 4),
            parser_confidence=round(parser_confidence, 4),
            recommended_action=_recommend_action(
                display_readable=display_readable,
                focus_good=focus_good,
                glare_low=glare_low,
                exposure_score=exposure_score,
                parser_confidence=parser_confidence,
            ),
            parsed_summary=parsed_summary,
        )
        _draw_status_banner(preview, status)
        return (status, preview)


def _save_debug_test_image(frame_bytes: bytes, folder: str = "data/test_images", max_images: int = 100) -> None:
    """Save frame as test_imageNNN.jpg, incrementing and looping at max_images."""
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    counter_file = folder_path / "counter.txt"
    if counter_file.exists():
        try:
            n = int(counter_file.read_text().strip())
        except Exception:
            n = 1
    else:
        n = 1
    img_path = folder_path / f"test_image{n:03d}.jpg"
    img_path.write_bytes(frame_bytes)
    n = n + 1 if n < max_images else 1
    counter_file.write_text(str(n))


def _encode_jpeg(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _focus_score(image: Image.Image) -> float:
    px = image.load()
    width, height = image.size
    if width < 2 or height < 2:
        return 0.0

    energy = 0.0
    count = 0
    for y in range(height - 1):
        for x in range(width - 1):
            center = float(px[x, y])
            energy += abs(center - float(px[x + 1, y]))
            energy += abs(center - float(px[x, y + 1]))
            count += 2
    if count <= 0:
        return 0.0
    return min(1.0, (energy / count) / 255.0)


def _glare_ratio(image: Image.Image) -> float:
    hist = image.histogram()
    bright = sum(hist[245:256])
    total = max(1, image.size[0] * image.size[1])
    return bright / total


def _exposure_score(image: Image.Image) -> float:
    hist = image.histogram()
    total = max(1, image.size[0] * image.size[1])
    mean = sum(i * count for i, count in enumerate(hist)) / total
    distance = abs(mean - 128.0) / 128.0
    return max(0.0, 1.0 - distance)


def _recommend_action(
    *,
    display_readable: bool,
    focus_good: bool,
    glare_low: bool,
    exposure_score: float,
    parser_confidence: float,
) -> str:
    if not display_readable:
        return "Aim the camera at the thermostat and increase zoom until the display is readable."
    if not focus_good:
        return "Adjust focus until thermostat digits and icons look crisp."
    if not glare_low:
        return "Reduce glare or change camera angle slightly to avoid washed-out LCD segments."
    if exposure_score < 0.45:
        return "Improve lighting balance so the display is neither too dark nor too bright."
    if parser_confidence < 0.6:
        return "Fine-tune framing and zoom so the parser overlay stays stable."
    return "Camera alignment looks good. Save a reference image and continue setup."


def _draw_status_banner(image: Image.Image, status: CameraSetupStatus) -> None:
    draw = ImageDraw.Draw(image)
    banner_h = 44
    banner_color = (28, 112, 58) if status.recommended_action.startswith("Camera alignment looks good") else (150, 90, 20)
    if not status.display_readable:
        banner_color = (150, 30, 30)

    draw.rectangle((0, 0, image.size[0], banner_h), fill=banner_color)
    summary = (
        f"display={'yes' if status.display_readable else 'no'}  "
        f"focus={status.focus_score:.2f}  "
        f"glare={status.glare_ratio:.2f}  "
        f"conf={status.parser_confidence:.2f}"
    )
    draw.text((8, 6), summary, fill=(255, 255, 255))
    draw.text((8, 24), status.recommended_action, fill=(255, 255, 255))