"""Primitive application update service backed by GitHub releases."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
import json
import re
import subprocess
import sys
from typing import Callable
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class UpdateStatus:
    enabled: bool
    repo: str
    current_version: str
    latest_version: str | None
    update_available: bool
    release_url: str | None
    error: str | None = None


@dataclass(frozen=True)
class UpdateApplyResult:
    ok: bool
    message: str
    command: str | None
    target_version: str | None
    restart_required: bool
    stdout: str | None = None
    stderr: str | None = None


def _current_version() -> str:
    try:
        return version("smartblaster")
    except PackageNotFoundError:
        return "dev"


def _parse_version_parts(value: str) -> tuple[int, ...]:
    normalized = value.strip().lstrip("vV")
    parts = [int(item) for item in re.findall(r"\d+", normalized)]
    return tuple(parts)


def _is_newer_version(latest: str, current: str) -> bool:
    latest_parts = _parse_version_parts(latest)
    current_parts = _parse_version_parts(current)
    if not latest_parts or not current_parts:
        return latest.strip() != current.strip()

    max_len = max(len(latest_parts), len(current_parts))
    left = latest_parts + (0,) * (max_len - len(latest_parts))
    right = current_parts + (0,) * (max_len - len(current_parts))
    return left > right


class GitHubAppUpdater:
    def __init__(
        self,
        *,
        repo: str,
        current_version: str | None = None,
        fetch_json: Callable[[str], dict[str, object]] | None = None,
        run_command: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.repo = repo.strip()
        self.current_version = current_version or _current_version()
        self._fetch_json = fetch_json or self._default_fetch_json
        self._run_command = run_command or self._default_run_command

    @classmethod
    def from_env(cls) -> "GitHubAppUpdater":
        import os

        repo = os.getenv("SMARTBLASTER_UPDATE_REPO", "")
        return cls(repo=repo)

    def status(self) -> UpdateStatus:
        if not self.repo:
            return UpdateStatus(
                enabled=False,
                repo="",
                current_version=self.current_version,
                latest_version=None,
                update_available=False,
                release_url=None,
                error=None,
            )

        try:
            payload = self._fetch_json(f"https://api.github.com/repos/{self.repo}/releases/latest")
            latest = str(payload.get("tag_name") or "").strip()
            release_url = str(payload.get("html_url") or "").strip() or None
            if not latest:
                return UpdateStatus(
                    enabled=True,
                    repo=self.repo,
                    current_version=self.current_version,
                    latest_version=None,
                    update_available=False,
                    release_url=release_url,
                    error="GitHub latest release did not include tag_name",
                )
            return UpdateStatus(
                enabled=True,
                repo=self.repo,
                current_version=self.current_version,
                latest_version=latest,
                update_available=_is_newer_version(latest, self.current_version),
                release_url=release_url,
                error=None,
            )
        except Exception as ex:
            return UpdateStatus(
                enabled=True,
                repo=self.repo,
                current_version=self.current_version,
                latest_version=None,
                update_available=False,
                release_url=None,
                error=str(ex),
            )

    def apply(self, target_version: str | None = None) -> UpdateApplyResult:
        current_status = self.status()
        if not current_status.enabled:
            return UpdateApplyResult(
                ok=False,
                message="App updates are disabled. Configure SMARTBLASTER_UPDATE_REPO to enable.",
                command=None,
                target_version=None,
                restart_required=False,
            )

        requested_target = target_version.strip() if isinstance(target_version, str) else ""
        final_target = requested_target or current_status.latest_version

        if not final_target:
            return UpdateApplyResult(
                ok=False,
                message="Unable to determine target version from GitHub.",
                command=None,
                target_version=None,
                restart_required=False,
            )

        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            f"git+https://github.com/{self.repo}.git@{final_target}",
        ]
        completed = self._run_command(command)
        ok = completed.returncode == 0
        message = "Update installed. Restart required." if ok else "Update failed. See stderr for details."
        return UpdateApplyResult(
            ok=ok,
            message=message,
            command=" ".join(command),
            target_version=final_target,
            restart_required=ok,
            stdout=(completed.stdout or "").strip() or None,
            stderr=(completed.stderr or "").strip() or None,
        )

    def _default_fetch_json(self, url: str) -> dict[str, object]:
        request = Request(url, headers={"User-Agent": "SmartBlaster-Updater/0.1"})
        with urlopen(request, timeout=10) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected GitHub response payload")
        return payload

    def _default_run_command(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, check=False)
