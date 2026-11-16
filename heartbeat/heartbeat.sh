#!/bin/bash
# Dead-man's switch: ping healthchecks.io every 5 minutes. If the PC freezes, loses power or
# loses internet, the pings stop and healthchecks.io alerts Discord from outside.
# URL lives in ~/homelab/alerts.env as HEARTBEAT_URL (secret, not in git).
HEARTBEAT_URL=$(grep -oP '^HEARTBEAT_URL=\K.*' "$HOME/homelab/alerts.env")
[ -n "$HEARTBEAT_URL" ] || exit 0   # not set up yet
# Each ping that gets through is timestamped so the bot can raise a problem when they stop (collect.py)
curl -fsS -m 10 --retry 3 -o /dev/null "$HEARTBEAT_URL" || exit 1
mkdir -p "$HOME/.local/state" && date +%s > "$HOME/.local/state/homelab-heartbeat"
