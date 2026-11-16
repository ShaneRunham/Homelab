#!/usr/bin/env python3
"""Copy the PS3's game saves and PSN licences (exdata: .rif files + act.dat) into ~/homelab/ps3-backup/data,
which the nightly homelab backup already includes. Runs every 30 min from a user timer, but only does work when
the PS3 answers (HEN enabled) and the last full copy is over 20 h old. Files are copied only when new or changed
in size; nothing is ever deleted here, so a save removed on the PS3 stays in the copy."""
import ftplib
import json
import os
import sys
import time

PS3 = "192.168.0.163"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
STATE = os.path.join(HERE, "last-run.json")
EVERY = 20 * 3600
FOLDERS = ("savedata", "exdata")


def listing(ftp, path):
    """[(name, is_dir, size)] for one folder."""
    rows = []
    ftp.retrlines(f"LIST {path}", rows.append)
    out = []
    for r in rows:
        parts = r.split(None, 8)
        if len(parts) < 9 or parts[8] in (".", ".."):
            continue
        out.append((parts[8], r.startswith("d"), int(parts[4])))
    return out


def mirror(ftp, remote, local, counts):
    os.makedirs(local, exist_ok=True)
    for name, is_dir, size in listing(ftp, remote):
        r, l = f"{remote}/{name}", os.path.join(local, name)
        if is_dir:
            mirror(ftp, r, l, counts)
        elif not (os.path.exists(l) and os.path.getsize(l) == size):
            with open(l + ".part", "wb") as f:
                ftp.retrbinary(f"RETR {r}", f.write)
            os.replace(l + ".part", l)
            counts["copied"] += 1
        counts["files"] += 1


def main():
    force = "--now" in sys.argv
    try:
        last = json.load(open(STATE))
    except (OSError, ValueError):
        last = {}
    if not force and time.time() - last.get("ok_at", 0) < EVERY:
        return
    try:
        ftp = ftplib.FTP(PS3, timeout=10)
        ftp.login()
    except OSError:
        return  # PS3 off or HEN not enabled: try again later
    counts = {"files": 0, "copied": 0}
    with ftp:
        for user, is_dir, _ in listing(ftp, "/dev_hdd0/home"):
            if not is_dir:
                continue
            for folder in FOLDERS:
                mirror(ftp, f"/dev_hdd0/home/{user}/{folder}", os.path.join(DATA, user, folder), counts)
    last = {"ok_at": time.time(), **counts}
    json.dump(last, open(STATE, "w"))
    print(f"PS3 backup: {counts['files']} files, {counts['copied']} new or changed")


if __name__ == "__main__":
    main()
