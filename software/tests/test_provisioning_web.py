from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from smartblaster.provisioning.camera_setup import CameraSetupService, ReferenceImageStore
from smartblaster.provisioning.service import ProvisioningService
from smartblaster.provisioning.web import create_provisioning_app
from smartblaster.vision.models import DisplayMode, FanSpeedLevel, ThermostatDisplayState


def test_create_provisioning_app() -> None:
    app = create_provisioning_app(ProvisioningService())
    assert app.title == "SmartBlaster Provisioning"


class FakeCamera:
    def start(self) -> None:
        return

    def stop(self) -> None:
        return

    def capture_frame(self) -> bytes:
        image = Image.new("RGB", (320, 180), color=(210, 210, 210))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return buffer.getvalue()


class FakeParser:
    model_id = "midea_kjr_12b_dp_t"

    def parse(self, frame: bytes) -> ThermostatDisplayState:  # noqa: ARG002
        return ThermostatDisplayState(
            model_id=self.model_id,
            power_on=True,
            mode=DisplayMode.COOL,
            set_temperature=24.0,
            fan_speed=FanSpeedLevel.HIGH,
            timer_set=False,
            follow_me_enabled=False,
            confidence_by_field={"mode": 1.0, "set_temperature": 0.9, "fan_speed": 0.8},
        )

    def debug_overlays(self, frame: bytes) -> dict[str, Image.Image]:  # noqa: ARG002
        return {"rois_selected": Image.new("RGB", (320, 180), color=(80, 120, 90))}


def _fake_parser_factory(model_id: str) -> FakeParser:  # noqa: ARG001
    return FakeParser()


def test_camera_status_endpoint(tmp_path: Path) -> None:
    app = create_provisioning_app(
        ProvisioningService(),
        camera_setup_service=CameraSetupService(
            camera=FakeCamera(),
            parser_factory=_fake_parser_factory,
            reference_store=ReferenceImageStore(tmp_path / "references"),
        ),
    )
    client = TestClient(app)

    response = client.get("/api/camera/status", params={"thermostat_profile_id": "midea_kjr_12b_dp_t"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_readable"] is True
    assert payload["parsed_summary"]["mode"] == "cool"
    assert "recommended_action" in payload


def test_camera_preview_endpoint_returns_jpeg(tmp_path: Path) -> None:
    app = create_provisioning_app(
        ProvisioningService(),
        camera_setup_service=CameraSetupService(
            camera=FakeCamera(),
            parser_factory=_fake_parser_factory,
            reference_store=ReferenceImageStore(tmp_path / "references"),
        ),
    )
    client = TestClient(app)

    response = client.get("/api/camera/preview.jpg", params={"thermostat_profile_id": "midea_kjr_12b_dp_t"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.content[:2] == b"\xff\xd8"


def test_camera_reference_capture_persists_files(tmp_path: Path) -> None:
    reference_dir = tmp_path / "references"
    app = create_provisioning_app(
        ProvisioningService(),
        camera_setup_service=CameraSetupService(
            camera=FakeCamera(),
            parser_factory=_fake_parser_factory,
            reference_store=ReferenceImageStore(reference_dir),
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/api/camera/reference-capture",
        json={
            "thermostat_profile_id": "midea_kjr_12b_dp_t",
            "phase": "install_camera_setup",
            "label": "installer-approved",
            "include_overlay": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert Path(payload["raw_image"]).exists()
    assert Path(payload["metadata_file"]).exists()
    assert Path(payload["overlay_image"]).exists()


def test_setup_page_mentions_camera_setup() -> None:
    app = create_provisioning_app(ProvisioningService())
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Camera Setup" in response.text
    assert "Save Reference Image" in response.text
