#!/usr/bin/env bash
# Installs Sunshine (game and desktop streaming to Moonlight) from the LizardByte COPR and opens
# its streaming ports to the LAN. The web UI (47990) stays local and on the tailnet. Run with sudo.
set -euo pipefail

echo "==> 1/3 Installing Sunshine"
dnf -y copr enable lizardbyte/stable
dnf -y install Sunshine

echo "==> 2/3 Allowing screen capture (KMS) and controller/keyboard input"
setcap cap_sys_admin+p "$(readlink -f "$(command -v sunshine)")"
getcap "$(readlink -f "$(command -v sunshine)")"
udevadm control --reload-rules
udevadm trigger --sysname-match=uinput || true

echo "==> 3/3 Firewall: Moonlight streaming ports on the LAN"
zone=FedoraWorkstation
firewall-cmd --permanent --zone="$zone" --add-port=47984/tcp --add-port=47989/tcp --add-port=48010/tcp
firewall-cmd --permanent --zone="$zone" --add-port=47998-48000/udp
firewall-cmd --reload
firewall-cmd --zone="$zone" --list-ports

rpm -q Sunshine
echo "Done. Tell Claude, which will start the Sunshine user service."
