#!/usr/bin/env bash
set -euo pipefail

WLAN_IFACE="${WLAN_IFACE:-wlan0}"

pkill hostapd || true
pkill dnsmasq || true

ip addr flush dev "$WLAN_IFACE" || true
ip link set "$WLAN_IFACE" down || true

# Let NetworkManager reacquire wifi control
nmcli networking on || true
nmcli radio wifi on || true

echo "AP mode stopped on $WLAN_IFACE"
