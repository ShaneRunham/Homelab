#!/usr/bin/env bash
# Mirrors /mnt/storage across both drives, adds disk health alerts, installs the backup and update
# scripts with Uptime Kuma check-ins, and closes the open firewall port range. Run with sudo.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

echo "==> 1/4 Mirroring /mnt/storage data across both drives (RAID1)"
btrfs balance start -dconvert=raid1,soft /mnt/storage
btrfs filesystem df /mnt/storage
btrfs filesystem show /mnt/storage

echo "==> 2/4 Installing backup and update scripts with Uptime Kuma check-ins"
install -m 755 ../backup/homelab-backup.sh /usr/local/bin/homelab-backup
install -m 755 ../update/homelab-update.sh /usr/local/bin/homelab-update
restorecon /usr/local/bin/homelab-backup /usr/local/bin/homelab-update

echo "==> 3/4 Disk health: drive self-tests and Discord alerts"
install -m 755 homelab-smart-check.sh /usr/local/bin/homelab-smart-check
install -m 644 homelab-smart-check.service homelab-smart-check.timer /etc/systemd/system/
restorecon /usr/local/bin/homelab-smart-check /etc/systemd/system/homelab-smart-check.service /etc/systemd/system/homelab-smart-check.timer
conf=/etc/smartmontools/smartd.conf
[ -e "$conf.orig" ] || cp -a "$conf" "$conf.orig"
# Watch all attributes, run a short self-test daily at 02:00 and a long one on Saturdays at 01:00.
sed -i 's#^DEVICESCAN .*#DEVICESCAN -a -o on -S on -n standby,10,q -s (S/../.././02|L/../../6/01) -m root -M exec /usr/libexec/smartmontools/smartdnotify#' "$conf"
grep '^DEVICESCAN' "$conf"
systemctl restart smartd
systemctl daemon-reload
systemctl enable --now homelab-smart-check.timer
for dev in /dev/sda /dev/sdb /dev/sdc; do
  printf '%s: ' "$dev"; smartctl -H "$dev" | grep -iE 'result|status' || true
done
/usr/local/bin/homelab-smart-check --test && echo "Test message sent to Discord"
systemctl start homelab-smart-check.service || true
journalctl -u homelab-smart-check.service -n 3 --no-pager -o cat || true

echo "==> 4/4 Firewall"
echo "Port 27500 belongs to:"; ss -tlnpH 'sport = :27500' || true
zone=FedoraWorkstation
firewall-cmd --permanent --zone=trusted --add-interface=tailscale0
firewall-cmd --permanent --zone="$zone" --remove-port=1025-65535/tcp --remove-port=1025-65535/udp
firewall-cmd --permanent --zone="$zone" --remove-service=ssh
firewall-cmd --permanent --zone="$zone" --add-service=kdeconnect --add-service=steam-streaming --add-service=steam-lan-transfer
firewall-cmd --permanent --zone="$zone" --add-port=41641/udp
firewall-cmd --reload
firewall-cmd --get-active-zones
firewall-cmd --zone="$zone" --list-all

echo "==> Test runs"
systemctl start homelab-backup.service && echo "Backup OK"
systemctl start homelab-update.service && echo "Update OK"
systemctl list-timers 'homelab-*' --no-pager || true
