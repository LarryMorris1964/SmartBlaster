# SmartBlaster

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
