#!/usr/bin/env bash
set -euo pipefail

# Install vision/runtime dependencies needed by SmartBlaster camera parsing.
# Targets Raspberry Pi OS Lite (Bookworm/Bullseye).
#
# Installs:
# - OpenCV (system package)
# - Tesseract OCR binary and dev headers
# - Python bindings/utilities (pytesseract)
# - TFLite runtime (best-effort)
#
# Usage:
#   sudo ./deploy/install/install_vision_stack.sh
#   sudo SMARTBLASTER_VENV=/opt/smartblaster/software/.venv ./deploy/install/install_vision_stack.sh

SMARTBLASTER_VENV="${SMARTBLASTER_VENV:-/opt/smartblaster/software/.venv}"

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root (sudo)."
  exit 1
fi

if [[ ! -d "$SMARTBLASTER_VENV" ]]; then
  echo "Python venv not found: $SMARTBLASTER_VENV"
  echo "Create it first (for example in first_boot_setup.sh)."
  exit 1
fi

echo "[vision] Installing apt packages..."
apt-get update
apt-get install -y --no-install-recommends \
  python3-opencv \
  opencv-data \
  tesseract-ocr \
  libtesseract-dev \
  libleptonica-dev \
  libopenblas-dev

echo "[vision] Installing Python packages into venv..."
"$SMARTBLASTER_VENV/bin/pip" install --upgrade pip
"$SMARTBLASTER_VENV/bin/pip" install pytesseract

# TFLite wheel availability can vary by Python version and architecture.
# We install best-effort and do not fail the script if a wheel is unavailable.
echo "[vision] Installing tflite-runtime (best-effort)..."
if "$SMARTBLASTER_VENV/bin/pip" install tflite-runtime; then
  echo "[vision] tflite-runtime installed."
else
  echo "[vision] WARNING: tflite-runtime wheel unavailable for this platform/Python."
  echo "[vision] You can continue without it for now and swap interpreter version later if needed."
fi

echo "[vision] Done."
