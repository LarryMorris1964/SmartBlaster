from pathlib import Path

from PIL import Image

from smartblaster.services.reference_images import ReferenceImageStore
from smartblaster.services.thermostat_status import ThermostatStatusService
from smartblaster.vision.models import (
    DisplayMode,
    DisplayTemperatureUnit,
    FanSpeedLevel,
    ThermostatDisplayState,
)


class FakeCamera:
    def __init__(self, frame: bytes | None = b"fake-jpeg") -> None:
        self.frame = frame
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def capture_frame(self) -> bytes | None:
        return self.frame

    def stop(self) -> None:
        self.stopped = True


class FakeParser:
    model_id = "midea_kjr_12b_dp_t"

    def parse(self, frame: bytes) -> ThermostatDisplayState:  # noqa: ARG002
        return ThermostatDisplayState(
            model_id=self.model_id,
            power_on=True,
            mode=DisplayMode.COOL,
            set_temperature=24.0,
            temperature_unit=DisplayTemperatureUnit.C,
            fan_speed=FanSpeedLevel.HIGH,
            timer_set=True,
            follow_me_enabled=False,
        )


class FailingParser:
    model_id = "midea_kjr_12b_dp_t"

    def parse(self, frame: bytes) -> ThermostatDisplayState:  # noqa: ARG002
        raise ValueError("parse failed")

    def debug_overlays(self, frame: bytes) -> dict[str, Image.Image]:  # noqa: ARG002
        return {"original_bounds": Image.new("RGB", (64, 32), color=(120, 140, 160))}


def test_request_status_logs_history(tmp_path: Path) -> None:
    history = tmp_path / "history.log"
    camera = FakeCamera()
    service = ThermostatStatusService(
        camera=camera,
        parser=FakeParser(),
        history_file=history,
    )

    state = service.request_status()

    assert state.mode == DisplayMode.COOL
    assert history.exists()
    text = history.read_text(encoding="utf-8")
    assert "\"mode\": \"cool\"" in text
    assert "\"fan_speed\": \"high\"" in text
    assert "\"timer_set\": true" in text
    assert camera.started is True
    assert camera.stopped is True


def test_request_status_saves_image_in_diagnostic_mode(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    service = ThermostatStatusService(
        camera=FakeCamera(frame=b"img"),
        parser=FakeParser(),
        history_file=tmp_path / "history.log",
        diagnostic_save_images=True,
        diagnostic_image_dir=image_dir,
    )

    service.request_status()

    files = list(image_dir.glob("*.jpg"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"img"


def test_request_status_raises_when_no_frame(tmp_path: Path) -> None:
    service = ThermostatStatusService(
        camera=FakeCamera(frame=None),
        parser=FakeParser(),
        history_file=tmp_path / "history.log",
    )
    try:
        service.request_status()
        assert False, "expected RuntimeError"
    except RuntimeError as ex:
        assert "camera did not return a frame" in str(ex)


def test_request_status_does_not_manage_camera_when_disabled(tmp_path: Path) -> None:
    camera = FakeCamera(frame=b"img")
    service = ThermostatStatusService(
        camera=camera,
        parser=FakeParser(),
        history_file=tmp_path / "history.log",
        manage_camera_lifecycle=False,
    )

    service.request_status()

    assert camera.started is False
    assert camera.stopped is False


def test_request_status_saves_reference_capture_on_parse_failure(tmp_path: Path) -> None:
    reference_dir = tmp_path / "references"
    service = ThermostatStatusService(
        camera=FakeCamera(frame=b"img"),
        parser=FailingParser(),
        history_file=tmp_path / "history.log",
        reference_capture_on_parse_failure=True,
        reference_image_store=ReferenceImageStore(reference_dir),
    )

    try:
        service.request_status()
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "parse failed" in str(ex)

    saved = list((reference_dir / "runtime_parse_failure").iterdir())
    assert any(path.suffix == ".jpg" for path in saved)
    assert any(path.name.endswith(".overlay.jpg") for path in saved)
    metadata_files = [path for path in saved if path.suffix == ".json"]
    assert len(metadata_files) == 1
    metadata = metadata_files[0].read_text(encoding="utf-8")
    assert "parse failed" in metadata
    assert "ValueError" in metadata
