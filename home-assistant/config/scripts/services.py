"""Homelab services line for the panel, from Uptime Kuma's public status page (same logic as vice-tv)."""
import json, urllib.request
KUMA = "http://127.0.0.1:3001/api/{}/homelab"
try:
    get = lambda u: json.load(urllib.request.urlopen(u, timeout=5))
    page, beats = get(KUMA.format("status-page")), get(KUMA.format("status-page/heartbeat"))
    down, total = [], 0
    for g in page["publicGroupList"]:
        for m in g["monitorList"]:
            total += 1
            if (beats["heartbeatList"].get(str(m["id"])) or [{}])[-1].get("status") != 1:
                down.append(m["name"])
    line = (f"All {total} services up" if not down else f"{down[0]} is down" if len(down) == 1
            else f"{len(down)} of {total} services down")
    print(json.dumps({"line": line, "good": not down}))
except Exception:
    print(json.dumps({"line": "Can't reach Uptime Kuma", "good": False}))
