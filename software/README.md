# SmartBlaster Software

Python application that runs on the Raspberry Pi.

## Structure

```
software/
├── src/
│   └── main.py     Entry point
├── tests/          pytest test suite
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```

## Test

```bash
pytest tests/
```
