from __future__ import annotations

from pathlib import Path

from smartblaster.vision.dataset import validate_labels_manifest


def test_validate_labels_manifest_accepts_valid_records(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True)
    (images_dir / "sample_001.jpg").write_bytes(b"img")

    labels_file = tmp_path / "labels.jsonl"
    labels_file.write_text(
        '{"filename":"sample_001.jpg","expected":{"mode":"cool","set_temperature":24.0,"fan_speed":"high","timer_set":true,"follow_me_enabled":true,"power_on":true}}\n',
        encoding="utf-8",
    )

    issues = validate_labels_manifest(labels_file, images_dir=images_dir)
    assert issues == []


def test_validate_labels_manifest_reports_invalid_fields_and_values(tmp_path: Path) -> None:
    labels_file = tmp_path / "labels.jsonl"
    labels_file.write_text(
        '{"filename":"sample_001.jpg","expected":{"mode":"cold","fan_speed":"turbo","timer_set":"yes","foo":1}}\n',
        encoding="utf-8",
    )

    issues = validate_labels_manifest(labels_file)

    assert any("unsupported expected field 'foo'" in issue for issue in issues)
    assert any("mode must be one of" in issue for issue in issues)
    assert any("fan_speed must be one of" in issue for issue in issues)
    assert any("timer_set must be true/false" in issue for issue in issues)


def test_validate_labels_manifest_reports_duplicate_and_missing_image(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True)

    labels_file = tmp_path / "labels.jsonl"
    labels_file.write_text(
        "\n".join(
            [
                '{"filename":"sample_001.jpg","expected":{"mode":"cool"}}',
                '{"filename":"sample_001.jpg","expected":{"mode":"cool"}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = validate_labels_manifest(labels_file, images_dir=images_dir)

    assert any("duplicate filename 'sample_001.jpg'" in issue for issue in issues)
    assert any("image file not found 'sample_001.jpg'" in issue for issue in issues)