#!/usr/bin/env bash
# Lets this PC act as a Tailscale exit node (IPv4 forwarding is already on for Docker; IPv6 isn't).
# Run with sudo.
set -euo pipefail
printf 'net.ipv4.ip_forward = 1\nnet.ipv6.conf.all.forwarding = 1\n' > /etc/sysctl.d/99-tailscale-exit-node.conf
sysctl -p /etc/sysctl.d/99-tailscale-exit-node.conf
echo "Done. Tell Claude."
