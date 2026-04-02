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
tail -f upgrade.log

2. Update packages:

```bash
sudo apt-get update
sudo apt-get -y upgrade | tee upgrade.log
# Note that the upgrade step reboots processes and will break your remote connect.  So we tee it to a log file and monitor the output after reconnecting
tail -f upgrade.log
# once the upgrade finally finishes we can move on
sudo apt install git -y
sudo reboot
```

3. After reboot, set timezone and locale if needed:

```bash
sudo raspi-config
```

## 3. Copy SmartBlaster Software

1. Copy repo to Pi (or clone):

```bash
git clone https://github.com/LarryMorris1964/SmartBlaster.git ~/SmartBlaster
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
- https://www.xda-developers.com/how-to-ssh-into-raspberry-pi/ set up SSH access
- Handy tools for copying files, etc
	- Putty is an all-in-one tool for Pi https://www.circuitbasics.com/use-putty-to-access-the-raspberry-pi-terminal-from-a-computer/ 
	- FileZilla makes transfer easy https://filezilla-project.org/
	- WinSCP is another nice alternative
- then configure Pi Connect https://connect.raspberrypi.com/devices 

- SmartBlaster uses FastAPI + camera/IR services and does not require desktop UI.
- `tflite-runtime` installation is best-effort because wheel availability depends on Python version and architecture.
- First boot still enters setup mode until setup state is saved; Wi-Fi connectivity alone does not skip setup.

**WiFi Setup Info:**
The default WiFi SSID for setup is `SmartBlaster-SETUP` and the default password is `smartblast-setup` (see `deploy/ap/hostapd.conf`).
When connecting to the SmartBlaster-SETUP WiFi network, use this password unless you have customized it in the configuration file.

**Accessing the Captive Portal:**
After connecting to the SmartBlaster-SETUP WiFi, open a browser and go to:

	http://192.168.4.1:8080

This will bring up the SmartBlaster setup portal to complete device configuration.


## 7. Routine Update Workflow (After Initial Install)

Use this for normal code changes so you do not need a long manual sequence each time:

```bash
cd ~/SmartBlaster/software
./deploy.sh
```

What this does:

- Pulls latest code with fast-forward only.
- Ensures the service venv exists.
- Reinstalls SmartBlaster package and dependencies into that venv.
- Reinstalls systemd unit from repo, reloads daemon, and restarts service.

Use deeper recovery steps only if this one-command flow fails.
