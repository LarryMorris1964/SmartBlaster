# SmartBlaster Software

Python application that runs on the Raspberry Pi.

## Structure

```
software/
├── src/
│   └── main.py     Entry point
├── tests/          pytest test suite
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```

## Test

```bash
pytest
```

## Project Diary

An AI-assisted build diary lives in `docs/AI_DIARY.md`.

## Project Backlog

A running project backlog lives in `docs/PROJECT_BACKLOG.md`.


## Update System Default Repo (OEM/Fork Guidance)

By default, SmartBlaster checks for updates from the OEM repo:

	LarryMorris1964/SmartBlaster

To use your own update repo (for forks/derivatives), set the environment variable in your systemd service or shell:

```bash
export SMARTBLASTER_UPDATE_REPO="yourusername/yourrepo"
```
Or edit the systemd service file to add:
```
Environment=SMARTBLASTER_UPDATE_REPO=yourusername/yourrepo
```
This will override the default and enable updates from your own repo.

## New Scaffolded Modules

- `src/smartblaster/config.py` — runtime settings from environment variables
- `src/smartblaster/hardware/` — camera + IR adapters
- `src/smartblaster/control/state_machine.py` — HVAC control state skeleton
- `src/smartblaster/services/runtime.py` — runtime wiring and loop

Run with:

```bash
python -m smartblaster
```

## CLI (ESP32 IR Bridge)

Send commands to the ESP32 bridge over serial:

```bash
smartblaster-cli --serial-port COM3 set --mode cool --temp 24 --fan medium --swing vertical
smartblaster-cli --serial-port COM3 off
```

Request thermostat status via camera parse pipeline:

```bash
smartblaster-cli status --model-id midea_kjr_12b_dp_t \
	--history-file data/thermostat_status_history.log
```

Enable diagnostic mode to also save each captured image for verification:

```bash
smartblaster-cli status --diagnostic-save-images --diagnostic-image-dir data/status_images
```

The status request flow is:
- capture camera frame
- parse display indicators (mode/fan/timer/follow-me/power/setpoint)
- append a text-readable JSON-lines history record
- optionally save source image in diagnostic mode

## Offline Vision Validation (No Live Thermostat Required)

You can evaluate parser quality against labeled JPEG samples without a full HVAC system:

```bash
smartblaster-cli vision-eval \
	--model-id midea_kjr_12b_dp_t \
	--images-dir data/samples/midea \
	--labels-file data/samples/midea/labels.jsonl \
	--output-report data/vision_eval_report.json
```

Use `data/samples/midea/labels.sample.jsonl` as a template for labels.

Validate labels before running evaluation:

```bash
smartblaster-cli vision-validate-labels \
	--labels-file data/samples/midea/labels.sample.jsonl \
	--images-dir data/samples/midea
```

If validation fails, the command prints each issue and exits non-zero.

Full label schema reference:
- `data/samples/midea/labels.schema.json`

## Runtime Event Dispatch

The runtime loop now maps high-level events to typed Midea commands:

- `cool_requested` -> COOL command
- `heat_requested` -> HEAT command
- `dry_requested` -> DRY command
- `fan_requested` -> FAN_ONLY command
- `stop_requested` -> OFF command

When state changes, runtime emits a `midea_ir.command` frame via `IrService.send_midea_command()`.

## Daily Automation (Initial Solar Approximation)

Configure fixed daily on/off events via environment variables:

- `SMARTBLASTER_DAILY_ON_TIME` (HH:MM, local time)
- `SMARTBLASTER_DAILY_OFF_TIME` (HH:MM, local time)
- `SMARTBLASTER_TARGET_TEMPERATURE_C`
- `SMARTBLASTER_SOLAR_WEEKLY_SCHEDULE_JSON` (optional per-day override JSON)

Default schedule is 10:00 ON and 15:00 OFF.
Default target setpoint is 26C (about 78.8F).

Example weekly schedule JSON:

```json
{
	"mon": {"on_time": "09:45", "off_time": "15:30"},
	"tue": {"on_time": "10:00", "off_time": "15:00"}
}
```

Current behavior:
- At `DAILY_ON_TIME`, SmartBlaster emits `cool_requested` and sends a COOL command at the target temperature.
- At `DAILY_OFF_TIME`, SmartBlaster emits `stop_requested` and sends OFF.
- Temperature control is sent as an explicit target setpoint in the IR payload (for example 24C), not as temp-up/temp-down button increments.
- Midea IR payload setpoints are encoded in Celsius (`temperature_c`), even when thermostat UI settings may be Fahrenheit-facing.
- Runtime treats thermostat timer state as informational; direct runtime ON/OFF commands are intended to supersede manual timer settings.

Future behavior:
- External stimuli (e.g., inverter/solar surplus signals) can inject events through `EventSource` implementations without replacing runtime/state-machine logic.

## Camera Optional Operation

SmartBlaster supports IR-only operation (no camera attached):

- Set `SMARTBLASTER_CAMERA_ENABLED=false`
- Runtime uses a no-op camera service and still executes all IR scheduling/dispatch

This enables a Sensibo-style launch mode where the device blasts IR commands without visual verification.

## Thermostat Profile Selection

Set `SMARTBLASTER_THERMOSTAT_PROFILE_ID` to select a supported profile from the thermostat library.

Current launch profile:
- `midea_kjr_12b_dp_t`

Profile metadata lives in `src/smartblaster/thermostats/library.py`.

Command execution policy is now profile-driven (criticality, retry count, retry wait), keyed by thermostat profile.
This keeps command behavior extensible across brands/models while reusing the same runtime flow.
At setup time, profile selection determines:
- IR protocol implementation
- camera support availability
- command policy defaults used by runtime (for current logging and future verification/retry orchestration)

## Captive Portal Provisioning Scaffold

Provisioning core logic is implemented in `src/smartblaster/provisioning/service.py`.
It validates setup payloads (Wi-Fi credentials, thermostat profile, camera mode) and persists setup state.

A future local web server/captive portal can call this module directly.

A local setup server scaffold is now available:

```bash
smartblaster-setup-server --host 0.0.0.0 --port 8080
```

Endpoints:
- `GET /` setup page (basic HTML)
- `GET /api/thermostats` profile options from library
- `POST /api/setup` validate and persist onboarding settings
- `GET /api/camera/status` live camera alignment metrics for the selected thermostat profile
- `GET /api/camera/preview.jpg` live preview JPEG with parser overlay banner
- `POST /api/camera/reference-capture` save install-time reference images with JSON metadata

The captive portal setup page now includes a `Camera Setup` section intended for headless installs:
- live preview with overlay
- parser readability/focus/glare feedback
- install-time reference image capture

Reference images are stored under `data/reference_images/<phase>/...` so the same storage layout can be reused later for runtime/support lifecycle snapshots.

Retention behavior:
- phase-specific FIFO retention (oldest captures pruned first, newest retained)
- higher default retention for high-value phases like `runtime_parse_failure`
- lower default retention for bulk phases like `training_periodic`

Offload readiness:
- each capture metadata file tracks offload state (`pending` / `offloaded`), attempt counts, and optional remote IDs
- this is intended to support future periodic upload/offload to a central server without changing on-device capture format

Offload skeleton (future work item):
- runtime includes a disabled-by-default offload worker scaffold that drains pending captures FIFO in batches
- current transport is a no-op placeholder; real server transport/auth/retry policy is still future work

Current lifecycle hook:
- runtime parse failures can automatically save the failed source image, overlay, and error context into the reference-image store

Status request behavior now supports two camera/parse paths:
- strict (`request_status`): used by command-verification logic; camera/parse failures are fatal to that transaction
- best-effort (`request_status_best_effort`): used by opportunistic workflows (for example periodic snapshots); camera/parse failures are non-fatal and returned as typed outcomes

Provisioning now also persists future-facing capture options:
- `reference_capture_on_parse_failure`
- `training_mode_enabled`
- `training_capture_interval_minutes`
- `validate_capabilities_enabled`

The training-mode and capability-validation workflows are not fully automated yet, but their settings now flow through setup state into runtime configuration so later hooks can reuse the same reference-image storage path.

## Device Bootstrap Mode

## Raspberry Pi OS Lite Deployment

Pi OS Lite (64-bit) is sufficient for SmartBlaster.

Deployment assets:
- First-boot setup script: `deploy/install/first_boot_setup.sh`
- Vision package install script (OpenCV, Tesseract, TFLite best-effort): `deploy/install/install_vision_stack.sh`
- Service installer: `deploy/install/install_service.sh`
- systemd unit: `deploy/systemd/smartblaster.service`
- Full image prep checklist: `docs/PI_IMAGE_PREP_CHECKLIST.md`

Typical bring-up flow on Pi:

```bash
cd ~/SmartBlaster/software
sudo ./deploy/install/first_boot_setup.sh
systemctl status smartblaster.service
```

Use one command to choose setup vs runtime automatically:

```bash
smartblaster-device --mode auto --state-file data/device_setup.json
```

Startup behavior:
- If setup state file is missing: run captive setup server mode.
- If setup state file exists: run HVAC runtime mode.

Override manually:
- `--mode setup`
- `--mode run`

Enable AP-mode script orchestration during setup mode:

```bash
smartblaster-device --mode setup --enable-ap-mode \
	--ap-use-sudo \
	--ap-start-script ./deploy/ap/start_ap_mode.sh \
	--ap-stop-script ./deploy/ap/stop_ap_mode.sh
```

For production service users, add a restricted sudoers rule so only AP scripts are permitted:
- [software/deploy/security/smartblaster-apmode.sudoers](deploy/security/smartblaster-apmode.sudoers)

Use real Wi-Fi verification with NetworkManager in setup server mode:

```bash
smartblaster-setup-server --use-nmcli
```

## Service Installation Helpers (Linux/Raspberry Pi)

From `/opt/smartblaster/software`:

```bash
./deploy/install/preflight_check.sh
```

```bash
./deploy/install/post_install_check.sh
```

```bash
sudo ./deploy/install/install_service.sh
```

Optional (skip checks):

```bash
sudo ./deploy/install/install_service.sh --skip-preflight --skip-post-check
```

To uninstall service artifacts:

```bash
sudo ./deploy/install/uninstall_service.sh
```
