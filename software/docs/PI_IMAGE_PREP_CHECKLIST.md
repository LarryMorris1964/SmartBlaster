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

**Important:**
Before running the first-boot setup, ensure your country code is set for Wi-Fi regulatory domain. If not already set, run:

```bash
echo 'country=US' | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf
sudo iw reg set US
```
Replace `US` with your country code if needed. This is required for AP mode to function.

5. Write image and safely eject SD card.

## 2.1. Update System Default Repo (OEM/Fork Guidance)

By default, SmartBlaster devices check for updates from the OEM repo:

	LarryMorris1964/SmartBlaster

To use your own update repo (for forks/derivatives), set the environment variable in your systemd service or shell:

```bash
export SMARTBLASTER_UPDATE_REPO="LarryMorris1964/SmartBlaster"
```
Or edit the systemd service file to add:
```
Environment=SMARTBLASTER_UPDATE_REPO=yourusername/yourrepo
```
This will override the default and enable updates from your own repo.

## 2. First Boot OS Hardening and Updates

7. Configure static IP for wlan0:

Add the following to the end of /etc/dhcpcd.conf (for copy-paste):

```bash
echo -e '\ninterface wlan0\n    static ip_address=192.168.4.1/24\n    nohook wpa_supplicant' | sudo tee -a /etc/dhcpcd.conf
```

This ensures wlan0 always has the correct static IP for AP mode. The install script should add this automatically, but verify if you have issues with DHCP or client connections.

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

# Copy SmartBlaster Software (must be done before any file copy/config steps)
```bash
git clone https://github.com/LarryMorris1964/SmartBlaster.git ~/SmartBlaster
cd ~/SmartBlaster/software
```


3. Install and configure hostapd (for Wi-Fi AP mode):

```bash
sudo apt-get install -y hostapd
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo cp ~/SmartBlaster/software/deploy/ap/hostapd.conf /etc/hostapd/hostapd.conf
```


5. Install and configure dnsmasq (for DHCP on AP):

```bash
sudo cp ~/SmartBlaster/software/deploy/ap/dnsmasq.conf /etc/dnsmasq.conf
```

This ensures dnsmasq is configured to provide DHCP to WiFi clients on future setups.

This ensures hostapd is installed, enabled, and configured for AP mode on future setups.

4. Unblock Wi-Fi interface (rfkill):

```bash
sudo rfkill unblock wlan
rfkill list
# Confirm 'Soft blocked: no' for your WiFi device
```

This ensures the WiFi interface is not blocked by software, which is required for AP mode to function.


6. Ensure WiFi stays unblocked after reboot:

Add the following line to /etc/rc.local before 'exit 0' (for copy-paste):

```bash
sudo touch /etc/rc.local
sudo chmod +x /etc/rc.local
sudo sed -i '/^exit 0/i rfkill unblock wlan' /etc/rc.local
```

This will keep WiFi unblocked on every boot. (The install script should add this automatically, but verify if you have issues with WiFi being soft blocked after reboot.)

3. After reboot, set timezone and locale if needed:
# Commenting out for now, since we should have taken care of all this above
# sudo raspi-config
```


## 3. Run SmartBlaster First-Boot Setup

```bash
sudo bash ./deploy/install/first_boot_setup.sh
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
- I use WinSCP for rapid file transfer during development

**WiFi Setup Info:**
The default WiFi SSID for setup is `SmartBlaster-SETUP` and the default password is `smartblast-setup` (see `deploy/ap/hostapd.conf`).
When connecting to the SmartBlaster-SETUP WiFi network, use this password unless you have customized it in the configuration file.

**Accessing the Captive Portal:**
After connecting to the SmartBlaster-SETUP WiFi, open a browser and go to:

	http://192.168.4.1:8080

This will bring up the SmartBlaster setup portal to complete device configuration.

---


## 7. Updating SmartBlaster Software on Raspberry Pi (Versioned Release Workflow)

To update SmartBlaster on your Raspberry Pi using a versioned release (recommended for production and field devices):

### A. On your development machine (create and push a version tag)

1. Commit and push all changes to the main repository:

	```bash
	git add .
	git commit -m "your message"
	git push
	```

2. Create a new version tag (replace v1.2.3 with your version):

	```bash
	git tag v1.2.3
	git push origin v1.2.3
	```

### B. On the Raspberry Pi (update to the new version)

1. SSH into your Pi and go to the software directory:

	```bash
	ssh pi@<your-pi-hostname>
	cd /opt/smartblaster/software
	```

2. Fetch tags and checkout the new version:

	```bash
	sudo git fetch --tags
	sudo git checkout v1.2.3
	```

3. (Recommended) Update Python dependencies in the virtual environment:

	```bash
	source .venv/bin/activate
	pip install --upgrade pip setuptools wheel
	pip install -e .
	deactivate
	```

4. Restart the SmartBlaster service to apply the update:

	```bash
	sudo systemctl restart smartblaster.service
	```

5. Check service and health endpoint:

	```bash
	systemctl status smartblaster.service
	curl -fsS http://127.0.0.1:8080/health
	```

If you encounter issues, review logs with:

```bash
journalctl -u smartblaster.service -n 100 --no-pager
```

This versioned workflow ensures only tested, tagged releases are deployed to devices. For development, you may still use branch-based updates, but tags are recommended for all production/field updates.


