# Device Onboarding (Captive Portal First)

## Goal
Allow non-technical users to power on SmartBlaster and complete setup from a phone without Raspberry Pi knowledge.

## First-Boot Flow
1. Device enters provisioning mode and exposes temporary Wi-Fi AP (e.g., `SmartBlaster-XXXX`).
2. User connects with phone; captive portal opens setup page.
3. User enters:
   - Home Wi-Fi SSID/password
   - Thermostat make/model profile
   - Camera enabled/disabled
4. Device validates inputs, saves config, exits provisioning mode, and joins home Wi-Fi.

## Current Implementation Scaffold
- Provisioning core logic: [software/src/smartblaster/provisioning/service.py](../../software/src/smartblaster/provisioning/service.py)
- Thermostat profile library: [software/src/smartblaster/thermostats/library.py](../../software/src/smartblaster/thermostats/library.py)
- Captive portal web scaffold: [software/src/smartblaster/provisioning/web.py](../../software/src/smartblaster/provisioning/web.py)

Run locally:
- `smartblaster-setup-server --host 0.0.0.0 --port 8080`

Device bootstrap entrypoint:
- `smartblaster-device --mode auto --state-file data/device_setup.json`
- `auto` mode selects setup portal when state is missing, otherwise runtime mode.

## Launch Constraints
- IR-only mode is fully supported (`camera_enabled=false`).
- Camera verification routines are model-specific and initially enabled only for Midea KJR-12B-DP-T profile.
- Minimum launch requirement is selecting a known IR profile from library and storing Wi-Fi credentials.

## Future Extensions
- Replace fixed schedule with inverter/solar event source integration.
- Add camera OCR/vision pipelines per thermostat profile incrementally.
- Add BLE-assisted provisioning as optional fallback, while keeping captive portal as default path.
