#!/bin/bash
# Removes the doorbell rule added by doorbell-firewall.sh (cameras were not tied in after all, 2026-11-11).
set -euo pipefail
firewall-cmd --permanent --zone=FedoraWorkstation --remove-rich-rule='rule family="ipv4" source address="192.168.0.49" port port="20005" protocol="udp" accept'
firewall-cmd --reload
rm -rf /home/shanerunham/homelab/home-assistant/config/custom_components   # root-owned cache left by the camera add-on
firewall-cmd --zone=FedoraWorkstation --list-rich-rules
