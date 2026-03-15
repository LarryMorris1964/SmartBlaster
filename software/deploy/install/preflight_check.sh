#!/usr/bin/env bash
set -euo pipefail

# SmartBlaster deployment preflight checks
# Usage:
#   ./deploy/install/preflight_check.sh

SRC_ROOT="${SRC_ROOT:-/opt/smartblaster/software}"
REQUIRED_CMDS=(systemctl visudo nmcli hostapd dnsmasq ip curl)
REQUIRED_FILES=(
  "$SRC_ROOT/deploy/systemd/smartblaster.service"
  "$SRC_ROOT/deploy/security/smartblaster-apmode.sudoers"
  "$SRC_ROOT/deploy/ap/start_ap_mode.sh"
  "$SRC_ROOT/deploy/ap/stop_ap_mode.sh"
)

FAILED=0

echo "[preflight] Checking required commands..."
for cmd in "${REQUIRED_CMDS[@]}"; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "  [ok] $cmd"
  else
    echo "  [missing] $cmd"
    FAILED=1
  fi
done

echo "[preflight] Checking required files..."
for path in "${REQUIRED_FILES[@]}"; do
  if [[ -f "$path" ]]; then
    echo "  [ok] $path"
  else
    echo "  [missing] $path"
    FAILED=1
  fi
done

if [[ $FAILED -ne 0 ]]; then
  echo "[preflight] FAILED - fix missing items before install."
  exit 1
fi

echo "[preflight] PASSED"
