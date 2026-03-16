from pathlib import Path

from smartblaster.services.reference_images import ReferenceImageStore


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_fifo_retention_prunes_oldest_first(tmp_path: Path) -> None:
    store = ReferenceImageStore(
        tmp_path / "references",
        retention_by_phase={"training_periodic": 2, "default": 2},
    )

    store.save_capture(frame=b"a", profile_id="midea_kjr_12b_dp_t", phase="training_periodic", label="one")
    store.save_capture(frame=b"b", profile_id="midea_kjr_12b_dp_t", phase="training_periodic", label="two")
    store.save_capture(frame=b"c", profile_id="midea_kjr_12b_dp_t", phase="training_periodic", label="three")

    phase_dir = tmp_path / "references" / "training_periodic"
    metadata_files = sorted(phase_dir.glob("*.json"))
    assert len(metadata_files) == 2

    payloads = [_read(path) for path in metadata_files]
    assert any('"label": "two"' in text for text in payloads)
    assert any('"label": "three"' in text for text in payloads)
    assert all('"label": "one"' not in text for text in payloads)


def test_pending_offload_and_mark_offloaded(tmp_path: Path) -> None:
    store = ReferenceImageStore(tmp_path / "references")

    result = store.save_capture(
        frame=b"img",
        profile_id="midea_kjr_12b_dp_t",
        phase="runtime_parse_failure",
        label="ValueError",
    )

    pending = store.list_pending_offload()
    assert len(pending) == 1
    assert pending[0]["phase"] == "runtime_parse_failure"

    metadata_file = Path(str(result["metadata_file"]))
    store.mark_offloaded(metadata_file, remote_id="upload-123")

    pending_after = store.list_pending_offload()
    assert pending_after == []

    text = metadata_file.read_text(encoding="utf-8")
    assert '"status": "offloaded"' in text
    assert '"remote_id": "upload-123"' in text


def test_mark_offload_attempt_failed_increments_counter(tmp_path: Path) -> None:
    store = ReferenceImageStore(tmp_path / "references")
    result = store.save_capture(
        frame=b"img",
        profile_id="midea_kjr_12b_dp_t",
        phase="install_camera_setup",
    )

    metadata_file = Path(str(result["metadata_file"]))
    store.mark_offload_attempt_failed(metadata_file)
    store.mark_offload_attempt_failed(metadata_file)

    text = metadata_file.read_text(encoding="utf-8")
    assert '"attempt_count": 2' in text
