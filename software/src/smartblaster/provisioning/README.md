# Provisioning Module

This package contains framework-agnostic onboarding logic used by a future captive portal UI.

## Responsibilities
- Validate setup payload (Wi-Fi, thermostat profile, camera mode)
- Verify Wi-Fi credentials (placeholder today; replace with NetworkManager checks)
- Persist device setup state for runtime startup
- Provide thermostat profile list for UI selection

## Integration Target
A local web server (captive portal) should call `ProvisioningService.apply_setup()` and then trigger reboot/network transition.
