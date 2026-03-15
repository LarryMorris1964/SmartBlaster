# ADR 0003: Enclosure Depth Constraint
# 0003 — Enclosure depth and internal stack

## Status

Accepted

## Context

The enclosure must:

- House the camera module and lens.
- Provide clearance behind the PCB for mounting and cabling.
- Maintain a slim, wall-mounted profile.

We have:

- 45 mm from lens front to PCB front.
- 14 mm required clearance behind PCB.

## Decision

Set the **internal depth** (front inner surface → back inner surface) to:

- **61 mm total**, composed of:
  - 45 mm lens stack.
  - 14 mm rear clearance.
  - ~2 mm lens setback behind the inner front surface.

The external depth will be slightly larger (front/back wall thickness).

## Consequences

- All internal components (Pi, IR module, wiring) must fit within this 61 mm envelope.
- The front face can remain visually slim while still accommodating the optics.
- Any future camera with a significantly different stack length will require a new enclosure revision.

