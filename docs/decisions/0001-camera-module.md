# ADR 0001: Camera Module Selection

## Status

Accepted

## Context

SmartBlaster needs a front-facing camera for:

- Visual feedback (e.g., alignment, diagnostics).
- Future potential closed-loop features.

The camera must fit inside a compact, wall-mounted enclosure and support a landscape orientation.

## Decision

Use a USB camera module with:

- **PCB:** 32 × 32 mm.
- **PCB depth:** 14 mm.
- **Lens diameter:** 27 mm.
- **Lens length:** 45 mm (front glass → PCB front).
- **Rear clearance:** 14 mm behind PCB to inner back shell.

The lens is:

- Centered on the front face.
- Oriented in landscape.
- Flush-mounted behind a chamfered window for a non-camera appliance look.

## Consequences

- Enclosure depth and internal layout are constrained by the 45 mm lens stack + 14 mm rear clearance.
- Future camera swaps must respect these dimensions or trigger a new hardware revision.
- Software can assume a fixed camera position and orientation.
- Status: Proposed
- Date: 2026-03-15

## Context
- Why we chose this camera
- Dimensions
- Landscape orientation
- Flush‑mount lens design
