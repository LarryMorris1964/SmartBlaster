# Wiring Guide

All connections between the Raspberry Pi GPIO header and external components.

## Pin Reference (BCM numbering)

| GPIO | Function | Component | Notes |
|------|----------|-----------|-------|
| 4    | IR TX    | IR LED (via 100Ω resistor) | |
| 17   | IR RX    | TSOP38238 OUT pin | |
| —    | 5V       | IR receiver VCC | |
| —    | GND      | IR LED cathode, receiver GND | |

## Camera
- Connected via CSI ribbon cable (15-pin FFC) — no GPIO required

## Power
- Pi powered via USB-C (5V 3A minimum)
- IR components powered from Pi 5V header pin

## Diagram
_Add a wiring diagram image here (e.g., Fritzing export)._
