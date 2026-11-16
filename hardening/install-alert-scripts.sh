#!/usr/bin/env bash
# Install the SMART and scrub checks from the repo into /usr/local/bin (they run as root from systemd).
# Run: sudo ~/homelab/hardening/install-alert-scripts.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run with sudo"; exit 1; }
H=/home/shanerunham/homelab
install -m 755 "$H/hardening/homelab-smart-check.sh" /usr/local/bin/homelab-smart-check
install -m 755 "$H/scrub/homelab-scrub.sh" /usr/local/bin/homelab-scrub
restorecon /usr/local/bin/homelab-smart-check /usr/local/bin/homelab-scrub 2>/dev/null || true
echo "Installed. Checking the disks (no Discord post unless there's a real problem)..."
/usr/local/bin/homelab-smart-check
