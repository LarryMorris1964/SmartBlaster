# Raspberry Pi Image Preparation Checklist

Target: Raspberry Pi OS Lite (64-bit)

## 1. Flash OS Image

1. Open Raspberry Pi Imager.
2. Choose OS: Raspberry Pi OS Lite (64-bit).
3. Choose your SD card.
4. In Advanced Options:
- Set hostname (example: `smartblaster-pi`)
- Enable SSH
- Set username/password
- Configure Wi-Fi country (required for AP/network tooling)
- Optionally preconfigure home Wi-Fi for first boot SSH access only (does not bypass SmartBlaster setup/calibration)
5. Write image and safely eject SD card.

## 2. First Boot OS Hardening and Updates

1. Boot Pi and SSH in.
2. Update packages:

```bash
sudo apt-get update
sudo apt-get -y upgrade
sudo reboot
```

3. After reboot, set timezone and locale if needed:

```bash
sudo raspi-config
```

## 3. Copy SmartBlaster Software

1. Copy repo to Pi (or clone):

```bash
git clone <your-smartblaster-repo-url> ~/SmartBlaster
cd ~/SmartBlaster/software
```

2. Run first-boot setup script:

```bash
sudo ./deploy/install/first_boot_setup.sh
```

This installs Python/runtime packages, vision stack, and systemd service.

## 4. Validate Install

1. Service should be active:

```bash
systemctl status smartblaster.service
```

2. Health endpoint should respond:

```bash
curl -fsS http://127.0.0.1:8080/health
```

3. Review logs:

```bash
journalctl -u smartblaster.service -n 100 --no-pager
```

4. AP/Wi-Fi sanity checks (recommended on first boot):

```bash
# Confirm Wi-Fi driver reports AP support
iw list | grep -A 10 "Supported interface modes"

# Confirm AP dependencies are present/running when setup mode is active
sudo systemctl status hostapd dnsmasq --no-pager

# If setup SSID is not visible on phone, inspect service logs again
sudo journalctl -u smartblaster.service -n 120 --no-pager
```

You should see `AP` listed in supported interface modes. If not, AP mode will not work reliably.

## 5. Files That Must Exist On Device

- Software root: `/opt/smartblaster/software`
- First-boot script: `/opt/smartblaster/software/deploy/install/first_boot_setup.sh`
- Vision package script: `/opt/smartblaster/software/deploy/install/install_vision_stack.sh`
- Service installer: `/opt/smartblaster/software/deploy/install/install_service.sh`
- Systemd unit file: `/opt/smartblaster/software/deploy/systemd/smartblaster.service`

## 6. Notes

- Pi OS Lite is sufficient for SmartBlaster.
- SmartBlaster uses FastAPI + camera/IR services and does not require desktop UI.
- `tflite-runtime` installation is best-effort because wheel availability depends on Python version and architecture.
- First boot still enters setup mode until setup state is saved; Wi-Fi connectivity alone does not skip setup.
