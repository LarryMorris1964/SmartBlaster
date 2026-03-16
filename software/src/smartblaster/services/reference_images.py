"""Shared reference image storage for setup, runtime diagnostics, and training captures."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re


DEFAULT_RETENTION_BY_PHASE: dict[str, int] = {
    # Highest value: parse failures are the most useful diagnostics.
    "runtime_parse_failure": 2000,
    "camera_no_frame": 1000,
    # Install captures are useful but bounded.
    "install_camera_setup": 80,
    # Capability-validation runs can generate many examples.
    "validate_capabilities": 4000,
    # Periodic training snapshots are lower value per frame.
    "training_periodic": 240,
    # Fallback for unknown/new phases.
    "default": 400,
}


class ReferenceImageStore:
    """Persist raw/overlay reference images with JSON sidecar metadata."""

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        retention_by_phase: dict[str, int] | None = None,
    ) -> None:
        self.base_dir = base_dir or Path("data/reference_images")
        self.retention_by_phase = {
            key: max(1, int(value))
            for key, value in (retention_by_phase or DEFAULT_RETENTION_BY_PHASE).items()
        }

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
            "offload": {
                "status": "pending",
                "attempt_count": 0,
                "last_attempt_utc": None,
                "offloaded_at_utc": None,
                "remote_id": None,
            },
        }

        metadata_path = phase_dir / f"{stem}.json"
        metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")
        self._prune_phase_dir(phase_dir, phase=safe_phase)
        return {
            "captured_at_utc": metadata_payload["captured_at_utc"],
            "raw_image": str(raw_path) if raw_path is not None else None,
            "overlay_image": str(overlay_path) if overlay_path is not None else None,
            "metadata_file": str(metadata_path),
        }

    def list_pending_offload(
        self,
        *,
        phases: list[str] | None = None,
        limit: int = 200,
    ) -> list[dict[str, object]]:
        """Return pending captures ordered oldest-first for FIFO offload."""
        allowed = {_slug(phase) for phase in phases} if phases else None
        pending: list[dict[str, object]] = []

        for metadata_path in sorted(self.base_dir.glob("*/*.json")):
            if not metadata_path.is_file():
                continue
            phase = metadata_path.parent.name
            if allowed is not None and phase not in allowed:
                continue

            payload = _read_json(metadata_path)
            if payload is None:
                continue
            offload = payload.get("offload")
            if not isinstance(offload, dict):
                continue
            if offload.get("status") == "offloaded":
                continue

            pending.append(
                {
                    "phase": phase,
                    "metadata_file": str(metadata_path),
                    "captured_at_utc": payload.get("captured_at_utc"),
                    "profile_id": payload.get("profile_id"),
                    "raw_image": payload.get("raw_image"),
                    "overlay_image": payload.get("overlay_image"),
                    "offload": offload,
                }
            )
            if len(pending) >= limit:
                break
        return pending

    def mark_offloaded(self, metadata_file: Path, *, remote_id: str | None = None) -> None:
        payload = _read_json(metadata_file)
        if payload is None:
            return
        offload = payload.get("offload")
        if not isinstance(offload, dict):
            offload = {}

        offload["status"] = "offloaded"
        offload["offloaded_at_utc"] = datetime.now(timezone.utc).isoformat()
        offload["remote_id"] = remote_id
        payload["offload"] = offload
        metadata_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def mark_offload_attempt_failed(self, metadata_file: Path) -> None:
        payload = _read_json(metadata_file)
        if payload is None:
            return
        offload = payload.get("offload")
        if not isinstance(offload, dict):
            offload = {}

        attempts = int(offload.get("attempt_count", 0)) + 1
        offload["status"] = "pending"
        offload["attempt_count"] = attempts
        offload["last_attempt_utc"] = datetime.now(timezone.utc).isoformat()
        payload["offload"] = offload
        metadata_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _prune_phase_dir(self, phase_dir: Path, *, phase: str) -> None:
        max_entries = self.retention_by_phase.get(phase, self.retention_by_phase.get("default", 400))
        # FIFO retention: metadata names start with UTC timestamp, so lexical sort
        # gives oldest-first and pruning removes oldest captures first.
        metadata_files = sorted(path for path in phase_dir.glob("*.json") if path.is_file())
        excess = len(metadata_files) - max_entries
        if excess <= 0:
            return

        for metadata_path in metadata_files[:excess]:
            stem = metadata_path.stem
            for suffix in (".json", ".jpg", ".overlay.jpg"):
                file_path = phase_dir / f"{stem}{suffix}"
                if file_path.exists():
                    file_path.unlink()


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    normalized = normalized.strip("-._")
    return normalized or "item"


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload