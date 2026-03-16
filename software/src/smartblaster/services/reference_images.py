"""Shared reference image storage for setup, runtime diagnostics, and training captures."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


class ReferenceImageStore:
    """Persist raw/overlay reference images with JSON sidecar metadata."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path("data/reference_images")

    def save_capture(
        self,
        *,
        frame: bytes | None,
        profile_id: str,
        phase: str,
        label: str | None = None,
        metadata: dict[str, object] | None = None,
        overlay_frame: bytes | None = None,
    ) -> dict[str, object]:
        timestamp = datetime.now(timezone.utc)
        safe_phase = _slug(phase or "unspecified")
        safe_profile = _slug(profile_id or "unknown-profile")
        safe_label = _slug(label or "reference")

        phase_dir = self.base_dir / safe_phase
        phase_dir.mkdir(parents=True, exist_ok=True)

        stem = f"{timestamp.strftime('%Y%m%dT%H%M%S.%fZ')}_{safe_profile}_{safe_label}"

        raw_path: Path | None = None
        if frame is not None:
            raw_path = phase_dir / f"{stem}.jpg"
            raw_path.write_bytes(frame)

        overlay_path: Path | None = None
        if overlay_frame is not None:
            overlay_path = phase_dir / f"{stem}.overlay.jpg"
            overlay_path.write_bytes(overlay_frame)

        metadata_payload = {
            "captured_at_utc": timestamp.isoformat(),
            "profile_id": profile_id,
            "phase": phase,
            "label": label,
            "raw_image": str(raw_path) if raw_path is not None else None,
            "overlay_image": str(overlay_path) if overlay_path is not None else None,
            "metadata": metadata or {},
        }

        metadata_path = phase_dir / f"{stem}.json"
        metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")
        return {
            "captured_at_utc": metadata_payload["captured_at_utc"],
            "raw_image": str(raw_path) if raw_path is not None else None,
            "overlay_image": str(overlay_path) if overlay_path is not None else None,
            "metadata_file": str(metadata_path),
        }


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    normalized = normalized.strip("-._")
    return normalized or "item"