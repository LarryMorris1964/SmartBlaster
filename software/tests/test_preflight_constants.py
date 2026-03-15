from pathlib import Path


def test_preflight_script_exists() -> None:
    path = Path("deploy/install/preflight_check.sh")
    assert path.exists()


def test_post_install_script_exists() -> None:
    path = Path("deploy/install/post_install_check.sh")
    assert path.exists()
