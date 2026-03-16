from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from smartblaster.provisioning.camera_setup import CameraSetupService, ReferenceImageStore
from smartblaster.provisioning.service import ProvisioningService
from smartblaster.provisioning.update import UpdateApplyResult, UpdateStatus
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


class FakeUpdater:
    def status(self) -> UpdateStatus:
        return UpdateStatus(
            enabled=True,
            repo="owner/repo",
            current_version="0.1.0",
            latest_version="0.2.0",
            update_available=True,
            release_url="https://github.com/owner/repo/releases/tag/v0.2.0",
            error=None,
        )

    def apply(self, target_version: str | None = None) -> UpdateApplyResult:
        return UpdateApplyResult(
            ok=True,
            message="Update installed. Restart required.",
            command="python -m pip install ...",
            target_version=target_version or "v0.2.0",
            restart_required=True,
            stdout="done",
            stderr=None,
        )


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
    app = create_provisioning_app(ProvisioningService(), update_service=FakeUpdater())
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Camera Setup" in response.text
    assert "Save Reference Image" in response.text
    assert "Device Name" in response.text
    assert "Software Version" in response.text
    assert "Owner's Manual" in response.text
    assert "App Update (GitHub)" in response.text
    assert "Reboot Device" in response.text


def test_device_info_endpoint_uses_saved_name(tmp_path: Path) -> None:
    state_file = tmp_path / "device_setup.json"
    state_file.write_text('{"device_name": "Bedroom SmartBlaster"}', encoding="utf-8")

    app = create_provisioning_app(ProvisioningService(state_file=state_file))
    client = TestClient(app)

    response = client.get("/api/device-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["device_name"] == "Bedroom SmartBlaster"
    assert "software_version" in payload


def test_portal_docs_endpoints_return_text() -> None:
    app = create_provisioning_app(ProvisioningService())
    client = TestClient(app)

    readme_response = client.get("/api/readme")
    manual_response = client.get("/api/owners-manual")

    assert readme_response.status_code == 200
    assert manual_response.status_code == 200
    assert "text" in readme_response.json()
    assert "text" in manual_response.json()


def test_update_status_endpoint_returns_payload() -> None:
    app = create_provisioning_app(ProvisioningService(), update_service=FakeUpdater())
    client = TestClient(app)

    response = client.get("/api/update/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["update_available"] is True
    assert payload["latest_version"] == "0.2.0"


def test_update_apply_endpoint_returns_success() -> None:
    app = create_provisioning_app(ProvisioningService(), update_service=FakeUpdater())
    client = TestClient(app)

    response = client.post("/api/update/apply", json={"target_version": "v0.2.0"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["target_version"] == "v0.2.0"


def test_system_reboot_endpoint_requests_reboot() -> None:
    calls = {"count": 0}

    def fake_reboot() -> None:
        calls["count"] += 1

    app = create_provisioning_app(ProvisioningService(), reboot_action=fake_reboot)
    client = TestClient(app)

    response = client.post("/api/system/reboot")

    assert response.status_code == 200
    assert calls["count"] == 1
    assert "Reboot requested" in response.json()["message"]
