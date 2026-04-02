"""Local captive-portal web server scaffold for device onboarding."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
import uvicorn

from smartblaster.hardware.camera import CameraService
from smartblaster.hardware.ir import IrService
from smartblaster.provisioning.camera_setup import CameraSetupService, ReferenceImageStore
from smartblaster.provisioning.network import NmcliWifiConfigurator
from smartblaster.provisioning.service import ProvisioningService, SetupRequest
from smartblaster.provisioning.state import load_setup_state, software_version
from smartblaster.provisioning.system import request_reboot
from smartblaster.provisioning.update import GitHubAppUpdater
from smartblaster.services.setup_validation import SetupValidator
from smartblaster.services.thermostat_status import ThermostatStatusService
from smartblaster.vision.registry import create_parser_for_model


class SetupPayload(BaseModel):
    device_name: str = Field(default="SmartBlaster", min_length=1)
    wifi_ssid: str = Field(min_length=1)
    wifi_password: str = Field(min_length=8)
    thermostat_profile_id: str
    camera_enabled: bool = False
    daily_on_time: str = Field(default="10:00", pattern=r"^\d{2}:\d{2}$")
    daily_off_time: str = Field(default="15:00", pattern=r"^\d{2}:\d{2}$")
    solar_weekly_schedule: dict[str, dict[str, str]] = Field(default_factory=dict)
    target_temperature_c: float = Field(default=26.0, ge=16.0, le=30.0)
    timezone: str = Field(default="UTC", min_length=1)
    active_days: list[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    fan_mode: str = Field(default="auto")
    swing_mode: str = Field(default="off")
    preset_mode: str = Field(default="none")
    thermostat_temperature_unit: str = Field(default="C")
    inverter_source_enabled: bool = False
    inverter_source_type: str = Field(default="none")
    inverter_surplus_start_w: int = Field(default=0, ge=0)
    inverter_surplus_stop_w: int = Field(default=0, ge=0)
    status_history_file: str = Field(default="data/thermostat_status_history.log")
    status_diagnostic_mode: bool = False
    status_image_dir: str = Field(default="data/status_images")
    reference_image_dir: str = Field(default="data/reference_images")
    reference_capture_on_parse_failure: bool = True
    training_mode_enabled: bool = False
    training_capture_interval_minutes: int = Field(default=60, ge=1)
    validate_capabilities_enabled: bool = False
    reference_offload_enabled: bool = False
    reference_offload_interval_minutes: int = Field(default=15, ge=1)
    reference_offload_batch_size: int = Field(default=25, ge=1)
    config_schema_version: int = Field(default=1, ge=1)


class CameraReferencePayload(BaseModel):
    thermostat_profile_id: str
    phase: str = Field(default="install_camera_setup", min_length=1)
    label: str | None = None
    include_overlay: bool = True
    reference_image_dir: str | None = None


class UpdateApplyPayload(BaseModel):
    target_version: str | None = None


class ValidationRunPayload(BaseModel):
    thermostat_profile_id: str
    camera_enabled: bool = False
    settle_seconds: float = Field(default=3.0, ge=0.0, le=60.0)
    reference_image_dir: str = Field(default="data/reference_images")
    status_history_file: str = Field(default="data/validation_status_history.log")


def _software_version() -> str:
    return software_version()


def _read_portal_doc(doc_path: Path, *, fallback: str) -> str:
    try:
        text = doc_path.read_text(encoding="utf-8")
    except Exception:
        return fallback
    lines = [line.rstrip() for line in text.splitlines()]
    # Keep this concise for captive portal readability.
    return "\n".join(lines[:120])


def create_provisioning_app(
    service: ProvisioningService | None = None,
    camera_setup_service: CameraSetupService | None = None,
    update_service: GitHubAppUpdater | None = None,
    reboot_action: Callable[[], None] | None = None,
) -> FastAPI:
    provisioning = service or ProvisioningService()
    _camera = CameraService()
    _camera.start()  # Keep camera warm between preview requests to avoid per-request startup delay.
    camera_setup = camera_setup_service or CameraSetupService(
        camera=_camera,
        reference_store=ReferenceImageStore(),
        manage_camera_lifecycle=False,
    )
    updater = update_service or GitHubAppUpdater.from_env()
    rebooter = reboot_action or request_reboot
    app = FastAPI(title="SmartBlaster Provisioning", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/thermostats")
    def thermostats() -> list[dict[str, object]]:
        return provisioning.available_thermostats()

    @app.get("/api/device-info")
    def device_info() -> dict[str, object]:
        setup_state = load_setup_state(provisioning.state_file)
        saved_name = setup_state.get("device_name")
        device_name = str(saved_name).strip() if isinstance(saved_name, str) and saved_name.strip() else "SmartBlaster"
        has_camera_setup_values = any(
            key in setup_state
            for key in (
                "camera_enabled",
                "status_image_dir",
                "reference_image_dir",
                "reference_capture_on_parse_failure",
                "training_mode_enabled",
                "training_capture_interval_minutes",
            )
        )
        return {
            "device_name": device_name,
            "software_version": _software_version(),
            "setup_state_version": str(setup_state.get("setup_state_version", "")),
            "config_schema_version": str(setup_state.get("config_schema_version", "")),
            "has_camera_setup_values": has_camera_setup_values,
            "camera_enabled": bool(setup_state.get("camera_enabled", False)),
        }

    @app.get("/api/update/status")
    def update_status() -> dict[str, object]:
        return asdict(updater.status())

    @app.post("/api/update/apply")
    def update_apply(payload: UpdateApplyPayload) -> dict[str, object]:
        result = updater.apply(payload.target_version)
        if not result.ok:
            raise HTTPException(status_code=400, detail=asdict(result))
        return asdict(result)

    @app.post("/api/system/reboot")
    def system_reboot() -> dict[str, str]:
        rebooter()
        return {"message": "Reboot requested."}

    @app.post("/api/validation/run")
    def run_validation(payload: ValidationRunPayload) -> dict[str, object]:
        ir = IrService(tx_gpio=4, rx_gpio=17, dry_run=False)
        status_service: ThermostatStatusService | None = None
        if payload.camera_enabled:
            try:
                parser = create_parser_for_model(payload.thermostat_profile_id)
                status_service = ThermostatStatusService(
                    camera=CameraService(),
                    parser=parser,
                    history_file=Path(payload.status_history_file),
                )
            except Exception as ex:
                raise HTTPException(status_code=503, detail=f"Camera setup failed: {ex}") from ex

        validator = SetupValidator(
            ir=ir,
            status_service=status_service,
            profile_id=payload.thermostat_profile_id,
            settle_seconds=payload.settle_seconds,
        )
        try:
            report = validator.run()
        except Exception as ex:
            raise HTTPException(status_code=500, detail=f"Validation error: {ex}") from ex
        return report.to_dict()

    @app.get("/api/readme")
    def setup_readme() -> dict[str, str]:
        root = Path(__file__).resolve().parents[3]
        readme_text = _read_portal_doc(
            root / "README.md",
            fallback="SmartBlaster setup guide is unavailable on this build.",
        )
        return {"title": "Setup Quick Guide", "text": readme_text}

    @app.get("/api/owners-manual")
    def owners_manual() -> dict[str, str]:
        root = Path(__file__).resolve().parents[3]
        manual_text = _read_portal_doc(
            root / "docs" / "OWNER_MANUAL.md",
            fallback="Owner's manual not found yet. See README for setup guidance.",
        )
        return {"title": "Owner's Manual", "text": manual_text}

    @app.get("/api/setup")
    def get_setup() -> dict[str, object]:
        if not provisioning.state_file.exists():
            raise HTTPException(status_code=404, detail="No saved setup")
        state = load_setup_state(provisioning.state_file)
        internal_keys = {"setup_state_version", "saved_by_software_version", "config_schema_version"}
        return {k: v for k, v in state.items() if k not in internal_keys}

    @app.post("/api/setup")
    def apply_setup(payload: SetupPayload) -> dict[str, object]:
        try:
            result = provisioning.apply_setup(
                SetupRequest(
                    device_name=payload.device_name,
                    wifi_ssid=payload.wifi_ssid,
                    wifi_password=payload.wifi_password,
                    thermostat_profile_id=payload.thermostat_profile_id,
                    camera_enabled=payload.camera_enabled,
                    daily_on_time=payload.daily_on_time,
                    daily_off_time=payload.daily_off_time,
                    solar_weekly_schedule=payload.solar_weekly_schedule,
                    target_temperature_c=payload.target_temperature_c,
                    timezone=payload.timezone,
                    active_days=payload.active_days,
                    fan_mode=payload.fan_mode,
                    swing_mode=payload.swing_mode,
                    preset_mode=payload.preset_mode,
                    thermostat_temperature_unit=payload.thermostat_temperature_unit,
                    inverter_source_enabled=payload.inverter_source_enabled,
                    inverter_source_type=payload.inverter_source_type,
                    inverter_surplus_start_w=payload.inverter_surplus_start_w,
                    inverter_surplus_stop_w=payload.inverter_surplus_stop_w,
                    status_history_file=payload.status_history_file,
                    status_diagnostic_mode=payload.status_diagnostic_mode,
                    status_image_dir=payload.status_image_dir,
                    reference_image_dir=payload.reference_image_dir,
                    reference_capture_on_parse_failure=payload.reference_capture_on_parse_failure,
                    training_mode_enabled=payload.training_mode_enabled,
                    training_capture_interval_minutes=payload.training_capture_interval_minutes,
                    validate_capabilities_enabled=payload.validate_capabilities_enabled,
                    reference_offload_enabled=payload.reference_offload_enabled,
                    reference_offload_interval_minutes=payload.reference_offload_interval_minutes,
                    reference_offload_batch_size=payload.reference_offload_batch_size,
                    config_schema_version=payload.config_schema_version,
                )
            )
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex)) from ex

        if not result.ok:
            raise HTTPException(status_code=400, detail=result.message)

        return asdict(result)

    @app.get("/api/camera/status")
    def camera_status(thermostat_profile_id: str = Query(..., min_length=1)) -> dict[str, object]:
        try:
            status = camera_setup.status(thermostat_profile_id)
        except Exception as ex:
            raise HTTPException(status_code=503, detail=str(ex)) from ex
        return asdict(status)

    @app.get("/api/camera/preview.jpg")
    def camera_preview(
        thermostat_profile_id: str = Query(..., min_length=1),
        overlay: bool = True,
    ) -> Response:
        try:
            content = camera_setup.preview_frame(thermostat_profile_id, overlay=overlay)
        except Exception as ex:
            raise HTTPException(status_code=503, detail=str(ex)) from ex
        return Response(content=content, media_type="image/jpeg")

    @app.post("/api/camera/reference-capture")
    def capture_reference(payload: CameraReferencePayload) -> dict[str, object]:
        try:
            result = camera_setup.capture_reference(
                profile_id=payload.thermostat_profile_id,
                phase=payload.phase,
                label=payload.label,
                include_overlay=payload.include_overlay,
                reference_image_dir=Path(payload.reference_image_dir) if payload.reference_image_dir else None,
            )
        except Exception as ex:
            raise HTTPException(status_code=503, detail=str(ex)) from ex
        return result

    @app.get("/", response_class=HTMLResponse)
    def setup_page() -> str:
        return """
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>SmartBlaster Setup</title>
    <style>
      :root {
        --bg: #f3efe3;
        --panel: #fffaf0;
        --ink: #1f2430;
        --accent: #1f5c4a;
        --accent-soft: #d8eadb;
        --warn: #8f4c18;
        --bad: #9c2f2f;
        --border: #d7ccb6;
      }
      body { font-family: Georgia, 'Times New Roman', serif; max-width: 780px; margin: 1.5rem auto; padding: 0 1rem 2rem; background: linear-gradient(180deg, #efe6d2 0%, var(--bg) 100%); color: var(--ink); }
      h1, h2 { margin-bottom: 0.35rem; }
      .panel { background: rgba(255,250,240,0.92); border: 1px solid var(--border); border-radius: 16px; padding: 1rem 1rem 1.2rem; margin-top: 1rem; box-shadow: 0 10px 24px rgba(80, 60, 20, 0.08); }
      .setup-title {
        font-size: 1.6rem;
        font-weight: 900;
        color: #174a3b;
        text-align: center;
        margin: 0.15rem 0 0.85rem 0;
        letter-spacing: 0.01em;
      }
      .subgroup { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 0.8rem; margin-top: 0.85rem; }
      .subgroup-title { margin: 0 0 0.15rem 0; font-size: 1.02rem; }
      .top-group > .subgroup-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: var(--accent);
        text-align: center;
        margin-bottom: 0.35rem;
        letter-spacing: 0.01em;
      }
      .top-group > .hint {
        margin: 0 auto 0.85rem auto;
        max-width: 42rem;
        text-align: center;
        color: #4d4a42;
        padding-bottom: 0.55rem;
        border-bottom: 1px solid var(--border);
      }
      h4.subgroup-title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--ink);
        text-align: left;
      }
      .subgroup .hint { margin-top: 0; }
      #perDayScheduleDetails > summary { cursor: pointer; color: var(--accent); font-weight: 700; padding: 0.3rem 0; list-style: none; user-select: none; }
      .schedule-wrap { display: flex; flex-direction: column; }
      #perDayScheduleDetails { order: 2; margin-top: 0.75rem; }
      .schedule-main { order: 1; }
      #mondayLabel .monday-label-monday { display: none; }
      #perDayScheduleDetails[open] ~ .schedule-main #mondayLabel .monday-label-daily { display: none; }
      #perDayScheduleDetails[open] ~ .schedule-main #mondayLabel .monday-label-monday { display: inline; }
      .grid { display: grid; grid-template-columns: 1fr; gap: 1rem; }
      label { display:block; margin-top: 0.8rem; font-weight: 700; }
      input:not([type="checkbox"]), select, button { width: 100%; padding: 0.7rem; margin-top: 0.25rem; border-radius: 10px; border: 1px solid var(--border); box-sizing: border-box; }
      label.checkbox-row { display: flex; align-items: center; justify-content: flex-start; text-align: left; gap: 0.5rem; }
      input[type="checkbox"] { width: auto; display: inline-block; flex: 0 0 auto; padding: 0; margin: 0; border: none; accent-color: var(--accent); }
      button { background: var(--accent); color: white; border: none; font-weight: 700; cursor: pointer; }
      button.secondary { background: #d8c7a0; color: #2e2417; }
      .hint { color: #5c5a52; font-size: 0.95rem; }
      .ok { color: #0a7f2e; }
      .err { color: #b00020; }
      .preview { width: 100%; border-radius: 14px; border: 1px solid var(--border); background: #d7d2c4; aspect-ratio: 16 / 9; object-fit: cover; }
      .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.6rem; margin-top: 0.75rem; }
      .status-chip { background: white; border: 1px solid var(--border); border-radius: 12px; padding: 0.65rem; }
      .camera-tools { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 0.75rem; }
      .schedule-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; align-items: center; margin-top: 0.5rem; }
      .schedule-grid div { font-size: 0.92rem; }
      .meta { display: flex; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap; }
      .camera-cta { border: 2px solid var(--accent); background: linear-gradient(180deg, #f3fbf7 0%, #eef8f2 100%); }
      .camera-cta h2 { color: #174a3b; margin-top: 0; }
      .btn-link { display: block; background: var(--accent); color: white; font-weight: 700; cursor: pointer; width: 100%; padding: 0.7rem; margin-top: 0.25rem; border-radius: 10px; text-align: center; text-decoration: none; box-sizing: border-box; }
      .camera-cta .btn-link { font-size: 1.05rem; font-weight: 800; padding: 0.85rem 0.9rem; }
      #cameraLiveModal { display: none; position: fixed; top: 0; right: 0; bottom: 0; left: 0; background: rgba(0,0,0,0.82); z-index: 1000; align-items: center; justify-content: center; padding: 1rem; box-sizing: border-box; }
      #cameraLiveModal:target { display: flex; }
      .modal-inner { background: #1a1a1a; border-radius: 16px; padding: 1rem; max-width: 900px; width: 100%; box-shadow: 0 24px 64px rgba(0,0,0,0.7); }
      .modal-inner h2 { color: #f3efe3; margin: 0 0 0.6rem 0; font-size: 1.2rem; display: flex; justify-content: space-between; align-items: center; }
      .modal-inner h2 button { width: auto; padding: 0.3rem 0.9rem; font-size: 0.95rem; background: #444; border-radius: 8px; }
      #modalPreview { width: 100%; border-radius: 10px; aspect-ratio: 16/9; object-fit: cover; background: #333; display: block; }
      .modal-hint { color: #b0a990; font-size: 0.9rem; margin-top: 0.5rem; text-align: center; }
      .modal-tools { display: flex; gap: 0.6rem; justify-content: center; margin-top: 0.6rem; }
      .modal-tools button { width: auto; padding: 0.45rem 0.9rem; font-size: 0.9rem; border-radius: 8px; background: #2f6a58; }
      .modal-diagnostics {
        margin-top: 0.6rem;
        background: #111;
        border: 1px solid #3f3f3f;
        border-radius: 8px;
        padding: 0.55rem 0.65rem;
        color: #d8d8d8;
        font-size: 0.85rem;
        line-height: 1.35;
        white-space: pre-wrap;
      }
      pre.doc { white-space: pre-wrap; background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 0.75rem; max-height: 260px; overflow: auto; }
      @media (max-width: 640px) {
        .camera-tools { grid-template-columns: 1fr; }
        .schedule-grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <h1>SmartBlaster Setup</h1>
    <p class=\"hint\">Connect SmartBlaster to home Wi-Fi, align the camera, and save a reference capture before finishing setup.</p>

    <section class="panel">
      <div class="meta">
        <div><strong>Device:</strong> <span id="deviceNameDisplay">SmartBlaster</span></div>
        <div><strong>Software Version:</strong> <span id="softwareVersionDisplay">loading...</span></div>
      </div>
    </section>
    <section class="panel camera-cta">
      <h2>Camera Setup</h2>
      <p id="cameraSetupCtaHint" class="hint">Run camera alignment and capture a reference image before finishing setup.</p>
      <a id="runCameraSetupNow" href="#cameraLiveModal" class="btn-link">Run Camera Setup Now</a>
    </section>

    <div id="cameraLiveModal" role="dialog" aria-modal="true" aria-label="Camera live view">
      <div class="modal-inner">
        <h2>Camera Live View <button id="closeLiveView" type="button" onclick="closeCameraLiveView()">Done</button></h2>
        <img id="modalPreview" alt="Live camera view" />
        <p id="modalPreviewMsg" class="modal-hint" style="color:#f08080;"></p>
        <div class="modal-tools">
          <button id="checkReadabilityBtn" type="button">Check Readability (Advanced)</button>
          <button id="copyDiagnosticsBtn" type="button">Copy Diagnostics</button>
        </div>
        <div id="modalDiagnostics" class="modal-diagnostics" style="display:none;"></div>
        <p id="modalCopyStatus" class="modal-hint" style="display:none;"></p>
        <p class="modal-hint">Position the device and adjust the camera zoom and focus. Press Done when the image looks good.</p>
      </div>
    </div>
    <section class=\"panel\">
      <h2 class="setup-title">Setup</h2>

      <div class="subgroup top-group">
        <h3 class="subgroup-title">Device And Thermostat</h3>
        <p class="hint">Name this SmartBlaster, connect it to home Wi-Fi, and choose the thermostat model it will control.</p>

        <label>Device Name</label>
        <input id="deviceName" value="SmartBlaster" />

        <label>Wi-Fi SSID</label>
        <input id=\"ssid\" placeholder=\"MyHomeWiFi\" />

        <label>Wi-Fi Password</label>
        <input id=\"password\" type=\"password\" />

        <label>Thermostat Model</label>
        <select id=\"profile\">
          <option value="midea_kjr_12b_dp_t" selected>Midea</option>
        </select>
        <p class="hint">Only the current Midea launch profile is supported right now. Additional thermostat models can be added later without changing the setup flow.</p>
      </div>

      <div class="subgroup top-group">
        <h3 class="subgroup-title">Schedule</h3>
        <p class="hint">Define when to turn cooling ON (solar surplus) and OFF (solar deficit).</p>

        <div class="schedule-wrap">
          <details id="perDayScheduleDetails">
            <summary>
              &#9654; Allow per-weekday times
            </summary>
            <div class="schedule-grid" style="margin-top:0.5rem;">
              <div>Tuesday</div><input id="sched_tue_on" value="10:00" /><input id="sched_tue_off" value="15:00" />
              <div>Wednesday</div><input id="sched_wed_on" value="10:00" /><input id="sched_wed_off" value="15:00" />
              <div>Thursday</div><input id="sched_thu_on" value="10:00" /><input id="sched_thu_off" value="15:00" />
              <div>Friday</div><input id="sched_fri_on" value="10:00" /><input id="sched_fri_off" value="15:00" />
              <div>Saturday</div><input id="sched_sat_on" value="10:00" /><input id="sched_sat_off" value="15:00" />
              <div>Sunday</div><input id="sched_sun_on" value="10:00" /><input id="sched_sun_off" value="15:00" />
            </div>
          </details>

          <div class="schedule-grid schedule-main" style="margin-top:0.5rem;">
            <div><strong>Day</strong></div>
            <div><strong>ON</strong></div>
            <div><strong>OFF</strong></div>
            <div id="mondayLabel"><span class="monday-label-daily">Daily</span><span class="monday-label-monday">Monday</span></div>
            <input id="sched_mon_on" value="10:00" />
            <input id="sched_mon_off" value="15:00" />
          </div>
        </div>

        <label>Timezone</label>
        <input id="timezone" value="UTC" />

        <label>Active Days (comma-separated, mon..sun)</label>
        <input id="activeDays" value="mon,tue,wed,thu,fri,sat,sun" />
      </div>

      <div class="subgroup top-group">
        <h3 class="subgroup-title">Cooling Target And Control</h3>
        <p class="hint">Set target temperature and default control profile values.</p>

        <label>Target Temperature (°C)</label>
        <input id="targetTemp" type="number" min="16" max="30" step="0.5" value="26" />

        <label>Thermostat Temperature Unit</label>
        <select id="tempUnit">
          <option value="C" selected>Celsius (°C)</option>
          <option value="F">Fahrenheit (°F)</option>
        </select>

        <label>Fan Mode</label>
        <select id="fanMode">
          <option value="auto" selected>Auto</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="silent">Silent</option>
          <option value="turbo">Turbo</option>
        </select>

        <label>Swing</label>
        <select id="swingMode">
          <option value="off" selected>Off</option>
          <option value="vertical">Vertical</option>
          <option value="both">Both</option>
        </select>

        <label>Preset</label>
        <select id="presetMode">
          <option value="none" selected>None</option>
          <option value="sleep">Sleep</option>
          <option value="eco">Eco</option>
          <option value="boost">Boost</option>
        </select>
      </div>

      <div class="subgroup top-group">
        <h3 class="subgroup-title">Solar System Integration</h3>
        <p class="hint">Future inverter integration controls for event-driven ON/OFF.</p>

        <label class="checkbox-row"><input id="inverterEnabled" type="checkbox" /> Enable inverter event source</label>

        <label>Inverter Source Type</label>
        <input id="inverterSourceType" value="none" />

        <label>Inverter Surplus Start (W)</label>
        <input id="inverterStartW" type="number" min="0" step="1" value="0" />

        <label>Inverter Surplus Stop (W)</label>
        <input id="inverterStopW" type="number" min="0" step="1" value="0" />
      </div>

      <div class="subgroup top-group">
        <h3 class="subgroup-title">Power User Features</h3>
        <p class="hint">Advanced controls for troubleshooting, validation, and data collection. Most installs can leave these at defaults.</p>
        <label class="checkbox-row"><input id="disableCameraVerification" type="checkbox" /> Disable camera verification (advanced)</label>

        <div class="subgroup">
          <h4 class="subgroup-title">Status Diagnostics</h4>
          <p class="hint">Capture and store status snapshots for troubleshooting parser behavior.</p>

          <label>Status History File</label>
          <input id="statusHistoryFile" value="data/thermostat_status_history.log" />

          <label class="checkbox-row"><input id="statusDiagnosticMode" type="checkbox" /> Diagnostic mode (save each status image)</label>

          <label>Status Image Directory</label>
          <input id="statusImageDir" value="data/status_images" />
        </div>

        <div class="subgroup">
          <h3 class="subgroup-title">Reference Images And Offload</h3>
          <p class="hint">Capture training/reference images and control optional future offload behavior.</p>

          <label>Reference Image Directory</label>
          <input id="referenceImageDir" value="data/reference_images" />

          <label class="checkbox-row"><input id="referenceCaptureOnFailure" type="checkbox" checked /> Save failed parses as reference captures</label>

          <label class="checkbox-row"><input id="trainingModeEnabled" type="checkbox" /> Training mode (periodic reference captures)</label>

          <label>Training Capture Interval (minutes)</label>
          <input id="trainingCaptureIntervalMinutes" type="number" min="1" step="1" value="60" />

          <label class="checkbox-row"><input id="referenceOffloadEnabled" type="checkbox" /> Future: enable periodic reference offload worker</label>

          <label>Offload Interval (minutes)</label>
          <input id="referenceOffloadIntervalMinutes" type="number" min="1" step="1" value="15" />

          <label>Offload Batch Size</label>
          <input id="referenceOffloadBatchSize" type="number" min="1" step="1" value="25" />
        </div>

        <div id="validationPanel" style="display:none; margin-top:0.8rem;">
          <h4 class="subgroup-title">Capability Validation</h4>
          <p class="hint">Manually cycle thermostat settings and confirm the display responds correctly. This runs immediately each time you click it and powers the unit off at the end.</p>

          <label>Settle Time (seconds)</label>
          <input id="validationSettleSeconds" type="number" min="0" max="30" step="1" value="3" />

          <button id="runValidation" type="button">Run Capability Validation</button>
          <p id="validationStatus" class="hint"></p>

          <div id="validationResults" style="display:none">
            <p id="validationOverall" class="hint"></p>
            <table style=\"width:100%; border-collapse:collapse; margin-top:0.5rem; font-size:0.9rem;\">
              <thead>
                <tr style=\"border-bottom:2px solid var(--border);\">
                  <th style=\"text-align:left;padding:4px 8px\">Command</th>
                  <th style=\"text-align:left;padding:4px 8px\">Outcome</th>
                  <th style=\"text-align:left;padding:4px 8px\">Confidence</th>
                  <th style=\"text-align:left;padding:4px 8px\">Parsed Mode</th>
                  <th style=\"text-align:left;padding:4px 8px\">Error</th>
                </tr>
              </thead>
              <tbody id="validationTableBody"></tbody>
            </table>
          </div>
        </div>
      </div>

      <button id=\"save\">Save Setup</button>
      <p id=\"result\" class=\"hint\"></p>
    </section>

    <section class=\"panel\">
      <h2>App Update (GitHub)</h2>
      <p id=\"updateStatus\" class=\"hint\">Checking update status...</p>
      <label>Optional target tag (example: v0.2.0)</label>
      <input id=\"updateTargetVersion\" placeholder=\"leave blank for latest release\" />
      <div class=\"camera-tools\">
        <button id=\"refreshUpdateStatus\" type=\"button\" class=\"secondary\">Refresh Update Status</button>
        <button id=\"applyUpdate\" type=\"button\">Apply App Update</button>
      </div>
      <p id=\"updateResult\" class=\"hint\"></p>
    </section>

    <section class=\"panel\">
      <h2>System</h2>
      <p class=\"hint\">If network has recovered, reboot back into normal runtime.</p>
      <button id=\"rebootNow\" type=\"button\" class=\"secondary\">Reboot Device</button>
      <p id=\"rebootResult\" class=\"hint\"></p>
    </section>

    <section class=\"panel\" id=\"cameraPanel\" style=\"display:none\">
      <h2>Camera Setup</h2>
      <p class=\"hint\">Use the live preview to point the camera at the thermostat, zoom in, focus, and save an install-time reference image.</p>

      <img id=\"cameraPreview\" class=\"preview\" alt=\"Camera preview\" />

      <div class=\"status-grid\">
        <div class=\"status-chip\"><strong>Display</strong><div id=\"statusDisplay\">waiting</div></div>
        <div class=\"status-chip\"><strong>Focus</strong><div id=\"statusFocus\">waiting</div></div>
        <div class=\"status-chip\"><strong>Glare</strong><div id=\"statusGlare\">waiting</div></div>
        <div class=\"status-chip\"><strong>Parser Confidence</strong><div id=\"statusConfidence\">waiting</div></div>
      </div>

      <label>Reference Capture Label</label>
      <input id=\"referenceLabel\" value=\"installer-approved\" />

      <div class=\"camera-tools\">
        <button id=\"refreshPreview\" type=\"button\" class=\"secondary\">Refresh Preview</button>
        <button id=\"saveReference\" type=\"button\">Save Reference Image</button>
      </div>

      <p id=\"cameraAdvice\" class=\"hint\">Enable camera verification to begin live alignment.</p>
      <p id=\"cameraReferenceResult\" class=\"hint\"></p>
    </section>

    <section class=\"panel\">
      <h2>Setup Quick Guide</h2>
      <pre id=\"readmeText\" class=\"doc\">Loading setup guidance...</pre>
    </section>

    <section class=\"panel\">
      <h2>Owner's Manual</h2>
      <pre id=\"ownersManualText\" class=\"doc\">Loading owner's manual...</pre>
    </section>

    <script>
      let previewTimer = null;
      let hasCameraSetupValues = false;
      const WEEK_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

      function updateCameraSetupCallToAction() {
        const button = document.getElementById('runCameraSetupNow');
        const hint = document.getElementById('cameraSetupCtaHint');
        if (!button || !hint) {
          return;
        }
        const rerun = hasCameraSetupValues;
        button.textContent = rerun ? 'Rerun Camera Setup' : 'Run Camera Setup Now';
        hint.textContent = rerun
          ? 'Camera setup values were previously saved. Run setup again after moving the device or thermostat.'
          : 'Run camera alignment and capture a reference image before finishing setup.';
      }

      async function loadDeviceInfo() {
        try {
          const res = await fetch('/api/device-info');
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || 'Unable to load device info');
          }

          const deviceName = data.device_name || 'SmartBlaster';
          document.getElementById('deviceName').value = deviceName;
          document.getElementById('deviceNameDisplay').textContent = deviceName;
          document.getElementById('softwareVersionDisplay').textContent = data.software_version || 'unknown';
          hasCameraSetupValues = Boolean(data.has_camera_setup_values);
          updateCameraSetupCallToAction();
        } catch (_err) {
          document.getElementById('softwareVersionDisplay').textContent = 'unknown';
          updateCameraSetupCallToAction();
        }
      }

      async function loadDoc(endpoint, targetId, fallbackText) {
        const target = document.getElementById(targetId);
        try {
          const res = await fetch(endpoint);
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || `Unable to load ${targetId}`);
          }
          target.textContent = data.text || fallbackText;
        } catch (_err) {
          target.textContent = fallbackText;
        }
      }

      async function loadUpdateStatus() {
        const updateStatus = document.getElementById('updateStatus');
        const updateResult = document.getElementById('updateResult');
        updateResult.textContent = '';
        try {
          const res = await fetch('/api/update/status');
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || 'Unable to load update status');
          }

          if (!data.enabled) {
            updateStatus.textContent = 'Updates disabled. Set SMARTBLASTER_UPDATE_REPO to enable GitHub updates.';
            updateStatus.className = 'hint';
            return;
          }

          const latest = data.latest_version || 'unknown';
          const current = data.current_version || 'unknown';
          const availability = data.update_available ? 'update available' : 'up to date';
          updateStatus.textContent = `Repo ${data.repo}: current=${current}, latest=${latest} (${availability})`;
          updateStatus.className = data.update_available ? 'hint err' : 'hint ok';
        } catch (err) {
          updateStatus.textContent = err.message || 'Unable to load update status';
          updateStatus.className = 'hint err';
        }
      }

      async function applyUpdate() {
        const updateResult = document.getElementById('updateResult');
        updateResult.className = 'hint';
        updateResult.textContent = 'Applying update...';

        const targetVersion = document.getElementById('updateTargetVersion').value.trim();
        const res = await fetch('/api/update/apply', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            target_version: targetVersion || null,
          }),
        });

        const data = await res.json();
        if (!res.ok) {
          const details = data.detail || {};
          updateResult.className = 'hint err';
          updateResult.textContent = details.message || 'Update failed';
          return;
        }

        updateResult.className = 'hint ok';
        updateResult.textContent = `${data.message} Target=${data.target_version || 'unknown'}`;
        loadUpdateStatus();
      }

      async function rebootDevice() {
        const rebootResult = document.getElementById('rebootResult');
        rebootResult.className = 'hint';
        rebootResult.textContent = 'Requesting reboot...';

        const res = await fetch('/api/system/reboot', {
          method: 'POST',
        });

        const data = await res.json();
        if (!res.ok) {
          rebootResult.className = 'hint err';
          rebootResult.textContent = data.detail || 'Reboot request failed';
          return;
        }

        rebootResult.className = 'hint ok';
        rebootResult.textContent = data.message || 'Reboot requested.';
      }

      async function loadProfiles() {
        const sel = document.getElementById('profile');
        if (!sel.value) {
          sel.innerHTML = '<option value="midea_kjr_12b_dp_t" selected>Midea</option>';
        }
        updateCameraPanel();
        await loadSavedSetup();
      }

      async function loadSavedSetup() {
        try {
          const res = await fetch('/api/setup');
          if (!res.ok) return;
          const s = await res.json();

          // Plain text / number inputs
          const textFields = {
            ssid: s.wifi_ssid,
            timezone: s.timezone,
            targetTemp: s.target_temperature_c,
            activeDays: Array.isArray(s.active_days) ? s.active_days.join(',') : s.active_days,
            inverterSourceType: s.inverter_source_type,
            inverterStartW: s.inverter_surplus_start_w,
            inverterStopW: s.inverter_surplus_stop_w,
            statusHistoryFile: s.status_history_file,
            statusImageDir: s.status_image_dir,
            referenceImageDir: s.reference_image_dir,
            trainingCaptureIntervalMinutes: s.training_capture_interval_minutes,
            referenceOffloadIntervalMinutes: s.reference_offload_interval_minutes,
            referenceOffloadBatchSize: s.reference_offload_batch_size,
          };
          for (const [id, val] of Object.entries(textFields)) {
            const el = document.getElementById(id);
            if (el && val != null) el.value = val;
          }

          // Select elements
          const selectFields = {
            profile: s.thermostat_profile_id,
            tempUnit: s.thermostat_temperature_unit,
            fanMode: s.fan_mode,
            swingMode: s.swing_mode,
            presetMode: s.preset_mode,
          };
          for (const [id, val] of Object.entries(selectFields)) {
            const el = document.getElementById(id);
            if (el && val != null) el.value = val;
          }

          // Checkboxes
          const checkboxes = [
            ['inverterEnabled', s.inverter_source_enabled],
            ['statusDiagnosticMode', s.status_diagnostic_mode],
            ['referenceCaptureOnFailure', s.reference_capture_on_parse_failure],
            ['trainingModeEnabled', s.training_mode_enabled],
            ['referenceOffloadEnabled', s.reference_offload_enabled],
          ];
          for (const [id, val] of checkboxes) {
            const el = document.getElementById(id);
            if (el && val != null) el.checked = Boolean(val);
          }
          // camera_enabled is stored inverted on the disableCameraVerification checkbox
          if (s.camera_enabled != null) {
            document.getElementById('disableCameraVerification').checked = !s.camera_enabled;
          }

          // UI convenience mode: the simple schedule uses the Monday row as the shared
          // value the user edits before it is copied into every weekday on save.
          if (s.daily_on_time) document.getElementById('sched_mon_on').value = s.daily_on_time;
          if (s.daily_off_time) document.getElementById('sched_mon_off').value = s.daily_off_time;

          // Canonical persisted form: per-weekday schedule entries.
          // Tuesday-Sunday are loaded from solar_weekly_schedule; Monday is preloaded from
          // the legacy/simple daily fields so old saved state and the simple UI both work.
          const sched = s.solar_weekly_schedule || {};
          for (const day of ['tue', 'wed', 'thu', 'fri', 'sat', 'sun']) {
            const entry = sched[day];
            if (entry) {
              if (entry.on_time) document.getElementById(`sched_${day}_on`).value = entry.on_time;
              if (entry.off_time) document.getElementById(`sched_${day}_off`).value = entry.off_time;
            }
          }

          // device_name is also populated by loadDeviceInfo; set it here in case order differs
          if (s.device_name) {
            document.getElementById('deviceName').value = s.device_name;
            document.getElementById('deviceNameDisplay').textContent = s.device_name;
          }

          updateCameraPanel();
        } catch (_err) {
          // silently ignore — form stays at defaults if saved state unavailable
        }
      }

      function selectedProfileId() {
        return document.getElementById('profile').value;
      }

      function cameraVerificationEnabled() {
        return !document.getElementById('disableCameraVerification').checked;
      }

      function propagateMonToOtherDays() {
        // Simple-mode helper: copy Monday's values into every other weekday.
        // This keeps the save payload in the same per-day shape used by advanced mode.
        const on = document.getElementById('sched_mon_on').value || '10:00';
        const off = document.getElementById('sched_mon_off').value || '15:00';
        for (const day of ['tue', 'wed', 'thu', 'fri', 'sat', 'sun']) {
          document.getElementById(`sched_${day}_on`).value = on;
          document.getElementById(`sched_${day}_off`).value = off;
        }
      }

      function buildWeeklySchedulePayload() {
        // The backend always receives a full per-weekday schedule map, even when the user
        // interacted only with the simple "same every day" controls.
        const schedule = {};
        for (const day of WEEK_DAYS) {
          schedule[day] = {
            on_time: (document.getElementById(`sched_${day}_on`).value || '').trim(),
            off_time: (document.getElementById(`sched_${day}_off`).value || '').trim(),
          };
        }
        return schedule;
      }

      function updateCameraPanel() {
        const enabled = cameraVerificationEnabled();
        document.getElementById('cameraPanel').style.display = enabled ? 'block' : 'none';
        document.getElementById('validationPanel').style.display = enabled ? 'block' : 'none';
        if (!enabled) {
          if (previewTimer) {
            clearInterval(previewTimer);
            previewTimer = null;
          }
          return;
        }
        refreshCameraSetup();
        if (!previewTimer) {
          previewTimer = setInterval(refreshCameraSetup, 2000);
        }
      }

      async function refreshCameraSetup() {
        const profileId = selectedProfileId();
        if (!profileId || !cameraVerificationEnabled()) {
          return;
        }

        const preview = document.getElementById('cameraPreview');
        preview.src = `/api/camera/preview.jpg?thermostat_profile_id=${encodeURIComponent(profileId)}&overlay=true&t=${Date.now()}`;

        const advice = document.getElementById('cameraAdvice');
        try {
          const res = await fetch(`/api/camera/status?thermostat_profile_id=${encodeURIComponent(profileId)}`);
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || 'camera preview unavailable');
          }

          document.getElementById('statusDisplay').textContent = data.display_readable ? 'readable' : 'not readable yet';
          document.getElementById('statusFocus').textContent = `${data.focus_good ? 'good' : 'adjust'} (${data.focus_score})`;
          document.getElementById('statusGlare').textContent = `${data.glare_low ? 'low' : 'high'} (${data.glare_ratio})`;
          document.getElementById('statusConfidence').textContent = String(data.parser_confidence);
          advice.textContent = data.recommended_action;
          advice.className = data.display_readable ? 'hint ok' : 'hint err';
        } catch (err) {
          advice.textContent = err.message || 'camera preview unavailable';
          advice.className = 'hint err';
        }
      }

      async function runValidation() {
        const profileId = selectedProfileId();
        const settleSeconds = parseFloat(document.getElementById('validationSettleSeconds').value || '3');
        const status = document.getElementById('validationStatus');
        const resultsDiv = document.getElementById('validationResults');
        const overall = document.getElementById('validationOverall');
        const tbody = document.getElementById('validationTableBody');

        status.className = 'hint';
        status.textContent = 'Running validation\u2026 (this may take up to a minute)';
        resultsDiv.style.display = 'none';

        const res = await fetch('/api/validation/run', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            thermostat_profile_id: profileId,
            camera_enabled: cameraVerificationEnabled(),
            settle_seconds: isNaN(settleSeconds) ? 3 : settleSeconds,
          }),
        });

        const data = await res.json();
        if (!res.ok) {
          status.className = 'hint err';
          status.textContent = data.detail || 'Validation request failed';
          return;
        }

        status.textContent = '';
        resultsDiv.style.display = 'block';

        if (data.skipped) {
          overall.className = 'hint';
          overall.textContent = 'Validation skipped: camera is not enabled.';
        } else {
          overall.className = data.overall_pass ? 'hint ok' : 'hint err';
          overall.textContent = data.overall_pass ? 'All steps passed.' : 'One or more steps failed.';
        }

        tbody.innerHTML = '';
        for (const step of data.steps) {
          const tr = document.createElement('tr');
          tr.style.borderBottom = '1px solid var(--border)';
          const outcomeColor = step.outcome === 'pass' ? '#0a7f2e' : step.outcome === 'skip' ? '#5c5a52' : '#b00020';
          tr.innerHTML = `
            <td style="padding:4px 8px">${step.command_name}</td>
            <td style="padding:4px 8px;color:${outcomeColor};font-weight:bold">${step.outcome}</td>
            <td style="padding:4px 8px">${step.confidence != null ? step.confidence : '\u2014'}</td>
            <td style="padding:4px 8px">${step.parsed_mode || '\u2014'}</td>
            <td style="padding:4px 8px;color:#b00020;font-size:0.85rem">${step.error_message || ''}</td>
          `;
          tbody.appendChild(tr);
        }
      }

      async function saveReferenceImage() {
        const profileId = selectedProfileId();
        const result = document.getElementById('cameraReferenceResult');
        result.className = 'hint';
        result.textContent = 'Saving reference image...';

        const res = await fetch('/api/camera/reference-capture', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            thermostat_profile_id: profileId,
            phase: 'install_camera_setup',
            label: document.getElementById('referenceLabel').value,
            include_overlay: true,
            reference_image_dir: document.getElementById('referenceImageDir').value,
          }),
        });

        const data = await res.json();
        if (!res.ok) {
          result.className = 'err';
          result.textContent = data.detail || 'Reference capture failed';
          return;
        }

        result.className = 'ok';
        result.textContent = `Saved reference image: ${data.raw_image}`;
      }

      async function saveSetup() {
        if (!document.getElementById('perDayScheduleDetails').open) {
          // If advanced mode is closed, treat the Monday row as the user's single
          // schedule choice and expand it into explicit weekday entries before save.
          propagateMonToOtherDays();
        }
        const activeDays = WEEK_DAYS;

        const payload = {
          device_name: document.getElementById('deviceName').value,
          wifi_ssid: document.getElementById('ssid').value,
          wifi_password: document.getElementById('password').value,
          thermostat_profile_id: document.getElementById('profile').value,
          camera_enabled: cameraVerificationEnabled(),
          daily_on_time: document.getElementById('sched_mon_on').value,
          daily_off_time: document.getElementById('sched_mon_off').value,
          solar_weekly_schedule: buildWeeklySchedulePayload(),
          target_temperature_c: parseFloat(document.getElementById('targetTemp').value),
          thermostat_temperature_unit: document.getElementById('tempUnit').value,
          timezone: document.getElementById('timezone').value,
          active_days: activeDays,
          fan_mode: document.getElementById('fanMode').value,
          swing_mode: document.getElementById('swingMode').value,
          preset_mode: document.getElementById('presetMode').value,
          inverter_source_enabled: document.getElementById('inverterEnabled').checked,
          inverter_source_type: document.getElementById('inverterSourceType').value,
          inverter_surplus_start_w: parseInt(document.getElementById('inverterStartW').value || '0', 10),
          inverter_surplus_stop_w: parseInt(document.getElementById('inverterStopW').value || '0', 10),
          status_history_file: document.getElementById('statusHistoryFile').value,
          status_diagnostic_mode: document.getElementById('statusDiagnosticMode').checked,
          status_image_dir: document.getElementById('statusImageDir').value,
          reference_image_dir: document.getElementById('referenceImageDir').value,
          reference_capture_on_parse_failure: document.getElementById('referenceCaptureOnFailure').checked,
          training_mode_enabled: document.getElementById('trainingModeEnabled').checked,
          training_capture_interval_minutes: parseInt(document.getElementById('trainingCaptureIntervalMinutes').value || '60', 10),
          validate_capabilities_enabled: false,
          reference_offload_enabled: document.getElementById('referenceOffloadEnabled').checked,
          reference_offload_interval_minutes: parseInt(document.getElementById('referenceOffloadIntervalMinutes').value || '15', 10),
          reference_offload_batch_size: parseInt(document.getElementById('referenceOffloadBatchSize').value || '25', 10),
          config_schema_version: 1,
        };

        const result = document.getElementById('result');
        result.className = 'hint';
        result.textContent = 'Saving...';

        const res = await fetch('/api/setup', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const data = await res.json();
          result.className = 'err';
          result.textContent = data.detail || 'Setup failed';
          return;
        }

        const data = await res.json();
        result.className = 'ok';
        result.textContent = data.message;
        hasCameraSetupValues = true;
        updateCameraSetupCallToAction();
      }

      let liveViewTimer = null;

      function refreshLiveView() {
        const profileId = (selectedProfileId() || 'midea_kjr_12b_dp_t');
        const img = document.getElementById('modalPreview');
        const url = `/api/camera/preview.jpg?thermostat_profile_id=${encodeURIComponent(profileId)}&overlay=false&t=${Date.now()}`;
        img.onerror = () => {
          img.onerror = null;
          img.removeAttribute('src');
          img.alt = 'Camera not available — check that the camera is connected.';
          document.getElementById('modalPreviewMsg').textContent = 'Camera not available. Check that the camera is connected to the device.';
        };
        img.src = url;
      }

      function openCameraLiveView() {
        window.location.hash = 'cameraLiveModal';
      }

      function closeCameraLiveView() {
        window.location.hash = '';
      }

      async function runReadabilityCheck() {
        const profileId = (selectedProfileId() || 'midea_kjr_12b_dp_t');
        const output = document.getElementById('modalDiagnostics');
        const button = document.getElementById('checkReadabilityBtn');
        const copyStatus = document.getElementById('modalCopyStatus');
        output.style.display = 'block';
        output.textContent = 'Running readability check...';
        copyStatus.style.display = 'none';
        copyStatus.textContent = '';
        button.disabled = true;
        button.textContent = 'Checking...';

        try {
          const res = await fetch(`/api/camera/status?thermostat_profile_id=${encodeURIComponent(profileId)}`);
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || 'Unable to evaluate readability');
          }

          const parsed = data.parsed_summary || {};
          const lines = [
            `Readable: ${data.display_readable ? 'yes' : 'no'}`,
            `Focus score: ${data.focus_score}`,
            `Glare ratio: ${data.glare_ratio}`,
            `Parser confidence: ${data.parser_confidence}`,
            `Mode: ${parsed.mode ?? 'n/a'}`,
            `Set temperature: ${parsed.set_temperature ?? 'n/a'}`,
            `Fan speed: ${parsed.fan_speed ?? 'n/a'}`,
          ];
          output.textContent = lines.join('\\n');
        } catch (err) {
          output.textContent = `Readability check failed: ${err.message || 'Unknown error'}`;
        } finally {
          button.disabled = false;
          button.textContent = 'Check Readability (Advanced)';
        }
      }

      async function copyDiagnosticsToClipboard() {
        const output = document.getElementById('modalDiagnostics');
        const copyStatus = document.getElementById('modalCopyStatus');
        const text = (output.textContent || '').trim();
        copyStatus.style.display = 'block';
        if (!text) {
          copyStatus.textContent = 'Nothing to copy yet. Run readability check first.';
          return;
        }

        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
          } else {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
          }
          copyStatus.textContent = 'Diagnostics copied to clipboard.';
        } catch (_err) {
          copyStatus.textContent = 'Copy failed. Please select and copy manually.';
        }
      }

      window.addEventListener('hashchange', function() {
        if (window.location.hash === '#cameraLiveModal') {
          document.getElementById('modalPreviewMsg').textContent = '';
          const diag = document.getElementById('modalDiagnostics');
          diag.style.display = 'none';
          diag.textContent = '';
          const copyStatus = document.getElementById('modalCopyStatus');
          copyStatus.style.display = 'none';
          copyStatus.textContent = '';
          refreshLiveView();
          if (!liveViewTimer) {
            liveViewTimer = setInterval(refreshLiveView, 1000);
          }
        } else if (liveViewTimer) {
          clearInterval(liveViewTimer);
          liveViewTimer = null;
        }
      });

      document.getElementById('save').addEventListener('click', saveSetup);
      document.getElementById('runValidation').addEventListener('click', runValidation);
      const perDayScheduleDetails = document.getElementById('perDayScheduleDetails');
      perDayScheduleDetails.addEventListener('toggle', () => {
        if (!perDayScheduleDetails.open) propagateMonToOtherDays();
      });
      document.getElementById('disableCameraVerification').addEventListener('change', updateCameraPanel);
      document.getElementById('checkReadabilityBtn').addEventListener('click', runReadabilityCheck);
      document.getElementById('copyDiagnosticsBtn').addEventListener('click', copyDiagnosticsToClipboard);
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeCameraLiveView(); });
      document.getElementById('deviceName').addEventListener('input', (event) => {
        const value = event.target.value || 'SmartBlaster';
        document.getElementById('deviceNameDisplay').textContent = value;
      });
      document.getElementById('profile').addEventListener('change', refreshCameraSetup);
      document.getElementById('refreshPreview').addEventListener('click', refreshCameraSetup);
      document.getElementById('saveReference').addEventListener('click', saveReferenceImage);
      document.getElementById('refreshUpdateStatus').addEventListener('click', loadUpdateStatus);
      document.getElementById('applyUpdate').addEventListener('click', applyUpdate);
      document.getElementById('rebootNow').addEventListener('click', rebootDevice);
      loadDeviceInfo();
      loadDoc('/api/readme', 'readmeText', 'Setup guide unavailable.');
      loadDoc('/api/owners-manual', 'ownersManualText', "Owner's manual unavailable.");
      loadUpdateStatus();
      loadProfiles();
    </script>
  </body>
</html>
"""

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SmartBlaster setup web server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--state-file", default="data/device_setup.json")
    parser.add_argument("--use-nmcli", action="store_true")
    args = parser.parse_args(argv)

    wifi_configurator = NmcliWifiConfigurator() if args.use_nmcli else None
    service = ProvisioningService(
      state_file=Path(args.state_file),
      wifi_configurator=wifi_configurator,
    )
    app = create_provisioning_app(service)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
