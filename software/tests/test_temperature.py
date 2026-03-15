from smartblaster.temperature import (
    program_celsius_to_thermostat,
    quantize_program_setpoint_for_thermostat,
    thermostat_to_program_celsius,
)


def test_celsius_passthrough() -> None:
    assert thermostat_to_program_celsius(24.0, "C") == 24.0
    assert program_celsius_to_thermostat(24.0, "C") == 24.0


def test_fahrenheit_conversion_round_trip() -> None:
    f = program_celsius_to_thermostat(25.0, "F")
    assert round(f, 2) == 77.0
    c = thermostat_to_program_celsius(f, "F")
    assert round(c, 2) == 25.0


def test_quantize_for_fahrenheit_thermostat() -> None:
    # 24.2C -> 75.56F -> rounds to 76F -> 24.44C
    q = quantize_program_setpoint_for_thermostat(24.2, "F")
    assert round(q, 2) == 24.44
