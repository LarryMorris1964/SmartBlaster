# SmartBlaster design goals

## Core intent

- **Purpose:** Wall-mounted smart IR “blaster” for HVAC (mini-splits, AC units).
- **Form factor:** Looks like a thermostat/appliance, not a camera.
- **Orientation:** Landscape camera, centered, with a clean front face.
- **Audience:** Hobbyists and tinkerers, but with a professional, finished feel.

## Hardware goals

- **Minimal hardware footprint:** Small, wall-mounted enclosure with no dangling dongles.
- **Hobbyist-friendly:** Off-the-shelf camera and IR modules, 3D-printable enclosure.
- **Modular:** Enclosure, electronics, and software can evolve independently.
- **Upgradable IR path:** Start with a simple IR module, allow future higher-power emitters.

## Software goals

- **Modular architecture:** Separate drivers, control logic, and UI.
- **Closed-loop capable:** Room to add sensing/feedback later (temp, camera-based checks).
- **Local-first:** Works standalone; cloud/Home Assistant integration is optional.
- **Testable:** Drivers and logic covered by unit tests where practical.

## Collaboration goals

- **Open-source:** Clear structure, documented decisions, easy to fork and extend.
- **Reproducible:** Dimensions, BOM, and build steps are all captured in the repo.
- **Revision-safe:** Hardware revisions are explicit (`revA`, `revB`, …), not overwritten.

## Product Goals
- Reliable autonomous operation on Raspberry Pi hardware
- Practical DIY assembly using 3D-printed enclosure parts
- Clear documentation for wiring, assembly, and troubleshooting
- Wall‑mounted, appliance‑like device
- Landscape camera orientation
- IR control for HVAC
- Open‑source, hobbyist‑friendly
- Modular hardware + software
- Enclosure independent from software development

## Engineering Goals
- Keep hardware/software boundaries explicit
- Prefer serviceable mechanical design (easy opening/rework)
- Keep wiring simple and reproducible
- Make software testable outside full hardware context where possible

## Non-goals (for now)
- Cloud dependency for core local control
- Complex custom PCB before validating revA behavior
- Over-optimization before first stable end-to-end prototype

