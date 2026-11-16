#!/usr/bin/env bash
# Installs the snapshot-before-offline-update hook (README › Updates), then takes one test snapshot so the
# GRUB entry can be checked. Run with sudo.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

install -m 755 homelab-update-snapshot.sh /usr/local/bin/homelab-update-snapshot
install -m 644 homelab-update-snapshot.service /etc/systemd/system/
restorecon /usr/local/bin/homelab-update-snapshot /etc/systemd/system/homelab-update-snapshot.service
systemctl daemon-reload
systemctl enable homelab-update-snapshot.service

# locate shouldn't index every snapshot as a second copy of /
grep -q '/\.snapshots' /etc/updatedb.conf || sed -i 's#^PRUNEPATHS = "\(.*\)"#PRUNEPATHS = "\1 /.snapshots"#' /etc/updatedb.conf

echo "--- test snapshot"
/usr/local/bin/homelab-update-snapshot --test
echo "--- boot entries"
cat /boot/loader/entries/homelab-pre-update-*.conf
echo "--- default kernel (must be unchanged): $(grubby --default-kernel)"
