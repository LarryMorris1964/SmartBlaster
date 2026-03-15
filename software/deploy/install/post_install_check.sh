#!/usr/bin/env bash
set -euo pipefail

# SmartBlaster post-install health checks
# Usage:
#   ./deploy/install/post_install_check.sh

SERVICE_NAME="${SERVICE_NAME:-smartblaster.service}"
SETUP_PORT="${SETUP_PORT:-8080}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-20}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[post-check] systemctl not found"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[post-check] curl not found"
  exit 1
fi

echo "[post-check] Checking service active state..."
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[post-check] Service is not active: $SERVICE_NAME"
  systemctl status "$SERVICE_NAME" --no-pager || true
  exit 1
fi

echo "[post-check] Waiting for health endpoint on :$SETUP_PORT ..."
start_ts=$(date +%s)
while true; do
  if curl -fsS "http://127.0.0.1:${SETUP_PORT}/health" >/dev/null 2>&1; then
    break
  fi

  now_ts=$(date +%s)
  if (( now_ts - start_ts >= TIMEOUT_SECONDS )); then
    echo "[post-check] Timed out waiting for http://127.0.0.1:${SETUP_PORT}/health"
    journalctl -u "$SERVICE_NAME" --no-pager -n 80 || true
    exit 1
  fi

  sleep 1
done

echo "[post-check] PASSED"
