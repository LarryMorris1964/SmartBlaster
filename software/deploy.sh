#!/bin/bash
set -euo pipefail

SERVICE_NAME="smartblaster"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PY="$SCRIPT_DIR/.venv/bin/python"
UNIT_SRC="$SCRIPT_DIR/deploy/systemd/smartblaster.service"
UNIT_DST="/etc/systemd/system/smartblaster.service"

cd "$SCRIPT_DIR"

echo "[deploy] Pulling latest code..."
git pull --ff-only

if [ ! -x "$VENV_PY" ]; then
  echo "[deploy] Creating virtual environment..."
  python3 -m venv --copies "$SCRIPT_DIR/.venv"
fi

echo "[deploy] Installing package + dependencies into service venv..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel
"$VENV_PY" -m pip install --upgrade --force-reinstall -e "$SCRIPT_DIR"

if [ -f "$UNIT_SRC" ]; then
  echo "[deploy] Installing systemd unit..."
  sudo install -m 0644 "$UNIT_SRC" "$UNIT_DST"
  sudo sed -i 's/\r$//' "$UNIT_DST"
  sudo systemctl daemon-reload
fi

if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
  echo "[deploy] Restarting ${SERVICE_NAME}.service..."
  sudo systemctl reset-failed "${SERVICE_NAME}.service" || true
  sudo systemctl restart "${SERVICE_NAME}.service"
  sleep 2
  sudo systemctl status "${SERVICE_NAME}.service" --no-pager -l || true
else
  echo "[deploy] ${SERVICE_NAME}.service not installed. Skipping restart."
fi

echo "[deploy] Complete."
