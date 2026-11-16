#!/usr/bin/env bash
# Monthly btrfs scrub of the boot SSD (/ and /home) and the RAID1 backup pair. A scrub reads every block and
# checks it against its checksum; on RAID1 it repairs a bad copy from the good one. Posts to Discord on any error.
set -uo pipefail

DISCORD_WEBHOOK_URL=''
[ -r /home/shanerunham/homelab/alerts.env ] && . /home/shanerunham/homelab/alerts.env

send() {
  [ -n "$DISCORD_WEBHOOK_URL" ] || { echo "No Discord webhook in alerts.env" >&2; return 1; }
  local payload
  payload=$(python3 -c 'import json, sys; print(json.dumps({"content": sys.argv[1][:1900]}))' "$1")  # no @mention: the bot sees the failed run and HA alerts the phone; this post is the log
  curl -fsS -m 15 --retry 3 -o /dev/null -H 'Content-Type: application/json' -d "$payload" "$DISCORD_WEBHOOK_URL"
}

problems=()
for fs in / /mnt/storage; do
  mountpoint -q "$fs" || { problems+=("$fs is not mounted"); continue; }
  out=$(btrfs scrub start -B "$fs" 2>&1)
  status=$?
  echo "== $fs (exit $status)"; echo "$out"
  summary=$(grep -m1 'Error summary:' <<<"$out" | sed 's/^[[:space:]]*Error summary:[[:space:]]*//')
  # Exit 3 = uncorrectable errors; any other non-zero = the scrub couldn't run.
  if (( status != 0 )) || [ "$summary" != "no errors found" ]; then
    problems+=("$fs: scrub exit $status, ${summary:-no summary}")
  fi
done

if (( ${#problems[@]} )); then
  msg="Btrfs scrub warning on $(hostname):"$'\n'"$(printf -- '- %s\n' "${problems[@]}")"
  echo "$msg"
  send "$msg"
  exit 1
fi
echo "Scrub finished: no errors"
