#!/usr/bin/env bash
# Daily snapshot of important home folders to /mnt/storage. Unchanged files are hard-linked between snapshots.
set -euo pipefail

HOME_DIR=/home/shanerunham
DEST=/mnt/storage/backups/fedora
KEEP=14
ALERTS="$HOME_DIR/homelab/alerts.env"
SOURCES=(
  homelab
  Documents
  Music
  Pictures
  Videos
  Desktop
  iso2dsd
  sacd-ripper
  CLAUDE.md
  .config/fish
  .claude/projects/-home-shanerunham/memory
  tv-launcher           # Vice Home on the LG + vice-tv (added 2026-11-12)
  couch-tv              # its config.json (pairing key) and local edits; build/.venv/node_modules left out below
  .local/bin            # ha-light, govee, phone-cam and friends
  .config/systemd/user  # the user services (vice-tv, couch-tv-bridge, govee-bridge, pc-actions, homelab-bot...)
  .config/sunshine      # Sunshine's apps.json (Play on PC games) and covers
  .var/app/org.ppsspp.PPSSPP/config/ppsspp/PSP  # PSP saves, save states, cheats (synced with the tablet; added 2026-11-13)
  .ssh                  # webOS / LG TV keys (added 2026-11-12)
  .claude/settings.json .claude/CLAUDE.md .claude/skills  # Claude Code settings and skills, not the chat transcripts
)
# Things that can be rebuilt, left out of the copy.
EXCLUDES=(--exclude=couch-tv/build/ --exclude=couch-tv/.venv/ --exclude=couch-tv/venv/ --exclude=node_modules/)

# Report the result to the Uptime Kuma push monitor, which alerts on "down" or on no report for a day.
BACKUP_PUSH_URL=''
[ -r "$ALERTS" ] && . "$ALERTS"
push() {
  [ -n "$BACKUP_PUSH_URL" ] || return 0
  curl -fsS -m 10 --retry 12 --retry-delay 5 --retry-all-errors -o /dev/null -G "$BACKUP_PUSH_URL" \
    --data-urlencode "status=$1" --data-urlencode "msg=$2" || true
}
trap 'push down "Backup failed at line $LINENO"' ERR

mountpoint -q /mnt/storage || { echo "/mnt/storage is not mounted" >&2; push down "/mnt/storage is not mounted"; exit 1; }
mkdir -p "$DEST"

partial="$DEST/.in-progress"
rm -rf "$partial"

link=()
[ -d "$DEST/latest" ] && link=(--link-dest="$DEST/latest")

# Stop Uptime Kuma during the copy so its database is consistent.
restart_kuma=no
start_kuma() { [ "$restart_kuma" = yes ] && docker start uptime-kuma >/dev/null; return 0; }
trap start_kuma EXIT
if [ -n "$(docker ps -q --filter name='^uptime-kuma$')" ]; then
  docker stop uptime-kuma >/dev/null
  restart_kuma=yes
fi

cd "$HOME_DIR"
rsync -aHAXR --delete "${EXCLUDES[@]}" "${link[@]}" "${SOURCES[@]}" "$partial/"

# Home Assistant keeps writing its database, so the rsync copy can be half-written. Replace it with a
# consistent SQLite backup (mv swaps in a new file, so a hard link to the previous snapshot is untouched).
ha_db=homelab/home-assistant/config/home-assistant_v2.db
if [ -f "$ha_db" ]; then
  python3 -I - "$ha_db" "$partial/$ha_db.tmp" <<'PY'
import sqlite3, sys
src = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close(); src.close()
PY
  mv -f "$partial/$ha_db.tmp" "$partial/$ha_db"
  rm -f "$partial/$ha_db-wal" "$partial/$ha_db-shm"
fi

start_kuma
restart_kuma=no

snapshot="$DEST/$(date +%F_%H%M%S)"
mv "$partial" "$snapshot"
ln -sfn "$snapshot" "$DEST/latest"

find "$DEST" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | head -n "-$KEEP" | xargs -r rm -rf

echo "Backup finished: $snapshot"
push up "Backup finished: $(basename "$snapshot")"
