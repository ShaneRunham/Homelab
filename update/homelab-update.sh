#!/usr/bin/env bash
# Pulls newer images within the major versions set in compose.yaml and recreates any changed containers.
set -euo pipefail

# Report the result to the Uptime Kuma push monitor, which alerts on "down" or on no report for a day.
UPDATE_PUSH_URL=''
[ -r /home/shanerunham/homelab/alerts.env ] && . /home/shanerunham/homelab/alerts.env
push() {
  [ -n "$UPDATE_PUSH_URL" ] || return 0
  curl -fsS -m 10 --retry 12 --retry-delay 5 --retry-all-errors -o /dev/null -G "$UPDATE_PUSH_URL" \
    --data-urlencode "status=$1" --data-urlencode "msg=$2" || true
}
trap 'push down "Update failed at line $LINENO"' ERR

cd /home/shanerunham/homelab
# Registries have brief outages (lscr.io timeout 2026-11-07, ghcr.io 401 2026-11-10): retry before failing.
for try in 1 2 3 4; do
  # --ignore-buildable: nxapi is built locally (nxapi:local), there's nothing to pull for it (failed 2026-11-17)
  docker compose pull --quiet --ignore-buildable && break
  [ "$try" -eq 4 ] && { echo "Image pull failed 4 times"; false; }
  echo "Pull failed (try $try), retrying in $((try * 60))s"
  sleep $((try * 60))
done
docker compose up -d --remove-orphans
docker image prune -f >/dev/null

echo "Update check finished"
push up "Update check finished"
