# ADR 0004: HVAC Control Strategy
# 0004 — HVAC control strategy

## Status

Planned

## Context

SmartBlaster’s primary function is to control HVAC units (e.g., mini-splits) via IR.  
Different units use different IR protocols and state models.

## Decision

- Use an **IR blasting** approach:
  - Encode and send full IR commands (mode, temp, fan, etc.).
  - Maintain an internal representation of the desired HVAC state.
- Start with:
  - Manual configuration of IR codes per device.
  - A simple state machine for on/off, mode, and temperature.
- Design the software so:
  - IR protocols are pluggable.
  - Closed-loop feedback (e.g., temperature sensors, camera-based checks) can be added later.
Use a conservative state-machine approach with explicit command pacing, confirmation checks, and safe fallbacks.

### Triggering roadmap

1. **Phase 1 (now): timed automation**
  - Use fixed daily ON/OFF times.
  - ON event sends COOL command at configured setpoint.
  - OFF event sends power-off command.

2. **Phase 2 (future): external energy stimuli**
  - Replace or augment timed triggers with inverter/charger surplus signals.
  - Keep the same state machine and IR dispatch path.
  - Implement external integrations as event sources so the control core remains unchanged.

## Rationale
- Prevents rapid command bursts and inconsistent device state
- Easier to test and reason about than ad-hoc command logic
- Supports later expansion with scheduling and sensor feedback

## Consequences

- Initial versions may rely on user-provided IR codes or captured sequences.
- The control logic must be robust to “stateless” IR (no direct feedback from the HVAC unit).
- Future enhancements (sensors, cloud integration) can build on the same core model.
- Requires explicit state definitions and transition tests
- Adds upfront design overhead but improves reliability
- Timing-based operation may be imperfect vs true energy-aware control, but provides a low-risk path to validate automation and IR reliability before inverter integration.

