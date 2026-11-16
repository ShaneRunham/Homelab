"""PS3 (192.168.0.163) for Home Assistant, through webMAN MOD only. Read-only apart from popup and shutdown.
Same calls and URL encoding as the Discord bot (homelab/discord-bot/gaming.py); see the ps3-webman notes:
never config, theme or fan writes from here.
  ps3.py status          -> JSON {"power", "webman", "cpu", "rsx", "fan", "game"}
  ps3.py popup <text>    -> on-screen message
  ps3.py shutdown"""
import ftplib, io, json, re, subprocess, sys, urllib.parse, urllib.request

IP = "192.168.0.163"


def cmd(path, timeout=15):
    url = f"http://{IP}" + urllib.parse.quote_plus(path, safe="/[]!;")  # spaces as "+", like webMAN's own links
    return urllib.request.urlopen(url, timeout=timeout).read().decode("utf-8", "replace")


def status():
    s = {"power": "off", "webman": False, "cpu": None, "rsx": None, "fan": None, "game": None}
    if subprocess.run(["ping", "-c1", "-W1", IP], capture_output=True).returncode:
        return s
    s["power"] = "on"
    try:
        text = re.sub(r"<[^>]+>", " ", cmd("/cpursx.ps3", 3))
    except OSError:
        return s  # on, but HEN (and so webMAN) not enabled yet
    s["webman"] = True
    for key, pat in (("cpu", r"CPU:\s*(\d+)\s*°C"), ("rsx", r"RSX:\s*(\d+)\s*°C"), ("fan", r"FAN SPEED:\s*(\d+)%")):
        m = re.search(pat, text)
        s[key] = int(m.group(1)) if m else None
    buf = io.BytesIO()
    try:
        with ftplib.FTP(IP, timeout=5) as ftp:
            ftp.login()
            ftp.retrbinary("RETR /dev_hdd0/tmp/wmtmp/last_game.txt", buf.write)
        last = buf.getvalue().decode("utf-8", "replace").strip().rsplit("/", 1)[-1]
        if last and not last.startswith("[MOVIES]"):
            s["game"] = last.split(".ntfs[")[0].removesuffix(".BIN.ENC").removesuffix(".iso").removesuffix(".ISO") or None
    except (OSError, ftplib.Error):
        pass
    return s


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "status"
    if what == "status":
        print(json.dumps(status()))
    elif what == "popup":
        cmd("/popup.ps3/" + " ".join(sys.argv[2:])[:200])
    elif what == "shutdown":
        cmd("/shutdown.ps3")
