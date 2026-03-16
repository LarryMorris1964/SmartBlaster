# SmartBlaster Project Backlog

This file is the running backlog for the project. Keep items here even when they span multiple days.

## Active Backlog

### 1. Weekly Scheduling in Captive Portal

Status: Planned

Goals:
- Add a setup UI for on/off time by day of week.
- Support a quick option to apply the same on/off window to every day.
- Persist schedule in setup state.
- Feed schedule into runtime config.
- Execute simple on/off automation at configured times.

Notes:
- This replaces env-only fixed daily automation with a user-facing schedule.
- Keep first version simple and deterministic.

### 2. Setup Validation Workflow (IR Capability Shakeout)

Status: Planned

Goals:
- Add a setup validation action that executes each IR command expected for the selected profile.
- Capture before/after images for each command step.
- Record pass/fail, parse confidence, and any error reason per step.
- Save a validation report artifact for later review.

Notes:
- This should surface latent command/parse regressions before field deployment.
- Reuse existing camera capture/reference storage where practical.

### 3. Home Automation Integration Design

Status: Planned

Goals:
- Define first integration architecture for IFTTT.
- Define first integration architecture for Amazon Alexa.
- Define first integration architecture for Apple/HomeKit and related ecosystems.
- Specify the minimum SmartBlaster API/event surface needed to support these integrations.

Notes:
- Start with architecture and interface contracts before implementation.

### 4. Rich Logging and Diagnostics

Status: In progress — core infrastructure complete; integration points to grow

Goals:
- Emit structured JSON activity records for all key interactions: IR commands sent, camera verification results, scheduling events, async events (solar/inverter), and home automation API commands.
- Write records to a rotating JSONL file (`data/activity_log.jsonl` by default, configurable via `SMARTBLASTER_ACTIVITY_LOG_FILE`).
- Use `structlog` over stdlib `logging`; capture logs in tests via `structlog.testing.capture_logs()`.
- Wire `home_automation_command` calls into future IFTTT/Alexa/HomeKit integration layer as it is built.
- Add `ir_command_verified` / `ir_command_verification_failed` call sites once the setup validation workflow (item 2) is implemented.

Notes:
- `ActivityLogger` is fully injectable — pass a custom instance in tests, or let runtime create one from config.
- `configure_logging()` is called once by `SmartBlasterRuntime.from_env()` at startup.

## Completed

- None yet.
