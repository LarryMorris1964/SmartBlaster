#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CODE_ROOT="/home/pi/SmartBlaster/software"
SERVICE_NAME="smartblaster"
TAGS=("0.1.3" "0.1.4")
UPDATE_REPO="${SMARTBLASTER_UPDATE_REPO:-LarryMorris1964/SmartBlaster}"
PY="$CODE_ROOT/.venv/bin/python3"

cd "$REPO_DIR"

if [ ! -x "$PY" ]; then
    echo "[tag-test] Creating service venv"
    python3 -m venv --copies "$CODE_ROOT/.venv"
fi

echo "[tag-test] Preparing pip in service venv"
"$PY" -m pip install --upgrade pip setuptools wheel

for TAG in "${TAGS[@]}"; do
    echo ""
    echo "[tag-test] ===== Testing tag $TAG ====="

    echo "[tag-test] Installing software from GitHub tag via pip"
    "$PY" -m pip install --upgrade "git+https://github.com/${UPDATE_REPO}.git@${TAG}#subdirectory=software"

    sudo systemctl reset-failed "$SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME"

    sleep 2

    echo "[tag-test] Service status for $TAG"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l || true

    echo "[tag-test] Health checks for $TAG"
    curl -fsS http://127.0.0.1:8080/health && echo "[tag-test] localhost health OK" || echo "[tag-test] localhost health FAILED"
    curl -fsS http://192.168.4.1:8080/health && echo "[tag-test] AP health OK" || echo "[tag-test] AP health FAILED"

    echo "[tag-test] Recent logs for $TAG"
    journalctl -u "$SERVICE_NAME" -n 40 --no-pager -l || true
done

echo "[tag-test] Done"
