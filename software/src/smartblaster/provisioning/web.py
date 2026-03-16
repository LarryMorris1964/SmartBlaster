"""Local captive-portal web server scaffold for device onboarding."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

from smartblaster.provisioning.network import NmcliWifiConfigurator
from smartblaster.provisioning.service import ProvisioningService, SetupRequest


class SetupPayload(BaseModel):
  wifi_ssid: str = Field(min_length=1)
  wifi_password: str = Field(min_length=8)
  thermostat_profile_id: str
  camera_enabled: bool = False
  daily_on_time: str = Field(default="10:00", pattern=r"^\d{2}:\d{2}$")
  daily_off_time: str = Field(default="16:00", pattern=r"^\d{2}:\d{2}$")
  target_temperature_c: float = Field(default=24.0, ge=16.0, le=30.0)
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
  config_schema_version: int = Field(default=1, ge=1)


def create_provisioning_app(service: ProvisioningService | None = None) -> FastAPI:
    provisioning = service or ProvisioningService()
    app = FastAPI(title="SmartBlaster Provisioning", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/thermostats")
    def thermostats() -> list[dict[str, object]]:
        return provisioning.available_thermostats()

    @app.post("/api/setup")
    def apply_setup(payload: SetupPayload) -> dict[str, object]:
        try:
            result = provisioning.apply_setup(
                SetupRequest(
                    wifi_ssid=payload.wifi_ssid,
                    wifi_password=payload.wifi_password,
                    thermostat_profile_id=payload.thermostat_profile_id,
                    camera_enabled=payload.camera_enabled,
                    daily_on_time=payload.daily_on_time,
                    daily_off_time=payload.daily_off_time,
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
                    config_schema_version=payload.config_schema_version,
                )
            )
        except ValueError as ex:
            raise HTTPException(status_code=400, detail=str(ex)) from ex

        if not result.ok:
            raise HTTPException(status_code=400, detail=result.message)

        return asdict(result)

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
      body { font-family: Arial, sans-serif; max-width: 480px; margin: 2rem auto; padding: 0 1rem; }
      label { display:block; margin-top: 1rem; font-weight: 600; }
      input, select, button { width: 100%; padding: 0.6rem; margin-top: 0.25rem; }
      .hint { color: #555; font-size: 0.9rem; }
      .ok { color: #0a7f2e; }
      .err { color: #b00020; }
    </style>
  </head>
  <body>
    <h1>SmartBlaster Setup</h1>
    <p class=\"hint\">Connect SmartBlaster to home Wi-Fi and choose thermostat profile.</p>

    <label>Wi-Fi SSID</label>
    <input id=\"ssid\" placeholder=\"MyHomeWiFi\" />

    <label>Wi-Fi Password</label>
    <input id=\"password\" type=\"password\" />

    <label>Thermostat Profile</label>
    <select id=\"profile\"></select>

    <label><input id=\"camera\" type=\"checkbox\" /> Enable camera verification</label>

    <label>Daily Cool Start (HH:MM)</label>
    <input id="dailyOn" value="10:00" />

    <label>Daily Cool Stop (HH:MM)</label>
    <input id="dailyOff" value="16:00" />

    <label>Target Temperature (°C)</label>
    <input id="targetTemp" type="number" min="16" max="30" step="0.5" value="24" />

    <label>Thermostat Temperature Unit</label>
    <select id="tempUnit">
      <option value="C" selected>Celsius (°C)</option>
      <option value="F">Fahrenheit (°F)</option>
    </select>

    <label>Timezone</label>
    <input id="timezone" value="UTC" />

    <label>Active Days (comma-separated, mon..sun)</label>
    <input id="activeDays" value="mon,tue,wed,thu,fri,sat,sun" />

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

    <label><input id="inverterEnabled" type="checkbox" /> Enable inverter event source</label>

    <label>Inverter Source Type</label>
    <input id="inverterSourceType" value="none" />

    <label>Inverter Surplus Start (W)</label>
    <input id="inverterStartW" type="number" min="0" step="1" value="0" />

    <label>Inverter Surplus Stop (W)</label>
    <input id="inverterStopW" type="number" min="0" step="1" value="0" />

    <label>Status History File</label>
    <input id="statusHistoryFile" value="data/thermostat_status_history.log" />

    <label><input id="statusDiagnosticMode" type="checkbox" /> Diagnostic mode (save each status image)</label>

    <label>Status Image Directory</label>
    <input id="statusImageDir" value="data/status_images" />

    <button id=\"save\">Save Setup</button>
    <p id=\"result\" class=\"hint\"></p>

    <script>
      async function loadProfiles() {
        const res = await fetch('/api/thermostats');
        const profiles = await res.json();
        const sel = document.getElementById('profile');
        sel.innerHTML = '';
        for (const p of profiles) {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = `${p.make} ${p.model}`;
          sel.appendChild(opt);
        }
      }

      async function saveSetup() {
        const payload = {
          wifi_ssid: document.getElementById('ssid').value,
          wifi_password: document.getElementById('password').value,
          thermostat_profile_id: document.getElementById('profile').value,
          camera_enabled: document.getElementById('camera').checked,
          daily_on_time: document.getElementById('dailyOn').value,
          daily_off_time: document.getElementById('dailyOff').value,
          target_temperature_c: parseFloat(document.getElementById('targetTemp').value),
          thermostat_temperature_unit: document.getElementById('tempUnit').value,
          timezone: document.getElementById('timezone').value,
          active_days: document.getElementById('activeDays').value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean),
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
      }

      document.getElementById('save').addEventListener('click', saveSetup);
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
