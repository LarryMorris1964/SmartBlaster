from smartblaster.thermostats.library import (
    CommandCriticality,
    get_command_policy,
    get_profile,
    list_profiles,
    list_supported_commands,
)


def test_midea_profile_present() -> None:
    profiles = list_profiles()
    ids = [p.id for p in profiles]
    assert "midea_kjr_12b_dp_t" in ids



def test_get_profile_returns_midea_protocol() -> None:
    profile = get_profile("midea_kjr_12b_dp_t")
    assert profile.make == "Midea"
    assert profile.ir_protocol == "midea"
    assert profile.camera_supported is True
    assert profile.supported_temperature_units == ("C", "F")
    assert profile.default_temperature_unit == "C"


def test_midea_profile_has_command_policy_defaults() -> None:
    policy = get_command_policy("midea_kjr_12b_dp_t", "power_off")
    assert policy.criticality == CommandCriticality.CRITICAL
    assert policy.max_attempts == 3
    assert policy.retry_wait_seconds == 2.0


def test_unknown_command_uses_profile_default_policy() -> None:
    policy = get_command_policy("midea_kjr_12b_dp_t", "unknown_command")
    assert policy.criticality == CommandCriticality.NORMAL
    assert policy.max_attempts == 1
    assert policy.retry_wait_seconds == 0.0


def test_supported_commands_list() -> None:
    commands = list_supported_commands("midea_kjr_12b_dp_t")
    assert "power_off" in commands
    assert "set_mode" in commands
