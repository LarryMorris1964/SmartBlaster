# Software Overview
# Software overview

## Structure

- `software/src/smartblaster/`
  - `camera.py` — camera access and basic capture/inspection.
  - `ir_driver.py` — IR encoding and transmission.
  - `control_logic.py` — HVAC control decisions and state machine.
  - `ui.py` — local UI or integration hooks (e.g., web UI, Home Assistant).
  - `__init__.py` — package initialization.
- `software/src/main.py` — entry point / launcher.
- `software/tests/` — unit tests (e.g., IR encoding, control logic).
- `software/tools/` — utilities (e.g., IR code capture, diagnostics).

## Responsibilities

- **Camera layer:**
  - Initialize camera.
  - Provide frames or snapshots for diagnostics or future feedback loops.

- **IR driver:**
  - Represent IR codes (protocol, carrier frequency, timings).
  - Transmit codes via GPIO/USB-attached IR hardware.
  - Provide a way to add HVAC-specific code sets.

- **Control logic:**
  - Decide when to send IR commands (on/off, mode, temperature).
  - Maintain internal state (target vs. actual).
  - Allow manual overrides and schedules.

- **UI / integration:**
  - Local configuration (files, simple UI, or API).
  - Optional integration with Home Assistant / other ecosystems.

## Non-goals (for now)

- Full-blown cloud backend.
- Complex computer vision.
- Multi-room orchestration.

These can be layered on later if the core remains clean and modular.


## Runtime
- Python project structure
- Drivers (camera, IR)
- Control logic
- UI layer
- Configuration system
- Logging

- Language: Python 3.9+
- Entry point: `software/src/main.py`
- Dependencies: `software/requirements.txt`

## Responsibilities
- Initialize hardware interfaces (GPIO/camera/IR)
- Run control loop / event handlers
- Emit control outputs and collect diagnostics

## Testing
- Test location: `software/tests/`
- Test runner: `pytest`

## Near-term Software Milestones
1. Define module boundaries (camera, ir, control, telemetry)
2. Add configuration model for GPIO and timings
3. Add automated tests for control logic
4. Add deployment process for Raspberry Pi target
