from smartblaster.thermostats.library import get_profile, list_profiles


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
