# ESP32 IR Bridge Firmware (Reference Scaffold)

This folder contains a reference Arduino sketch for bridging SmartBlaster JSON commands to Midea IR transmissions.

## Goal
- Receive line-delimited JSON over Serial
- Parse `midea_ir.command` envelopes
- Transmit Midea IR packet via `IRremoteESP8266`
- Return `midea_ir.ack` envelope with success/error

## Dependencies
- IRremoteESP8266
- ArduinoJson

## Message Contract
See [docs/architecture/esp32_ir_bridge_contract.md](../../docs/architecture/esp32_ir_bridge_contract.md).

## Wiring (example)
- IR LED transistor driver on `GPIO4` (change in sketch as needed)
- Optional status LED on board LED

## Notes
This is a scaffold and intentionally keeps mode mapping conservative. Extend for model-specific features once captures from KJR-12B-DP-T are validated.
