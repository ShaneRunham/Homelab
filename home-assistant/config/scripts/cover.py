"""Saves a game's art for the Vice panel: /config/www/vice-panel/covers/<kind>-<slug>.png (served as /local/...).
The panel works out the same file name from sensor.ps5_last_game / sensor.ps3_last_played.
  cover.py ps5 <urlencoded name> <picture url or HA path>   PSN artwork from media_player.playstation_5
  cover.py ps3 <urlencoded name>                            the game's ICON0 that webMAN keeps (FTP read only)"""
import ftplib, os, re, sys, urllib.parse, urllib.request

OUT = "/config/www/vice-panel/covers"
PS3 = "192.168.0.163"


def main():
    kind, name = sys.argv[1], urllib.parse.unquote(sys.argv[2])
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    if kind not in ("ps5", "ps3") or not slug:
        return
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{kind}-{slug}.png")
    if os.path.exists(out):
        return
    if kind == "ps5":
        url = sys.argv[3] if len(sys.argv) > 3 else ""
        if not url or url == "None":
            return
        if url.startswith("/"):
            url = "http://127.0.0.1:8123" + url
        data = urllib.request.urlopen(url, timeout=15).read()
        with open(out + ".part", "wb") as f:
            f.write(data)
    else:
        with ftplib.FTP(PS3, timeout=5) as ftp, open(out + ".part", "wb") as f:
            ftp.login()
            ftp.retrbinary(f"RETR /dev_hdd0/tmp/wmtmp/{name}.PNG", f.write)
    os.replace(out + ".part", out)


if __name__ == "__main__":
    main()
