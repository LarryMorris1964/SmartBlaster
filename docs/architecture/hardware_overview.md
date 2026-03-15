# Hardware Overview

## Camera module

- **PCB size:** 32 × 32 mm.
- **PCB depth:** 14 mm.
- **Lens diameter:** 27 mm.
- **Lens length:** 45 mm (front glass → PCB front).
- **Required rear clearance:** 14 mm behind PCB to inner back shell.

## IR module

- **Board size:** 23.5 × 21.5 mm.
- **LED height:** 5 mm above board.
- **IR window:** 6 mm circular opening in front shell.
- **Range:** Nominally ~1.3 m for the current module; design allows upgrading to stronger emitters.

## Enclosure constraints

- **Internal depth (front inner → back inner):** 61 mm.
  - 45 mm lens stack.
  - 14 mm rear clearance.
  - ~2 mm lens setback behind inner front surface.
- **Lens:** Centered on front face, landscape orientation.
- **IR LED:** Offset (e.g., +25 mm in X) with its own window.
- **Mounting:** Backplate with a 1/4-20 style boss (Blink-like) for wall mounting or brackets.
- **Ventilation:** Side/perimeter venting to avoid “boxy” look and allow airflow.

## Upgrade paths

- **IR:** Replace the simple IR module with a higher-power LED + transistor driver, keeping the same LED position.
- **Sensors:** Add temperature/humidity sensors inside or near the enclosure.
- **Compute:** Swap Pi variants as long as mounting and power constraints are respected.

## Core Hardware
- Camera dimensions
- IR module dimensions
- Required clearances
- Enclosure depth calculation
- Mounting strategy
- Ventilation strategy

- Raspberry Pi (primary compute)
- Camera module mounted via `camera_bracket`
- IR emitter/receiver path mounted via `ir_mount`
- Power input via USB-C

## Mechanical Stack
- Enclosure files: `hardware/enclosure/revA/`
- Mechanical constraints: `hardware/mechanical_specs/camera_dimensions.md`

## Electrical Artifacts
- BOM: `hardware/electronics/bill_of_materials.csv`
- Schematics placeholder: `hardware/electronics/schematics/`
- PCB placeholder: `hardware/electronics/pcb/`

## Open Hardware Work Items
- Finalize selected camera SKU and tolerances
- Validate IR range and line-of-sight geometry
- Add schematic PDFs and source files
