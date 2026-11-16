#!/usr/bin/env bash
# Installs the timer that writes the GRUB default kernel to /run/kernel-default, so the bot can warn when a
# newly installed kernel would boot next. Run with sudo.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

install -m 644 homelab-kernel-default.service homelab-kernel-default.timer /etc/systemd/system/
restorecon /etc/systemd/system/homelab-kernel-default.service /etc/systemd/system/homelab-kernel-default.timer

systemctl daemon-reload
systemctl enable --now homelab-kernel-default.timer
systemctl start homelab-kernel-default.service
echo "Default kernel: $(cat /run/kernel-default)"
