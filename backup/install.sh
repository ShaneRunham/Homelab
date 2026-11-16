#!/usr/bin/env bash
# Installs the backup job, enables the daily timer and runs the first backup. Run with sudo.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

install -m 755 homelab-backup.sh /usr/local/bin/homelab-backup
install -m 644 homelab-backup.service homelab-backup.timer /etc/systemd/system/
restorecon /usr/local/bin/homelab-backup /etc/systemd/system/homelab-backup.service /etc/systemd/system/homelab-backup.timer

systemctl daemon-reload
systemctl enable --now homelab-backup.timer

echo "==> Running the first backup"
systemctl start homelab-backup.service
systemctl status homelab-backup.service --no-pager -l | tail -5 || true
ls -la /mnt/storage/backups/fedora
du -sh /mnt/storage/backups/fedora/latest/
systemctl list-timers homelab-backup.timer --no-pager
