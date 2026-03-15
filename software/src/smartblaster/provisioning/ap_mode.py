"""Access-point mode orchestration helpers for captive provisioning."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass
class ApModeController:
    """Starts/stops AP mode using external scripts.

    Scripts are intentionally external so deployments can tailor network interfaces
    and distro specifics without changing Python logic.
    """

    start_command: list[str]
    stop_command: list[str]

    def start(self) -> bool:
        return self._run(self.start_command)

    def stop(self) -> bool:
        return self._run(self.stop_command)

    @staticmethod
    def _run(command: list[str]) -> bool:
        try:
            proc = subprocess.run(command, check=False, capture_output=True, text=True)
        except FileNotFoundError:
            return False
        return proc.returncode == 0
