#!/usr/bin/env bash
set -euo pipefail

# SmartBlaster service installer for Raspberry Pi/Linux
# Usage:
#   sudo ./deploy/install/install_service.sh
#   sudo ./deploy/install/install_service.sh --skip-preflight
#   sudo ./deploy/install/install_service.sh --skip-post-check

SKIP_PREFLIGHT=false
SKIP_POST_CHECK=false
for arg in "$@"; do
  case "$arg" in
    --skip-preflight)
      SKIP_PREFLIGHT=true
      ;;
    --skip-post-check)
      SKIP_POST_CHECK=true
      ;;
  esac
done

SERVICE_NAME="smartblaster.service"
SRC_ROOT="/opt/smartblaster/software"
UNIT_SRC="$SRC_ROOT/deploy/systemd/$SERVICE_NAME"
UNIT_DST="/etc/systemd/system/$SERVICE_NAME"
SUDOERS_SRC="$SRC_ROOT/deploy/security/smartblaster-apmode.sudoers"
SUDOERS_DST="/etc/sudoers.d/smartblaster-apmode"
PREFLIGHT_SCRIPT="$SRC_ROOT/deploy/install/preflight_check.sh"
POST_CHECK_SCRIPT="$SRC_ROOT/deploy/install/post_install_check.sh"
STATE_DIR="/var/lib/smartblaster"
LOG_DIR="/var/log/smartblaster"

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root (sudo)."
  exit 1
fi

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "Missing unit file: $UNIT_SRC"
  exit 1
fi

if [[ ! -f "$SUDOERS_SRC" ]]; then
  echo "Missing sudoers file: $SUDOERS_SRC"
  exit 1
fi

if [[ "$SKIP_PREFLIGHT" == "false" ]]; then
  if [[ ! -f "$PREFLIGHT_SCRIPT" ]]; then
    echo "Preflight script missing: $PREFLIGHT_SCRIPT"
    echo "Run with --skip-preflight only if you understand the risks"
    exit 1
  fi

  echo "Running preflight checks..."
  SRC_ROOT="$SRC_ROOT" bash "$PREFLIGHT_SCRIPT"
fi

echo "Creating runtime directories..."
install -d -m 0755 "$STATE_DIR" "$LOG_DIR"

echo "Installing systemd unit..."
install -m 0644 "$UNIT_SRC" "$UNIT_DST"

echo "Installing sudoers policy..."
install -m 0440 "$SUDOERS_SRC" "$SUDOERS_DST"

# Validate sudoers syntax before enabling service.
visudo -cf "$SUDOERS_DST"

echo "Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

if [[ "$SKIP_POST_CHECK" == "false" ]]; then
  if [[ ! -f "$POST_CHECK_SCRIPT" ]]; then
    echo "Post-install check script missing: $POST_CHECK_SCRIPT"
    echo "Run with --skip-post-check only if you understand the risks"
    exit 1
  fi

  echo "Running post-install checks..."
  bash "$POST_CHECK_SCRIPT"
fi

echo "Done. Check status with:"
echo "  systemctl status $SERVICE_NAME"
