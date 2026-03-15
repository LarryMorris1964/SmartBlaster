from smartblaster.provisioning.ap_mode import ApModeController


def test_ap_mode_controller_missing_script_returns_false() -> None:
    ctrl = ApModeController(
        start_command=["/definitely/missing/start_ap_mode.sh"],
        stop_command=["/definitely/missing/stop_ap_mode.sh"],
    )
    assert ctrl.start() is False
    assert ctrl.stop() is False
