"""Parser registry for thermostat display models."""

from __future__ import annotations

from smartblaster.vision.midea_kjr_12b_dp_t import MideaKjr12bDpTParser
from smartblaster.vision.parser import ThermostatDisplayParser


def create_parser_for_model(model_id: str) -> ThermostatDisplayParser:
    normalized = model_id.strip().lower()
    if normalized == "midea_kjr_12b_dp_t":
        return MideaKjr12bDpTParser()
    raise ValueError(f"no display parser registered for model: {model_id}")
