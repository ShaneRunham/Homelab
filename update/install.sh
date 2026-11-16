#!/usr/bin/env bash
# Installs the nightly update job, turns on Tailscale auto-updates and runs one update. Run with sudo.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

install -m 755 homelab-update.sh /usr/local/bin/homelab-update
install -m 644 homelab-update.service homelab-update.timer /etc/systemd/system/
restorecon /usr/local/bin/homelab-update /etc/systemd/system/homelab-update.service /etc/systemd/system/homelab-update.timer

systemctl daemon-reload
systemctl enable --now homelab-update.timer
tailscale set --auto-update

echo "==> Running the first update"
systemctl start homelab-update.service
journalctl -u homelab-update.service -n 5 --no-pager -o cat || true
docker ps --format '{{.Names}}  {{.Image}}  {{.Status}}' || true
systemctl list-timers homelab-update.timer --no-pager || true
