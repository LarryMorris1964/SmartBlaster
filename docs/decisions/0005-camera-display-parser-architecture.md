# ADR 0005: Camera Display Parser Architecture

## Status

Proposed

## Date

2026-03-15

## Context

SmartBlaster camera support should be:

- Model-specific for parsing accuracy.
- Standalone so parsing can evolve independently from control logic.
- Predictable for safety: parser emits structured state + confidence, not direct control actions.

For the first supported thermostat (`midea_kjr_12b_dp_t`), the display includes indicators for:

- Mode (`auto`, `cool`, `dry`, `heat`, `fan_only`)
- Timer ON/OFF
- Follow-me
- Power/ON-OFF
- Fan speed
- Lock
- Setpoint digits
- Unit icon (`C` or `F`)

## Decision

1. **Internal standard unit is Celsius.**
   - Runtime and control logic remain Celsius-centric.
   - Camera parser reads thermostat display unit and value.
   - Conversion is applied at boundaries only.

2. **Use a model-specific parser adapter.**
   - Introduce `ThermostatDisplayParser` protocol.
   - Each supported thermostat model gets a dedicated parser implementation.
   - First implementation target: `MideaKjr12bDpTParser`.

3. **Use a normalized output object.**
   - Parsers return `ThermostatDisplayState` with:
     - canonical fields (`mode`, `set_temperature`, `temperature_unit`, etc.)
     - `confidence_by_field`
     - `unreadable_fields`
     - raw indicator flags for diagnostics

4. **No direct actuation from parser output.**
   - Parser only reports observed state.
   - Control decisions remain in runtime/state-machine layer.

5. **Handle uncertainty explicitly.**
   - Missing/ambiguous fields are represented as `None` or `UNKNOWN`.
   - Downstream logic can gate behavior by confidence thresholds.

## Consequences

### Positive

- Clear separation of concerns.
- Easier model-by-model rollout.
- Safer behavior under uncertain vision reads.

### Trade-offs

- Requires per-model parser maintenance.
- Calibration and test fixtures needed per display model.

## Implementation Notes

Scaffolded modules:

- `software/src/smartblaster/vision/models.py`
- `software/src/smartblaster/vision/parser.py`
- `software/src/smartblaster/vision/midea_kjr_12b_dp_t.py`

These are interface-first and intentionally lightweight, ready for iterative CV implementation.
