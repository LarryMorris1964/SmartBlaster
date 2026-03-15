from smartblaster.bootstrap import _resolve_mode


def test_resolve_mode_setup_explicit() -> None:
    assert _resolve_mode("setup", state_exists=True) == "setup"
