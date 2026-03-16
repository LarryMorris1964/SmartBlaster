"""System-level helpers for network probing and reboot requests."""

from __future__ import annotations

import os
import subprocess


def network_connected_best_effort() -> bool:
    """Best-effort NetworkManager state probe.

    If `nmcli` is unavailable or errors, do not block normal operation.
    """
    command = ["nmcli", "-t", "-f", "STATE", "general"]
    try:
        proc = subprocess.run(command, check=False, capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True

    if proc.returncode != 0:
        return True

    state = (proc.stdout or "").strip().lower()
    return state.startswith("connected")


def reboot_commands_from_env() -> list[list[str]]:
    """Build allowlisted reboot command attempts from env configuration."""
    mode = os.getenv("SMARTBLASTER_REBOOT_COMMAND", "auto").strip().lower()
    allowlist: dict[str, list[list[str]]] = {
        "auto": [["systemctl", "reboot"], ["reboot"]],
        "systemctl-reboot": [["systemctl", "reboot"]],
        "reboot": [["reboot"]],
        "sudo-reboot": [["sudo", "reboot"]],
        "none": [],
    }
    return allowlist.get(mode, allowlist["auto"])


def request_reboot() -> None:
    for command in reboot_commands_from_env():
        try:
            proc = subprocess.run(command, check=False, capture_output=True, text=True)
        except FileNotFoundError:
            continue
        if proc.returncode == 0:
            return
