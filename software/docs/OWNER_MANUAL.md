# SmartBlaster Owner's Manual

## 1. What SmartBlaster Does
SmartBlaster controls an HVAC remote over IR and can optionally read thermostat status using a camera.

Core functions:
- Scheduled daily cooling window with configurable start/stop times
- Target temperature control with thermostat profile support
- Optional camera verification for display readability and parser confidence
- Optional inverter-triggered cooling behavior

## 2. First-Time Setup
Use the captive portal page on first boot.

1. Connect to the SmartBlaster access point.
2. Open the setup portal page.
3. Enter a device name.
4. Enter your home Wi-Fi SSID and password.
5. Select your thermostat profile.
6. Enable camera verification if installed.
7. Save setup.

If camera verification is enabled:
1. Open Camera Setup in the portal.
2. Align camera framing so the thermostat display is clearly visible.
3. Check focus, glare, and parser confidence.
4. Save a reference image labeled installer-approved.

## 3. Setup Page Fields
Important fields:
- Device Name: Friendly name shown in setup and runtime metadata.
- Daily Cool Start/Stop: 24-hour HH:MM local time.
- Target Temperature: Desired setpoint for cool mode.
- Thermostat Temperature Unit: Must be supported by selected profile.
- Active Days: Comma-separated day list (mon..sun).

Advanced fields:
- Inverter controls: Start/stop thresholds and source type.
- Status diagnostics: Save status history and optional status images.
- Reference capture options: Parse-failure capture, training mode, offload settings.

## 4. Normal Operation
After setup is saved, SmartBlaster can run in runtime mode.

Typical behavior:
- Applies profile-supported commands for cooling, fan, and swing.
- Uses policy metadata to classify command verification behavior.
- Captures status snapshots and reference images when configured.

## 5. Troubleshooting
- Wi-Fi setup fails:
  - Re-check SSID/password and signal quality.
- Camera status not readable:
  - Reposition camera, increase lighting, reduce glare.
- Low parser confidence:
  - Save a clean reference image and verify profile selection.
- Unit does not respond to commands:
  - Confirm IR emitter placement and thermostat profile.

## 6. Safety Notes
- Do not block thermostat vents or safety sensors.
- Keep SmartBlaster and power supplies dry.
- Treat camera captures as potentially sensitive operational data.

## 7. Maintenance
- Keep lens clean and thermostat display unobstructed.
- Review status/reference storage periodically.
- Update software when newer builds are available.
