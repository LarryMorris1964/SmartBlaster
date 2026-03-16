"""Reference-image offload skeleton for future central upload workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from smartblaster.services.reference_images import ReferenceImageStore


class ReferenceOffloadTransport(Protocol):
    """Upload one capture payload to remote storage.

    Return a remote identifier when successful.
    Raise an exception on failure.
    """

    def upload_capture(
        self,
        *,
        metadata: dict[str, object],
        metadata_file: Path,
        raw_image: bytes | None,
        overlay_image: bytes | None,
    ) -> str | None:
        ...


class NoopReferenceOffloadTransport:
    """Placeholder transport for development.

    This intentionally does not upload anything; it simply returns a marker ID.
    """

    def upload_capture(
        self,
        *,
        metadata: dict[str, object],
        metadata_file: Path,
        raw_image: bytes | None,
        overlay_image: bytes | None,
    ) -> str | None:
        _ = (metadata, metadata_file, raw_image, overlay_image)
        return "noop-offload"


@dataclass(frozen=True)
class ReferenceOffloadResult:
    scanned: int
    offloaded: int
    failed: int


class ReferenceOffloadService:
    """Drains pending reference captures FIFO and marks offload status.

    This is a future-work skeleton and is disabled in runtime by default.
    """

    def __init__(
        self,
        *,
        store: ReferenceImageStore,
        transport: ReferenceOffloadTransport,
        batch_size: int = 25,
    ) -> None:
        self.store = store
        self.transport = transport
        self.batch_size = max(1, int(batch_size))

    def run_once(self, *, phases: list[str] | None = None) -> ReferenceOffloadResult:
        pending = self.store.list_pending_offload(phases=phases, limit=self.batch_size)
        scanned = len(pending)
        offloaded = 0
        failed = 0

        for item in pending:
            metadata_file = Path(str(item["metadata_file"]))
            metadata = self._read_metadata(metadata_file)
            if metadata is None:
                self.store.mark_offload_attempt_failed(metadata_file)
                failed += 1
                continue

            raw_image = self._read_optional_bytes(metadata.get("raw_image"))
            overlay_image = self._read_optional_bytes(metadata.get("overlay_image"))

            try:
                remote_id = self.transport.upload_capture(
                    metadata=metadata,
                    metadata_file=metadata_file,
                    raw_image=raw_image,
                    overlay_image=overlay_image,
                )
            except Exception:
                self.store.mark_offload_attempt_failed(metadata_file)
                failed += 1
                continue

            self.store.mark_offloaded(metadata_file, remote_id=remote_id)
            offloaded += 1

        return ReferenceOffloadResult(scanned=scanned, offloaded=offloaded, failed=failed)

    def _read_metadata(self, metadata_file: Path) -> dict[str, object] | None:
        from smartblaster.services.reference_images import _read_json  # local import keeps module boundary light

        return _read_json(metadata_file)

    def _read_optional_bytes(self, path_value: object) -> bytes | None:
        if not isinstance(path_value, str) or not path_value.strip():
            return None
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            return None
        try:
            return path.read_bytes()
        except Exception:
            return None
