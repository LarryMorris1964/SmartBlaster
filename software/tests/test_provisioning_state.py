from pathlib import Path

from smartblaster.provisioning.state import (
    DEFAULT_DEVICE_NAME,
    SETUP_STATE_VERSION,
    load_setup_state,
    migrate_setup_state,
    persist_setup_state,
)


def test_migrate_setup_state_adds_version_defaults() -> None:
    migrated = migrate_setup_state({"wifi_ssid": "HomeWiFi"})

    assert migrated["setup_state_version"] == SETUP_STATE_VERSION
    assert migrated["config_schema_version"] >= 1
    assert migrated["device_name"] == DEFAULT_DEVICE_NAME
    assert "saved_by_software_version" in migrated


def test_load_setup_state_missing_file_returns_defaults(tmp_path: Path) -> None:
    state = load_setup_state(tmp_path / "missing.json")

    assert state["setup_state_version"] == SETUP_STATE_VERSION
    assert state["config_schema_version"] >= 1
    assert state["device_name"] == DEFAULT_DEVICE_NAME


def test_persist_setup_state_writes_metadata(tmp_path: Path) -> None:
    state_file = tmp_path / "device_setup.json"

    persist_setup_state(
        state_file,
        {
            "device_name": "Workshop SmartBlaster",
            "wifi_ssid": "HomeWiFi",
            "config_schema_version": 2,
        },
    )

    loaded = load_setup_state(state_file)
    assert loaded["device_name"] == "Workshop SmartBlaster"
    assert loaded["setup_state_version"] == SETUP_STATE_VERSION
    assert loaded["config_schema_version"] == 2
    assert "saved_by_software_version" in loaded
