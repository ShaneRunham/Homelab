#!/usr/bin/env bash
# Push ~/homelab/jellyfin/custom.css into Jellyfin's Custom CSS (Dashboard > General). Needs JELLYFIN_API_KEY in ~/homelab/.env.
# Undo: ./apply-css.sh --clear
set -euo pipefail
cd "$(dirname "$0")"
KEY=$(grep -m1 '^JELLYFIN_API_KEY=' ../.env | cut -d= -f2-)
css=$([ "${1:-}" = --clear ] && echo "" || cat custom.css)
python3 - "$KEY" "$css" <<'EOF'
import json, sys, urllib.request
key, css = sys.argv[1], sys.argv[2]
url = "http://127.0.0.1:8096/System/Configuration/branding"
h = {"X-Emby-Token": key, "Content-Type": "application/json"}
cfg = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h)))
cfg["CustomCss"] = css
urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(cfg).encode(), headers=h, method="POST"))
print("Custom CSS", "cleared" if not css else f"applied ({len(css)} chars)")
EOF
