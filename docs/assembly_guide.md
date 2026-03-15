# Assembly Guide

Step-by-step instructions for building the SmartBlaster enclosure and mounting all components.

## Parts Required
- All 3D-printed parts from `hardware/enclosure/revA/`
- Components listed in `hardware/electronics/bill_of_materials.csv`
- M2×6 screws ×4 (Pi standoffs)
- M2×4 screws ×2 (camera bracket)

## Steps

### 1. Print all enclosure parts
Print each `.obj` file from `hardware/enclosure/revA/`. See the [enclosure README](../hardware/enclosure/revA/README.md) for recommended print settings.

### 2. Mount Raspberry Pi
- Press Pi into `pi_standoffs` posts
- Secure with M2×6 screws

### 3. Install camera
- Attach ribbon cable to Pi CSI port before mounting
- Snap camera PCB into `camera_bracket`
- Secure bracket with M2×4 screws

### 4. Install IR components
- Seat IR LED and receiver into `ir_mount`
- Route wires per [wiring.md](wiring.md)

### 5. Close enclosure
- Align `smartblaster_front` with `smartblaster_back`
- Snap or screw closed (hardware TBD)
