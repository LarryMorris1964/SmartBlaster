# Troubleshooting

## Camera not detected
- Run `rpicam-hello` to verify camera is recognised by the OS
- Check CSI ribbon cable is fully seated and the locking tab is closed
- Ensure `camera_auto_detect=1` is set in `/boot/firmware/config.txt`

## IR not responding
- Verify wiring against [wiring.md](wiring.md)
- Test IR LED with a phone camera (should glow purple when active)
- Check GPIO pin assignments match `src/main.py` configuration

## Software won't start
- Confirm virtual environment is activated and `requirements.txt` is installed
- Check Python version: requires Python 3.9+
- Run `python src/main.py` directly to see stack traces

## Pi won't boot
- Re-flash SD card with latest Raspberry Pi OS (64-bit Lite recommended)
- Ensure power supply provides ≥3A
