# Linux Service + AP Mode Setup

This is the first production-style deployment scaffold for Raspberry Pi.

## Systemd service
- Unit file: [software/deploy/systemd/smartblaster.service](../../software/deploy/systemd/smartblaster.service)
- Runs bootstrap command in `auto` mode.
- Uses setup state file: `/var/lib/smartblaster/device_setup.json`.

Recommended setup-mode command options (service or manual):
- `--enable-ap-mode`
- `--ap-use-sudo`
- `--ap-start-script /opt/smartblaster/software/deploy/ap/start_ap_mode.sh`
- `--ap-stop-script /opt/smartblaster/software/deploy/ap/stop_ap_mode.sh`

## Sudo hardening for AP scripts

Install restricted sudoers file:
- Source: [software/deploy/security/smartblaster-apmode.sudoers](../../software/deploy/security/smartblaster-apmode.sudoers)
- Destination: `/etc/sudoers.d/smartblaster-apmode`
- Permissions: `0440`

Validate syntax before enabling:
- `sudo visudo -cf /etc/sudoers.d/smartblaster-apmode`

## AP mode scripts
- Start AP: [software/deploy/ap/start_ap_mode.sh](../../software/deploy/ap/start_ap_mode.sh)
- Stop AP: [software/deploy/ap/stop_ap_mode.sh](../../software/deploy/ap/stop_ap_mode.sh)
- Configs:
  - [software/deploy/ap/hostapd.conf](../../software/deploy/ap/hostapd.conf)
  - [software/deploy/ap/dnsmasq.conf](../../software/deploy/ap/dnsmasq.conf)

## Install steps (Raspberry Pi)
1. Copy project to `/opt/smartblaster/software`
2. Create and activate virtualenv; install dependencies
3. Copy service unit to `/etc/systemd/system/smartblaster.service`
4. Enable service:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable smartblaster`
   - `sudo systemctl start smartblaster`

### Automated install (recommended)

Use the installer script:
- [software/deploy/install/install_service.sh](../../software/deploy/install/install_service.sh)
- Preflight checks: [software/deploy/install/preflight_check.sh](../../software/deploy/install/preflight_check.sh)
- Post-install checks: [software/deploy/install/post_install_check.sh](../../software/deploy/install/post_install_check.sh)

From `/opt/smartblaster/software`:
- `./deploy/install/preflight_check.sh`
- `sudo ./deploy/install/install_service.sh`
- `./deploy/install/post_install_check.sh`

Uninstall helper:
- [software/deploy/install/uninstall_service.sh](../../software/deploy/install/uninstall_service.sh)

## Notes
- AP scripts require root privileges.
- Tune interface names and conf paths per image.
- Recommended: a dedicated sudoers rule allowing only AP start/stop scripts.
