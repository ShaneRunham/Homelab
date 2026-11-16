#!/usr/bin/env bash
# Opens Jellyfin's port to the LAN so smart TV / console / tablet apps can reach it directly
# (they aren't on the tailnet). Run with sudo.
set -euo pipefail

zone=FedoraWorkstation
firewall-cmd --permanent --zone="$zone" --add-port=8096/tcp
firewall-cmd --reload
firewall-cmd --zone="$zone" --list-ports

echo "Done. Jellyfin reachable at http://192.168.0.10:8096"
