# SmartBlaster — AI Coding Instructions

## Project Overview
Raspberry Pi-based smart device with a unified hardware + software repository.

## Repository Structure
```
SmartBlaster/
├── hardware/
│   ├── enclosure/revA/     OBJ files for 3D-printed parts; revB/ is a future placeholder
│   ├── electronics/        Schematics, PCB layouts, bill_of_materials.csv
│   └── mechanical_specs/   Reference dimensions (camera, IR components)
├── software/
│   ├── src/main.py         Raspberry Pi Python entry point
│   ├── tests/              pytest suite
│   └── requirements.txt
├── docs/                   assembly_guide.md, wiring.md, troubleshooting.md
└── LICENSE                 MIT
```

## Software Stack
- **Language**: Python 3.9+ on Raspberry Pi OS (64-bit)
- **Key libraries**: `RPi.GPIO`, `picamera2` (see `software/requirements.txt`)
- **Entry point**: `software/src/main.py`
- **Tests**: `pytest software/tests/`

## Hardware Conventions
- Enclosure parts are stored as `.obj` files; one subdirectory per revision (`revA/`, `revB/`)
- Each enclosure revision has its own `README.md` describing parts and print settings
- GPIO pin assignments are defined in `software/src/main.py` (BCM numbering); cross-reference with `docs/wiring.md`
- BOM is a CSV at `hardware/electronics/bill_of_materials.csv` with columns: Reference, Quantity, Description, Manufacturer, Part Number, Supplier, Supplier PN, Unit Price, Notes

## Developer Workflows
```bash
# Software setup (run from repo root)
cd software
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python src/main.py

# Run tests
pytest tests/
```
- No CI configured yet; no linter configured yet

## Key Docs
- Wiring pin table: [docs/wiring.md](../docs/wiring.md)
- Assembly steps: [docs/assembly_guide.md](../docs/assembly_guide.md)
- Camera clearance specs: [hardware/mechanical_specs/camera_dimensions.md](../hardware/mechanical_specs/camera_dimensions.md)
