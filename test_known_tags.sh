#!/bin/bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CODE_ROOT="/home/pi/SmartBlaster/software"
SERVICE_NAME="smartblaster"
TAGS=("0.1.3" "0.1.4")

cd "$REPO_DIR"

echo "[tag-test] Fetching tags"
git fetch origin --tags

echo "[tag-test] Stashing local changes (if any)"
git stash push -u -m "before-known-tag-test" >/dev/null 2>&1 || true

for TAG in "${TAGS[@]}"; do
    echo ""
    echo "[tag-test] ===== Testing tag $TAG ====="

    git checkout --detach "tags/$TAG"

    python3 -m venv --copies "$CODE_ROOT/.venv"
    "$CODE_ROOT/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
    "$CODE_ROOT/.venv/bin/pip" install -r "$CODE_ROOT/requirements.txt"
    "$CODE_ROOT/.venv/bin/pip" install -e "$CODE_ROOT"

    sudo cp "$CODE_ROOT/deploy/systemd/smartblaster.service" /etc/systemd/system/smartblaster.service
    sudo systemctl daemon-reload
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

echo ""
echo "[tag-test] Restoring master"
git checkout master
git reset --hard origin/master

echo "[tag-test] Done"
