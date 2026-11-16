#!/usr/bin/env bash
# Starts Speedtest Tracker and lets Govee LAN replies (UDP 4002) in from the home network. Run with sudo.
set -euo pipefail
cd /home/shanerunham/homelab
docker compose up -d speedtest-tracker
firewall-cmd --permanent --zone=FedoraWorkstation --add-port=4002/udp
firewall-cmd --reload
firewall-cmd --zone=FedoraWorkstation --list-ports
echo "Done. Tell Claude."
