import subprocess

from smartblaster.provisioning.update import GitHubAppUpdater


def test_update_status_disabled_without_repo() -> None:
    updater = GitHubAppUpdater(repo="", current_version="0.1.0")

    status = updater.status()

    assert status.enabled is False
    assert status.update_available is False
    assert status.latest_version is None


def test_update_status_detects_newer_release() -> None:
    def fake_fetch_json(_url: str) -> dict[str, object]:
        return {
            "tag_name": "v0.2.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v0.2.0",
        }

    updater = GitHubAppUpdater(repo="owner/repo", current_version="0.1.0", fetch_json=fake_fetch_json)

    status = updater.status()

    assert status.enabled is True
    assert status.latest_version == "v0.2.0"
    assert status.update_available is True


def test_apply_update_runs_pip_install() -> None:
    commands: list[list[str]] = []

    def fake_fetch_json(_url: str) -> dict[str, object]:
        return {
            "tag_name": "v0.2.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v0.2.0",
        }

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    updater = GitHubAppUpdater(
        repo="owner/repo",
        current_version="0.1.0",
        fetch_json=fake_fetch_json,
        run_command=fake_run,
    )

    result = updater.apply()

    assert result.ok is True
    assert result.restart_required is True
    assert commands
    assert "git+https://github.com/owner/repo.git@v0.2.0" in commands[0][-1]


def test_apply_update_fails_when_disabled() -> None:
    updater = GitHubAppUpdater(repo="", current_version="0.1.0")

    result = updater.apply()

    assert result.ok is False
    assert "disabled" in result.message.lower()
