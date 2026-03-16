"""Thermostat display parser protocol.

Design intent:
- Keep parser model-specific and standalone.
- Return model-agnostic state values for the control/runtime layers.
"""

from __future__ import annotations

from typing import Protocol

from smartblaster.vision.models import ThermostatDisplayState


class ThermostatDisplayParser(Protocol):
    model_id: str

    def parse(self, frame: bytes) -> ThermostatDisplayState:
        """Parse one frame and return extracted display state."""
