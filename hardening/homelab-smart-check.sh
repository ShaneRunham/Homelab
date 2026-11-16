#!/usr/bin/env bash
# Daily disk health check. Posts to Discord when a drive fails its health check, has bad sectors,
# fails a self-test or can't be read. Run with --test to send a test message.
set -uo pipefail

DISCORD_WEBHOOK_URL=''
[ -r /home/shanerunham/homelab/alerts.env ] && . /home/shanerunham/homelab/alerts.env

send() {
  [ -n "$DISCORD_WEBHOOK_URL" ] || { echo "No Discord webhook in alerts.env" >&2; return 1; }
  local payload
  payload=$(python3 -c 'import json, sys; print(json.dumps({"content": sys.argv[1][:1900]}))' "$1")  # no @mention: the bot sees the failed run and HA alerts the phone; this post is the log
  curl -fsS -m 15 --retry 3 -o /dev/null -H 'Content-Type: application/json' -d "$payload" "$DISCORD_WEBHOOK_URL"
}

if [ "${1:-}" = --test ]; then
  send "Test from $(hostname): disk health alerts are set up."
  exit
fi

problems=()
for dev in /dev/sd?; do
  name=${dev##*/}
  [ "$(cat "/sys/block/$name/size")" -gt 0 ] || continue  # skip empty card-reader slots like sdd
  label="$dev ($(cat "/sys/block/$name/device/model" 2>/dev/null | xargs))"
  out=$(smartctl -H -A -l selftest "$dev")
  status=$?
  # USB enclosures (e.g. the Seagate Expansion PS3 drive) often need SAT passthrough; some don't pass SMART at all.
  if (( status & 2 )) && [ "$(lsblk -dno TRAN "$dev")" = usb ]; then
    out=$(smartctl -d sat -H -A -l selftest "$dev")
    status=$?
    (( status & 2 )) && { echo "$label: USB drive doesn't pass SMART through, skipped"; continue; }
  fi
  # smartctl exit bits: 2 = couldn't open, 8 = failing, 16 = pre-fail attribute at threshold, 128 = failed self-test
  (( status & (2|8|16|128) )) && problems+=("$label: smartctl reported a problem (exit status $status)")
  # Reallocated, pending and uncorrectable sector counts should stay at 0.
  bad=$(awk '($1==5 || $1==197 || $1==198) && $10+0 > 0 {printf "%s=%s ", $2, $10}' <<<"$out")
  [ -n "$bad" ] && problems+=("$label: $bad")
done

if (( ${#problems[@]} )); then
  msg="Disk warning on $(hostname):"$'\n'"$(printf -- '- %s\n' "${problems[@]}")"
  echo "$msg"
  send "$msg"
  exit 1
fi
echo "All disks healthy"
