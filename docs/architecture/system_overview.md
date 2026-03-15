# SmartBlaster system overview
SmartBlaster is a Raspberry Pi-based device combining custom enclosure hardware, camera sensing, IR interaction, and software control.

## High-level components

- **Compute:** Raspberry Pi (e.g., Zero 2 W or similar).
- **Camera:** USB camera module with 32 × 32 mm PCB and 27 mm lens.
- **IR transmitter:** Small IR module with a 5 mm LED for blasting HVAC IR codes.
- **Enclosure:** 3D-printed, wall-mounted, landscape-oriented front face.
- **Power:** USB power to the Pi (and through it to camera/IR as needed).

## Data/control flow

1. **Inputs:**
   - Optional: temperature sensors, user configuration, schedules.
   - Optional: camera-based feedback (e.g., indicator LEDs, status).

2. **Processing:**
   - Control logic decides when and how to send IR commands.
   - IR driver encodes and transmits HVAC-specific IR sequences.

3. **Outputs:**
   - IR signals to HVAC unit.
   - Optional UI feedback (LEDs, on-screen, or remote dashboard).
   Status and diagnostics are logged for troubleshooting

## Separation of concerns

- **Hardware:** Defines physical constraints and mounting.
- **Electronics:** Defines wiring, power, and signal paths.
- **Software:** Implements behavior, protocols, and integrations.
- **Docs:** Capture decisions, constraints, and assembly steps.


## Repository Mapping
- Hardware: `hardware/`
- Software: `software/`
- Build + troubleshooting docs: `docs/`
