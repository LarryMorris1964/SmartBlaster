from pathlib import Path

from smartblaster.services.reference_images import ReferenceImageStore
from smartblaster.services.reference_offload import ReferenceOffloadService


class FakeSuccessTransport:
    def __init__(self) -> None:
        self.uploaded_labels: list[str] = []

    def upload_capture(self, *, metadata, metadata_file, raw_image, overlay_image):  # noqa: ANN001
        _ = (metadata_file, raw_image, overlay_image)
        self.uploaded_labels.append(str(metadata.get("label")))
        return f"remote-{metadata.get('label')}"


class FakeFailTransport:
    def upload_capture(self, *, metadata, metadata_file, raw_image, overlay_image):  # noqa: ANN001
        _ = (metadata, metadata_file, raw_image, overlay_image)
        raise RuntimeError("upload failed")


def test_run_once_offloads_pending_fifo(tmp_path: Path) -> None:
    store = ReferenceImageStore(tmp_path / "refs", retention_by_phase={"default": 20})
    store.save_capture(frame=b"1", profile_id="midea", phase="runtime_parse_failure", label="one")
    store.save_capture(frame=b"2", profile_id="midea", phase="runtime_parse_failure", label="two")

    transport = FakeSuccessTransport()
    svc = ReferenceOffloadService(store=store, transport=transport, batch_size=10)

    result = svc.run_once()

    assert result.scanned == 2
    assert result.offloaded == 2
    assert result.failed == 0
    assert transport.uploaded_labels == ["one", "two"]
    assert store.list_pending_offload() == []


def test_run_once_marks_failure_attempts(tmp_path: Path) -> None:
    store = ReferenceImageStore(tmp_path / "refs", retention_by_phase={"default": 20})
    saved = store.save_capture(frame=b"1", profile_id="midea", phase="training_periodic", label="hourly")

    svc = ReferenceOffloadService(store=store, transport=FakeFailTransport(), batch_size=10)
    result = svc.run_once()

    assert result.scanned == 1
    assert result.offloaded == 0
    assert result.failed == 1

    metadata_file = Path(str(saved["metadata_file"]))
    text = metadata_file.read_text(encoding="utf-8")
    assert '"attempt_count": 1' in text
    assert '"status": "pending"' in text
