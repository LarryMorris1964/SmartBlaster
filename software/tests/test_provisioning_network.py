from smartblaster.provisioning.network import AlwaysSuccessWifiConfigurator


def test_always_success_wifi_configurator() -> None:
    cfg = AlwaysSuccessWifiConfigurator()
    assert cfg.connect_to_home_wifi("HomeWiFi", "supersecret") is True
