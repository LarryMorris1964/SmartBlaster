echo "[first-boot] Checking Wi-Fi regulatory domain (country code)..."
COUNTRY_CODE="US"  # Change this if deploying outside the US
WPA_SUPPLICANT_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
if ! grep -q "^country=" "$WPA_SUPPLICANT_CONF" 2>/dev/null; then
  echo "country=$COUNTRY_CODE" | tee "$WPA_SUPPLICANT_CONF"
  iw reg set $COUNTRY_CODE
  echo "[first-boot] Set Wi-Fi country code to $COUNTRY_CODE."
else
  echo "[first-boot] Wi-Fi country code already set: $(grep '^country=' "$WPA_SUPPLICANT_CONF")"
fi
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

# Unblock WiFi in case rfkill is set (prevents AP mode failures)
rfkill unblock wifi || true

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
  libcap-dev \
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
SMARTBLASTER_VENV="$TARGET_ROOT/.venv" bash "$TARGET_ROOT/deploy/install/install_vision_stack.sh"

echo "[first-boot] Installing and starting smartblaster.service..."
bash "$TARGET_ROOT/deploy/install/install_service.sh"

# Ensure dnsmasq config is correct for AP mode
echo "[first-boot] Copying dnsmasq.conf for AP mode..."
cp "$TARGET_ROOT/deploy/ap/dnsmasq.conf" /etc/dnsmasq.conf


# Install and enable restart-dnsmasq-after-hostapd.service to ensure dnsmasq starts after hostapd
echo "[first-boot] Installing restart-dnsmasq-after-hostapd.service..."
cp "$TARGET_ROOT/deploy/install/restart-dnsmasq-after-hostapd.service" /etc/systemd/system/
systemctl enable restart-dnsmasq-after-hostapd.service


# Install and enable static-ip-wlan0.service to assign static IP to wlan0 for AP mode
echo "[first-boot] Installing static-ip-wlan0.service..."
cp "$TARGET_ROOT/deploy/install/static-ip-wlan0.service" /etc/systemd/system/
systemctl enable static-ip-wlan0.service

echo "[first-boot] Complete."
echo "Check service status with: systemctl status smartblaster.service"

# Ensure rfkill unblock wlan is present in rc.local to prevent WiFi soft block on reboot
RC_LOCAL=/etc/rc.local
if ! grep -q 'rfkill unblock wlan' "$RC_LOCAL" 2>/dev/null; then
  echo "[first-boot] Adding 'rfkill unblock wlan' to $RC_LOCAL ..."
  sudo sed -i '/^exit 0/i rfkill unblock wlan' "$RC_LOCAL"
fi

# Ensure static IP for wlan0 in /etc/dhcpcd.conf
DHCPCD_CONF=/etc/dhcpcd.conf
STATIC_IP_BLOCK="interface wlan0\n    static ip_address=192.168.4.1/24\n    nohook wpa_supplicant"
if ! grep -q 'static ip_address=192.168.4.1/24' "$DHCPCD_CONF" 2>/dev/null; then
  echo "[first-boot] Adding static IP for wlan0 to $DHCPCD_CONF ..."
  printf '\n%s\n' "$STATIC_IP_BLOCK" | sudo tee -a "$DHCPCD_CONF"
fi
