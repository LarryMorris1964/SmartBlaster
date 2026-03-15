# 0002 — IR module and range

## Status

Accepted (with upgrade path)

## Context

SmartBlaster must send IR commands to HVAC units at ~3 m / 10 ft.  
The initial IR module under consideration has a nominal range of ~1.3 m.

## Decision

- Use a small IR module with:
  - **Board:** 23.5 × 21.5 mm.
  - **LED:** 5 mm package, 5 mm height.
- Place the LED behind a 6 mm circular window, offset from the camera (e.g., +25 mm in X).
- Design the enclosure and mounting so:
  - A standard 5 mm IR LED position is fixed.
  - The PCB footprint allows for a future custom or higher-power IR driver.

## Consequences

- Rev A may have limited range depending on drive current and LED characteristics.
- The enclosure does **not** need to change if the IR electronics are upgraded, as long as the LED remains in the same physical position.
- Software can treat the IR path as a pluggable driver (simple module now, more advanced later).
- Status: Proposed
- Date: 2026-03-15

## Context
- Range concerns
- Upgrade path
- LED height
- Window placement

SmartBlaster needs IR transmit only for initial Midea thermostat goals. Receive capability for control and verification could be valuable in future use cases.


