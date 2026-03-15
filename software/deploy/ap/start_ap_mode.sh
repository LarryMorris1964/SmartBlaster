#!/usr/bin/env bash
set -euo pipefail

# Requires root. Adjust paths/interface as needed.
WLAN_IFACE="${WLAN_IFACE:-wlan0}"
HOSTAPD_CONF="${HOSTAPD_CONF:-/opt/smartblaster/software/deploy/ap/hostapd.conf}"
DNSMASQ_CONF="${DNSMASQ_CONF:-/opt/smartblaster/software/deploy/ap/dnsmasq.conf}"

ip link set "$WLAN_IFACE" down || true
ip addr flush dev "$WLAN_IFACE" || true
ip addr add 192.168.4.1/24 dev "$WLAN_IFACE"
ip link set "$WLAN_IFACE" up

# Stop NetworkManager on AP iface if needed
nmcli radio wifi on || true

pkill hostapd || true
pkill dnsmasq || true

hostapd "$HOSTAPD_CONF" -B

dnsmasq --conf-file="$DNSMASQ_CONF"

echo "AP mode started on $WLAN_IFACE"
