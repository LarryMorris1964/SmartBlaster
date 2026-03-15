"""Wi-Fi/AP orchestration abstractions for provisioning mode."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Protocol


class WifiConfigurator(Protocol):
    def connect_to_home_wifi(self, ssid: str, password: str) -> bool:
        ...


@dataclass
class NmcliWifiConfigurator:
    """NetworkManager-backed Wi-Fi connector for Raspberry Pi Linux images."""

    timeout_seconds: int = 20

    def connect_to_home_wifi(self, ssid: str, password: str) -> bool:
        cmd = [
            "nmcli",
            "device",
            "wifi",
            "connect",
            ssid,
            "password",
            password,
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

        return proc.returncode == 0


@dataclass
class AlwaysSuccessWifiConfigurator:
    """Development/testing connector stub."""

    def connect_to_home_wifi(self, ssid: str, password: str) -> bool:  # noqa: ARG002
        return True
