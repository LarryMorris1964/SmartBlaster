# SmartBlaster — Open Smart HVAC Controller

SmartBlaster is an open-source, wall-mounted HVAC controller featuring:

- A landscape camera for visual feedback
- IR control for mini-splits and AC units
- A sleek, thermostat-like enclosure
- Modular hardware and software design
- Hobbyist-friendly assembly and open collaboration

This repository contains:

- **Hardware** (enclosure CAD, electronics, mechanical specs)
- **Software** (Python-based control logic, drivers, tools)
- **Documentation** (assembly, wiring, printing, troubleshooting)

Contributions are welcome!

A Raspberry Pi-based smart device. This repo contains both hardware design files and the Python software stack.

## Repository Layout

```
SmartBlaster/
├── hardware/
│   ├── enclosure/revA/     3D-printable enclosure parts (.obj)
│   ├── electronics/        Schematics, PCB files, BOM
│   └── mechanical_specs/   Reference dimensions and tolerances
├── software/               Python source, tests, dependencies
├── docs/                   Assembly guide, wiring diagrams, troubleshooting
└── LICENSE
```

## Quick Start

### Hardware
See [docs/assembly_guide.md](docs/assembly_guide.md) for full build instructions and [docs/wiring.md](docs/wiring.md) for wiring diagrams.

3D print files are in `hardware/enclosure/revA/`. All parts are designed for standard FDM printing (PLA or PETG recommended).

### Software
```bash
cd software
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## Hardware Revision History

| Rev | Status | Notes |
|-----|--------|-------|
| A   | Current | Initial release |
| B   | Planned | TBD |

## License
See [LICENSE](LICENSE).


## Project Manifest

SmartBlaster is defined by the following core constraints:

- Camera PCB: 32 × 32 mm, 14 mm deep
- Lens: 27 mm diameter, 45 mm long
- Required rear clearance: 14 mm
- IR module: 23.5 × 21.5 mm, 5 mm LED height
- Enclosure internal depth: 61 mm
- Landscape orientation
- IR LED offset: +25 mm X

These constraints drive both the enclosure geometry and the software architecture.