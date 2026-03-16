from pathlib import Path

from smartblaster.provisioning.network import AlwaysSuccessWifiConfigurator
from smartblaster.provisioning.service import ProvisioningService, SetupRequest


def test_apply_setup_persists_state(tmp_path: Path) -> None:
    state_file = tmp_path / "device_setup.json"
    svc = ProvisioningService(
        state_file=state_file,
        wifi_configurator=AlwaysSuccessWifiConfigurator(),
    )

    result = svc.apply_setup(
        SetupRequest(
            device_name="Living Room SmartBlaster",
            wifi_ssid="HomeWiFi",
            wifi_password="supersecret",
            thermostat_profile_id="midea_kjr_12b_dp_t",
            camera_enabled=False,
            daily_on_time="09:15",
            daily_off_time="17:45",
            target_temperature_c=23.5,
            timezone="America/Los_Angeles",
            active_days=["mon", "tue", "wed", "thu", "fri"],
            fan_mode="high",
            swing_mode="vertical",
            preset_mode="eco",
            thermostat_temperature_unit="F",
            inverter_source_enabled=True,
            inverter_source_type="modbus-tcp",
            inverter_surplus_start_w=1500,
            inverter_surplus_stop_w=400,
            status_history_file="data/thermostat_status_history.log",
            status_diagnostic_mode=True,
            status_image_dir="data/status_images",
            reference_image_dir="data/reference_images",
            reference_capture_on_parse_failure=True,
            training_mode_enabled=True,
            training_capture_interval_minutes=60,
            validate_capabilities_enabled=True,
            reference_offload_enabled=True,
            reference_offload_interval_minutes=20,
            reference_offload_batch_size=40,
            config_schema_version=1,
        )
    )

    assert result.ok is True
    assert state_file.exists()
    text = state_file.read_text(encoding="utf-8")
    assert "Living Room SmartBlaster" in text
    assert "HomeWiFi" in text
    assert "midea_kjr_12b_dp_t" in text
    assert "09:15" in text
    assert "17:45" in text
    assert "23.5" in text
    assert "America/Los_Angeles" in text
    assert "modbus-tcp" in text
    assert "\"thermostat_temperature_unit\": \"F\"" in text
    assert "thermostat_status_history.log" in text
    assert "status_images" in text
    assert "reference_images" in text
    assert '"reference_capture_on_parse_failure": true' in text
    assert '"training_mode_enabled": true' in text
    assert '"training_capture_interval_minutes": 60' in text
    assert '"validate_capabilities_enabled": true' in text
    assert '"reference_offload_enabled": true' in text
    assert '"reference_offload_interval_minutes": 20' in text
    assert '"reference_offload_batch_size": 40' in text
    assert '"setup_state_version": 1' in text
    assert '"saved_by_software_version"' in text



def test_apply_setup_rejects_short_password(tmp_path: Path) -> None:
    svc = ProvisioningService(state_file=tmp_path / "device_setup.json")
    try:
        svc.apply_setup(
            SetupRequest(
                wifi_ssid="HomeWiFi",
                wifi_password="short",
                thermostat_profile_id="midea_kjr_12b_dp_t",
                camera_enabled=False,
            )
        )
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "wifi_password" in str(ex)


def test_apply_setup_rejects_empty_device_name(tmp_path: Path) -> None:
    svc = ProvisioningService(state_file=tmp_path / "device_setup.json")
    try:
        svc.apply_setup(
            SetupRequest(
                device_name="  ",
                wifi_ssid="HomeWiFi",
                wifi_password="supersecret",
                thermostat_profile_id="midea_kjr_12b_dp_t",
                camera_enabled=False,
            )
        )
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "device_name" in str(ex)


def test_apply_setup_wifi_verification_failure(tmp_path: Path) -> None:
    class AlwaysFailWifiConfigurator:
        def connect_to_home_wifi(self, ssid: str, password: str) -> bool:  # noqa: ARG002
            return False

    svc = ProvisioningService(
        state_file=tmp_path / "device_setup.json",
        wifi_configurator=AlwaysFailWifiConfigurator(),
    )
    result = svc.apply_setup(
        SetupRequest(
            wifi_ssid="HomeWiFi",
            wifi_password="supersecret",
            thermostat_profile_id="midea_kjr_12b_dp_t",
            camera_enabled=False,
        )
    )
    assert result.ok is False
    assert "Wi-Fi verification failed" in result.message


def test_apply_setup_rejects_invalid_daily_time(tmp_path: Path) -> None:
    svc = ProvisioningService(state_file=tmp_path / "device_setup.json")
    try:
        svc.apply_setup(
            SetupRequest(
                wifi_ssid="HomeWiFi",
                wifi_password="supersecret",
                thermostat_profile_id="midea_kjr_12b_dp_t",
                camera_enabled=False,
                daily_on_time="25:00",
            )
        )
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "daily_on_time" in str(ex)


def test_apply_setup_rejects_out_of_range_temperature(tmp_path: Path) -> None:
    svc = ProvisioningService(state_file=tmp_path / "device_setup.json")
    try:
        svc.apply_setup(
            SetupRequest(
                wifi_ssid="HomeWiFi",
                wifi_password="supersecret",
                thermostat_profile_id="midea_kjr_12b_dp_t",
                camera_enabled=False,
                target_temperature_c=35.0,
            )
        )
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "target_temperature_c" in str(ex)


def test_apply_setup_rejects_invalid_temperature_unit(tmp_path: Path) -> None:
    svc = ProvisioningService(state_file=tmp_path / "device_setup.json")
    try:
        svc.apply_setup(
            SetupRequest(
                wifi_ssid="HomeWiFi",
                wifi_password="supersecret",
                thermostat_profile_id="midea_kjr_12b_dp_t",
                camera_enabled=False,
                thermostat_temperature_unit="K",
            )
        )
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "thermostat_temperature_unit" in str(ex)


def test_apply_setup_rejects_invalid_active_days(tmp_path: Path) -> None:
    svc = ProvisioningService(state_file=tmp_path / "device_setup.json")
    try:
        svc.apply_setup(
            SetupRequest(
                wifi_ssid="HomeWiFi",
                wifi_password="supersecret",
                thermostat_profile_id="midea_kjr_12b_dp_t",
                camera_enabled=False,
                active_days=["mon", "funday"],
            )
        )
        assert False, "expected ValueError"
    except ValueError as ex:
        assert "active_days" in str(ex)
