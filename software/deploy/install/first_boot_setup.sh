#!/usr/bin/env bash
set -euo pipefail

# First-boot setup for SmartBlaster on Raspberry Pi OS Lite.
#
# This script:
# - installs base OS packages
# - syncs software to /opt/smartblaster/software
# - creates Python virtualenv and installs app
# - installs vision stack (OpenCV/Tesseract/TFLite best-effort)
# - installs and enables systemd service
#
# Usage:
#   sudo ./deploy/install/first_boot_setup.sh

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root (sudo)."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_ROOT="/opt/smartblaster/software"

if [[ ! -f "$REPO_ROOT/pyproject.toml" ]]; then
  echo "Could not find pyproject.toml from $REPO_ROOT"
  exit 1
fi

echo "[first-boot] Installing base OS packages..."
apt-get update
apt-get install -y --no-install-recommends \
  git \
  curl \
  ca-certificates \
  rsync \
  sudo \
  python3 \
  python3-venv \
  python3-pip \
  python3-dev \
  build-essential \
  libcamera0.7 \
  python3-libcamera \
  python3-picamera2 \
  network-manager \
  dnsmasq \
  hostapd \
  iproute2

echo "[first-boot] Syncing software to $TARGET_ROOT ..."
install -d -m 0755 /opt/smartblaster
install -d -m 0755 "$TARGET_ROOT"
rsync -a --delete --exclude ".venv" --exclude ".pytest_cache" "$REPO_ROOT/" "$TARGET_ROOT/"

echo "[first-boot] Creating Python virtualenv..."
python3 -m venv "$TARGET_ROOT/.venv"
"$TARGET_ROOT/.venv/bin/pip" install --upgrade pip setuptools wheel
"$TARGET_ROOT/.venv/bin/pip" install -e "$TARGET_ROOT"

echo "[first-boot] Installing vision dependency stack..."
SMARTBLASTER_VENV="$TARGET_ROOT/.venv" "$TARGET_ROOT/deploy/install/install_vision_stack.sh"

echo "[first-boot] Installing and starting smartblaster.service..."
"$TARGET_ROOT/deploy/install/install_service.sh"

echo "[first-boot] Complete."
echo "Check service status with: systemctl status smartblaster.service"
