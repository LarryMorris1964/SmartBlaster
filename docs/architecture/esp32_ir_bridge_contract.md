# ESP32 IR Bridge Contract (Pi ↔ ESP32)

This document defines the serial/MQTT JSON contract between SmartBlaster (Pi) and an ESP32 IR transmitter service.

## Protocol Version
- `v = 1`

## Command Envelope (Pi → ESP32)

Topic: `midea_ir.command`

```json
{
  "v": 1,
  "topic": "midea_ir.command",
  "request_id": "b812eb2f-93dc-404f-8ded-94d04a44bd6d",
  "payload": {
    "mode": "cool",
    "temperature_c": 24,
    "fan": "medium",
    "swing": "vertical",
    "preset": "none",
    "beeper": false
  }
}
```

### Payload Fields
- `mode`: `off|auto|cool|heat|dry|fan_only`
- `temperature_c`: required for non-`off`, range `17..30`
- `fan`: `auto|low|medium|high|silent|turbo`
- `swing`: `off|vertical|both`
- `preset`: `none|sleep|eco|boost`
- `follow_me_c`: optional, range `0..37`
- `beeper`: boolean

## ACK Envelope (ESP32 → Pi)

Topic: `midea_ir.ack`

Success:
```json
{"v":1,"topic":"midea_ir.ack","request_id":"...","ok":true}
```

Failure:
```json
{"v":1,"topic":"midea_ir.ack","request_id":"...","ok":false,"error_code":"invalid_command","error_message":"temperature_c out of range"}
```

## Standard Error Codes
- `bad_json`
- `bad_schema`
- `unsupported_version`
- `invalid_command`
- `tx_failed`

## Python Reference Implementation
- Encoder/parser helpers: [software/src/smartblaster/ir/esp32_schema.py](../../software/src/smartblaster/ir/esp32_schema.py)
- Typed command model: [software/src/smartblaster/ir/command.py](../../software/src/smartblaster/ir/command.py)
