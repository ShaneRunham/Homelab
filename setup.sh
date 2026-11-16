#!/usr/bin/env bash
# Installs Tailscale, starts Homepage and Uptime Kuma, and publishes both to the tailnet.
# Historical: Homepage was removed 2026-11-14 (README › Dashboard); don't rerun as is.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

mkdir -p homepage/config uptime-kuma/data

echo "==> Installing Tailscale"
sudo curl -fsSL -o /etc/yum.repos.d/tailscale.repo https://pkgs.tailscale.com/stable/fedora/tailscale.repo
sudo dnf install -y tailscale
sudo systemctl enable --now tailscaled

echo "==> Starting Homepage and Uptime Kuma"
sudo docker compose up -d

echo "==> Signing in to Tailscale: open the link it prints"
sudo tailscale up --operator="$USER"

name=$(tailscale status --json | python3 -I -c 'import json,sys;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
echo "==> This PC is $name"

echo "HOMEPAGE_ALLOWED_HOSTS=127.0.0.1:3000,localhost:3000,$name" > .env
sed -i "s|href: http://127.0.0.1:3001|href: https://$name:8443|" homepage/config/services.yaml
sudo docker compose up -d

echo "==> Publishing to your tailnet. If it prints a link to enable HTTPS, open it and run this script's last two commands again"
tailscale serve --bg --https=443 http://127.0.0.1:3000
tailscale serve --bg --https=8443 http://127.0.0.1:3001

echo
echo "Done."
echo "Homepage:    https://$name"
echo "Uptime Kuma: https://$name:8443"
