#!/usr/bin/env bash
# Keep the SATA links at full power: the boot SSD (sdb, ata5) logs "UnrecovData Handshk" link errors with link power
# saving on. The kernel arg ahci.mobile_lpm_policy=1 sets it at boot, but tuned's "balanced" profile switches it back
# to med_power_with_dipm, so KDE's Balanced now maps to balanced-sata (= balanced + alpm=max_performance).
# Run: sudo ~/homelab/hardening/install-sata-lpm.sh
# Undo: set "balanced=balanced" in /etc/tuned/ppd.conf, rm -r /etc/tuned/profiles/balanced-sata, restart tuned tuned-ppd
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run with sudo"; exit 1; }

mkdir -p /etc/tuned/profiles/balanced-sata
cat > /etc/tuned/profiles/balanced-sata/tuned.conf <<'EOF'
[main]
summary=balanced, with SATA link power saving off (boot SSD link errors, 2026-11-15)
include=balanced

[scsi_host]
alpm=max_performance
EOF
restorecon -R /etc/tuned/profiles/balanced-sata 2>/dev/null || true

sed -i 's/^balanced=balanced$/balanced=balanced-sata/' /etc/tuned/ppd.conf
systemctl restart tuned tuned-ppd
sleep 3

echo "tuned profile: $(tuned-adm active)"
for h in /sys/class/scsi_host/host*/link_power_management_policy; do echo "$h: $(cat "$h")"; done
