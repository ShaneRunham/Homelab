#!/usr/bin/env python3
"""PC black box: records system vitals every 10 s and journal warnings, synced to disk,
so the moments before a full freeze survive it.

  blackbox.py run      the logger (run by blackbox.service)
  blackbox [N]         show recent sessions and the last N lines (default 40) before the
                       most recent one that ended without a clean shutdown
"""
import os, re, signal, subprocess, sys, threading, time, json, urllib.request
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".local/state/blackbox"
KEEP_DAYS = 14
INTERVAL = 10
WIFI_PCI = "/sys/bus/pci/devices/0000:03:00.0/aer_dev_correctable"
ALERTS_ENV = Path.home() / "homelab/alerts.env"
CLEAN = "STOP clean shutdown"


def read(path, default=""):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def hwmon_temp(name):
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        if read(h / "name") == name:
            return int(read(h / "temp1_input", "0")) // 1000
    return None


def cpu_times():
    f = read("/proc/stat").splitlines()[0].split()[1:]
    vals = list(map(int, f))
    return sum(vals), vals[3] + vals[4]  # total, idle+iowait


def proc_times():
    out = {}
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            stat = (p / "stat").read_text()
        except OSError:
            continue
        comm = stat[stat.index("(") + 1:stat.rindex(")")]
        f = stat[stat.rindex(")") + 2:].split()
        out[p.name] = (comm, int(f[11]) + int(f[12]))  # utime + stime
    return out


def sample(prev):
    total, idle = cpu_times()
    procs = proc_times()
    line = None
    if prev:
        ptotal, pidle, pprocs = prev
        dt = max(total - ptotal, 1)
        cpu = 100 * (dt - (idle - pidle)) / dt
        ncpu = os.cpu_count() or 1
        top = sorted(((t - pprocs[pid][1], c) for pid, (c, t) in procs.items() if pid in pprocs),
                     reverse=True)[:3]
        top_s = ",".join(f"{c}:{100 * d * ncpu / dt:.0f}%" for d, c in top if d > 0) or "-"
        mem = {k: int(v.split()[0]) // 1024 for k, v in
               (l.split(":", 1) for l in read("/proc/meminfo").splitlines())}
        aer = re.search(r"TOTAL_ERR_COR (\d+)", read(WIFI_PCI))
        sig = re.search(r"signal: (-?\d+)", subprocess.run(
            ["iw", "dev", "wlp3s0", "link"], capture_output=True, text=True).stdout)
        line = (f"{datetime.now():%H:%M:%S} load={read('/proc/loadavg').split()[0]} cpu={cpu:.0f}% "
                f"mem_free={mem['MemAvailable']}M swap_used={mem['SwapTotal'] - mem['SwapFree']}M "
                f"cpu_temp={hwmon_temp('coretemp')}C gpu_temp={hwmon_temp('amdgpu')}C "
                f"gpu_busy={read('/sys/class/drm/card1/device/gpu_busy_percent', '?')}% "
                f"wifi={sig.group(1) if sig else '?'}dBm wifi_pcie_err={aer.group(1) if aer else '?'} "
                f"top={top_s}")
    return line, (total, idle, procs)


def sessions():
    return sorted(LOG_DIR.glob("*.log"))


def ended_clean(path):
    with open(path, "rb") as f:
        f.seek(max(0, path.stat().st_size - 4096))
        records = [l for l in f.read().decode(errors="replace").splitlines() if not l.startswith("  J ")]
        return bool(records) and CLEAN in records[-1]


def discord(msg):
    env = dict(re.findall(r"^(\w+)=['\"]?(.*?)['\"]?$", read(ALERTS_ENV), re.M))
    url = env.get("DISCORD_WEBHOOK_URL")
    if not url:
        return
    body = json.dumps({"content": f"{env.get('DISCORD_MENTION', '')} {msg}".strip()[:1900]}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json", "User-Agent": "blackbox"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except OSError as e:
        print(f"Discord post failed: {e}", file=sys.stderr)


def run():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - KEEP_DAYS * 86400
    for old in sessions():
        if old.stat().st_mtime < cutoff:
            old.unlink()

    previous = sessions()
    if previous and not ended_clean(previous[-1]):
        lines = previous[-1].read_text(errors="replace").splitlines()
        vitals = [l for l in lines if not l.startswith("  J ")][-3:]
        warnings = [l[4:][:160] for l in lines if l.startswith("  J ")][-5:]
        tail = "\n".join(vitals + (["warnings:"] + warnings if warnings else []))[:1400] or "none"
        discord(f"⚠️ Black box: the last session on {os.uname().nodename} ended without a clean "
                f"shutdown (freeze or power loss). Its last records:\n```\n{tail}\n```"
                f"Run `blackbox` on the PC for more.")

    boot = read("/proc/sys/kernel/random/boot_id")[:8]
    path = LOG_DIR / f"{datetime.now():%Y-%m-%d_%H%M}_{boot}.log"
    f = open(path, "a", buffering=1)
    lock = threading.Lock()

    def write(text, sync=False):
        with lock:
            f.write(text + "\n")
            if sync:
                f.flush()
                os.fsync(f.fileno())

    def stop(*_):
        write(f"{datetime.now():%H:%M:%S} {CLEAN}", sync=True)
        os._exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    write(f"{datetime.now():%Y-%m-%d %H:%M:%S} START boot={boot} kernel={os.uname().release}", sync=True)

    def follow_journal():
        p = subprocess.Popen(["journalctl", "-f", "-n", "0", "-p", "warning", "-o", "short-iso"],
                             stdout=subprocess.PIPE, text=True, errors="replace")
        for jl in p.stdout:
            write("  J " + jl.rstrip())

    threading.Thread(target=follow_journal, daemon=True).start()

    _, prev = sample(None)
    while True:
        time.sleep(INTERVAL)
        line, prev = sample(prev)
        write(line, sync=True)


def report(n):
    all_s = sessions()
    if not all_s:
        print(f"No black box records yet in {LOG_DIR}")
        return
    current = read("/proc/sys/kernel/random/boot_id")[:8]
    print("Recent sessions:")
    bad = None
    for s in all_s[-10:]:
        live = s.stem.endswith(current)
        state = "running now" if live else ("clean" if ended_clean(s) else "ENDED WITHOUT CLEAN SHUTDOWN")
        print(f"  {s.stem}  {state}")
        if not live and state != "clean":
            bad = s
    if bad:
        print(f"\nLast {n} lines of {bad.name} (just before it stopped):")
        print("\n".join(bad.read_text(errors="replace").splitlines()[-n:]))
    else:
        print("\nNo freezes or power losses recorded.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["run"]:
        run()
    else:
        report(int(sys.argv[1]) if sys.argv[1:] else 40)
