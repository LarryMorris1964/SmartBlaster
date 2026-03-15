# SmartBlaster Enclosure — Rev A

This is the first working enclosure for the SmartBlaster HVAC controller.

## Included Parts


| File | Description |
|------|-------------|
| `smartblaster_front.obj` | Front face panel |
| `smartblaster_back.obj` | Rear panel with port cutouts |
| `camera_bracket.obj` | Camera module mounting bracket |
| `ir_mount.obj` | IR sensor/emitter mount |
| `pi_standoffs.obj` | Raspberry Pi PCB standoff posts |
| `blink_mount.obj` | Raspberry Pi PCB standoff posts |

## Print Settings (recommended)

- **Material**: PLA or PETG
- **Layer height**: 0.2 mm
- **Infill**: 20%
- **Supports**: Required for `camera_bracket.obj` and `ir_mount.obj`

## Assembly
See [docs/assembly_guide.md](../../../../docs/assembly_guide.md) for step-by-step instructions.

## Notes

- Designed for landscape camera orientation
- Flush-mounted lens behind a chamfered window
- IR LED positioned at +25 mm X offset
- Pi standoffs sized for Raspberry Pi Zero 2 W (adjustable)
- Backplate includes Blink-style 1/4-20 mount boss

See `/docs/enclosure_printing.md` for print settings.