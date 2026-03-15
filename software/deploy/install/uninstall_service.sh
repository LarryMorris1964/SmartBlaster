#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="smartblaster.service"
UNIT_DST="/etc/systemd/system/$SERVICE_NAME"
SUDOERS_DST="/etc/sudoers.d/smartblaster-apmode"

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root (sudo)."
  exit 1
fi

echo "Stopping and disabling service (if installed)..."
systemctl stop "$SERVICE_NAME" || true
systemctl disable "$SERVICE_NAME" || true

if [[ -f "$UNIT_DST" ]]; then
  rm -f "$UNIT_DST"
fi

if [[ -f "$SUDOERS_DST" ]]; then
  rm -f "$SUDOERS_DST"
fi

systemctl daemon-reload

echo "Uninstall complete."
