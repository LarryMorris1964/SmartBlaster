#!/bin/bash
set -e

# Change to the project directory
cd "$(dirname "$0")"

echo "Pulling latest code..."
git pull

# Set up venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Optional: Restart systemd service if it exists
if systemctl list-units --full -all | grep -q "smartblaster.service"; then
  echo "Restarting smartblaster.service..."
  sudo systemctl restart smartblaster.service
else
  echo "smartblaster.service not found. Skipping service restart."
fi

# Optional: Uncomment to reboot instead of just restarting the service
# echo "Rebooting system..."
# sudo reboot

echo "Deploy complete."
