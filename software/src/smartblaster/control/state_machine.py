"""Basic HVAC control state machine skeleton."""

from __future__ import annotations

from dataclasses import dataclass

from smartblaster.ir.command import MideaFan, MideaIrCommand, MideaMode, MideaPreset, MideaSwing


@dataclass
class HvacStateMachine:
    state: str = "idle"

    def handle_event(self, event: str) -> str:
        if event == "cool_requested":
            self.state = "cooling"
        elif event == "heat_requested":
            self.state = "heating"
        elif event == "dry_requested":
            self.state = "drying"
        elif event == "fan_requested":
            self.state = "fan_only"
        elif event == "stop_requested":
            self.state = "idle"
        return self.state

    def build_command(
        self,
        *,
        target_temperature_c: float = 24,
        fan: MideaFan = MideaFan.AUTO,
        swing: MideaSwing = MideaSwing.OFF,
        preset: MideaPreset = MideaPreset.NONE,
    ) -> MideaIrCommand:
        if self.state == "cooling":
            return MideaIrCommand(
                mode=MideaMode.COOL,
                temperature_c=target_temperature_c,
                fan=fan,
                swing=swing,
                preset=preset,
            )
        if self.state == "heating":
            return MideaIrCommand(
                mode=MideaMode.HEAT,
                temperature_c=target_temperature_c,
                fan=fan,
                swing=swing,
                preset=preset,
            )
        if self.state == "drying":
            return MideaIrCommand(
                mode=MideaMode.DRY,
                temperature_c=target_temperature_c,
                fan=fan,
                swing=swing,
                preset=preset,
            )
        if self.state == "fan_only":
            # Midea fan-only still expects a temperature field in this scaffold model.
            return MideaIrCommand(
                mode=MideaMode.FAN_ONLY,
                temperature_c=target_temperature_c,
                fan=fan,
                swing=swing,
                preset=preset,
            )
        return MideaIrCommand(mode=MideaMode.OFF)
