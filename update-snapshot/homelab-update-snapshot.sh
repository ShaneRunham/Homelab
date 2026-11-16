#!/usr/bin/env bash
# Runs as root in the offline-update boot (system-update.target), before PackageKit/dnf5 install the staged Fedora
# updates. Takes a writable btrfs snapshot of / (subvolume root00) and adds a GRUB entry that boots it, so a bad
# update can be undone from the boot menu. Keeps the newest 3. Never blocks the update: failures only go to the
# status file, which the Discord bot reads (problem "update_snapshot").
# `homelab-update-snapshot --test` takes one now (outside an update boot) to try it.
set -uo pipefail
ROOT_SUBVOL=root00
DIR=/.snapshots
ENTRIES=/boot/loader/entries
KEEP=3
STATUS=/var/lib/homelab/update-snapshot.status

mkdir -p "$(dirname "$STATUS")"
fail() { echo "failed $(date '+%Y-%m-%d %H:%M'): $*" | tee "$STATUS" >&2; exit 1; }

[ -e /system-update ] || [ "${1:-}" = --test ] || { echo "No offline update staged; nothing to do"; exit 0; }
grep -q "subvol=$ROOT_SUBVOL " /proc/cmdline || grep -q "subvol=$ROOT_SUBVOL$" /proc/cmdline \
  || fail "/ isn't subvol=$ROOT_SUBVOL (booted from a snapshot?), skipped"

stamp=$(date +%Y-%m-%d_%H%M)
name=pre-update-$stamp
snap=$DIR/$name

# The entry is a copy of the default one, so it boots the kernel that was default before the update
default_id=$(grub2-editenv list 2>/dev/null | sed -n 's/^saved_entry=//p')
src=$ENTRIES/$default_id.conf
[ -n "$default_id" ] && [ -f "$src" ] || fail "can't find the default boot entry ($default_id)"
grep -q "rootflags=subvol=$ROOT_SUBVOL\b" "$src" || fail "default entry has no rootflags=subvol=$ROOT_SUBVOL"

mkdir -p "$DIR"
btrfs subvolume snapshot / "$snap" >/dev/null || fail "btrfs snapshot of / failed"
rm -f "$snap/system-update"  # the snapshot must not start the offline update again when booted
sed -i "s#subvol=$ROOT_SUBVOL\([,[:space:]]\)#subvol=$ROOT_SUBVOL$snap\1#" "$snap/etc/fstab"
grep -q "subvol=$ROOT_SUBVOL$snap" "$snap/etc/fstab" || fail "couldn't point the snapshot's fstab at itself"

kver=$(sed -n 's/^version[[:space:]]*//p' "$src")
sed -e "s#^title .*#title Fedora before update $stamp ($kver)#" \
    -e "s#rootflags=subvol=$ROOT_SUBVOL\b#rootflags=subvol=$ROOT_SUBVOL$snap#" \
    "$src" > "$ENTRIES/homelab-$name.conf" || fail "couldn't write the boot entry"
restorecon "$ENTRIES/homelab-$name.conf" 2>/dev/null

# Keep the newest $KEEP; drop older snapshots and their entries, and entries whose kernel has been removed
mapfile -t old < <(ls -1d "$DIR"/pre-update-* 2>/dev/null | sort | head -n -"$KEEP")
for s in "${old[@]}"; do
  btrfs subvolume delete "$s" >/dev/null && rm -f "$ENTRIES/homelab-$(basename "$s").conf"
done
for e in "$ENTRIES"/homelab-pre-update-*.conf; do
  [ -e "$e" ] || continue
  k=$(sed -n 's/^linux[[:space:]]*//p' "$e")
  [ -e "/boot$k" ] || [ -e "$k" ] || rm -f "$e"
done

echo "ok $(date '+%Y-%m-%d %H:%M'): $snap (kernel $kver)" | tee "$STATUS"
