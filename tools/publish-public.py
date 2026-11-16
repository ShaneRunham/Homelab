#!/usr/bin/env python3
"""Publishes cleaned public copies of Shane's projects to GitHub (2026-11-16): Homelab, VICE-Bot, VICE-Radio (from
~/homelab) and VICE-Home (from ~/tv-launcher). The full history stays private (Forgejo, and the GitHub copies
homelab-private / vice-home-private).

Each copy is the committed files of the source repo, minus private working notes, media (third-party artwork, logos,
fonts, videos) and machine-specific bits, with personal details swapped for placeholders. The real values live in
~/.config/public-mirror/scrub.json (never in git). Before pushing it checks the result: if any real value, a
Tailscale address, a MAC address, a Discord ID or anything gitleaks flags is left, it pushes nothing and says why.

Run by the shared post-commit hook in the background (homelab and tv-launcher); safe to run by hand any time:
  ~/homelab/tools/publish-public.py ~/homelab        (or ~/tv-launcher; --dry-run builds and checks without pushing)
Snapshots are committed in ~/.local/share/public-mirrors/<repo> under Shane's GitHub noreply email, so the repos show
him as contributor (his pick, 2026-11-16: new work counts on the graph in both the private and the public copy)."""
import fnmatch, json, os, re, shutil, subprocess, sys, tempfile, urllib.request

HOME = os.path.expanduser("~")
WORK = os.path.join(HOME, ".local/share/public-mirrors")
SCRUB = os.path.join(HOME, ".config/public-mirror/scrub.json")
OVERLAY = os.path.join(HOME, "homelab/public")  # README per public repo, copied over the export
MEDIA = ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.mp4", "*.mp3", "*.wav", "*.woff2", "*.ttf", "*.otf",
         "*.svg", "*.ico", "*.ipk")
NOTES = ("README.md", "CHANGELOG.md", "HANDOFF.md", "OVERHAUL.md", "*-plan.md", ".gitleaksignore", ".graphifyignore",
         "expiries.json")
REPOS = {  # source repo folder name -> [(public repo, subfolder or "", extra excluded globs)]
    "homelab": [
        ("Homelab", "", ["discord-bot/*", "radio/*", "public/*", "maintenance/*", "psp/*", "forgejo-runner/*",
                         "home-assistant/panel/source/*", "home-assistant/panel/mockup/*"]),
        ("VICE-Bot", "discord-bot", []),
        ("VICE-Radio", "radio", []),
    ],
    "tv-launcher": [
        ("VICE-Home", "", ["mockup/*", "tools/perf/results-*", "tools/tvshot", "tools/tvkey", "tools/tvopen",
                           "public/*"]),
    ],
}
LEFTOVERS = {  # checked after scrubbing, on top of every real value in scrub.json
    "Tailscale address": r"(?<![\d.])100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}(?![\d])",
    "MAC address": r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(?![0-9A-Fa-f:])",
    "Discord-style ID": r"(?<!\d)\d{17,20}(?!\d)",
}
PLACEHOLDERS = {"100.64.0.1", "00:00:00:00:00:00", "000000000000000000"}  # what the patterns above become


def git(repo, *args, **kw):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True, **kw).stdout


def scrubber():
    words = json.load(open(SCRUB))["words"]
    pats = []
    for real, fake in words.items():
        if real[0].isalpha():  # names: whole word only (letters around it), so "Jackson" or "jack" stay
            pats.append((re.compile(rf"(?<![A-Za-z]){re.escape(real)}(?![A-Za-z])"), fake))
        else:
            pats.append((re.compile(re.escape(real)), fake))
    tail = re.compile(LEFTOVERS["Tailscale address"])
    mac = re.compile(LEFTOVERS["MAC address"])
    ids = re.compile(LEFTOVERS["Discord-style ID"])

    def clean(text):
        for p, fake in pats:
            text = p.sub(fake, text)
        text = tail.sub("100.64.0.1", text)
        text = mac.sub("00:00:00:00:00:00", text)
        return ids.sub("000000000000000000", text)
    return clean, list(words)


def excluded(path, extra):
    name = os.path.basename(path)
    return (any(fnmatch.fnmatch(name, g) for g in MEDIA + NOTES)
            or any(fnmatch.fnmatch(path, g) for g in extra))


def build(src, sub, extra, clean, out):
    files = git(src, "ls-files", "-z", "--", sub or ".").split("\0")
    for f in filter(None, files):
        rel = f[len(sub) + 1:] if sub else f
        if excluded(rel, extra) or not os.path.isfile(os.path.join(src, f)):
            continue
        data = subprocess.run(["git", "-C", src, "show", f"HEAD:{f}"], check=True, capture_output=True).stdout
        if b"\0" in data[:8000]:
            continue  # binary that isn't media: leave it out rather than publish unchecked bytes
        dest = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as fh:
            fh.write(clean(data.decode("utf-8", "replace")))
        if os.access(os.path.join(src, f), os.X_OK):
            os.chmod(dest, 0o755)


def problems(out, reals):
    found = []
    checks = [(r, re.compile(re.escape(r), re.I)) for r in reals if r[0].isalpha() and len(r) > 4]
    checks += [(r, re.compile(re.escape(r))) for r in reals if not r[0].isalpha()]
    checks += [(name, re.compile(p)) for name, p in LEFTOVERS.items()]
    names = [r for r in reals if r[0].isalpha() and len(r) <= 4]  # short names: whole word, exact case
    checks += [(r, re.compile(rf"(?<![A-Za-z]){re.escape(r)}(?![A-Za-z])")) for r in names]
    for root, _, files in os.walk(out):
        if "/.git" in root + "/":
            continue
        for f in files:
            p = os.path.join(root, f)
            text = open(p, errors="replace").read()
            for label, rx in checks:
                if any(m.group(0) not in PLACEHOLDERS for m in rx.finditer(text)):
                    found.append(f"{os.path.relpath(p, out)}: {label}")
    leaks = subprocess.run(["gitleaks", "dir", "--no-banner", "--redact", out], capture_output=True, text=True)
    if leaks.returncode:
        found.append("gitleaks: " + (leaks.stdout + leaks.stderr).strip().splitlines()[-1])
    return found


def publish(name, out, message, dry):
    repo = os.path.join(WORK, name)
    token = open(os.path.join(HOME, ".config/github/token")).read().strip()
    url = f"https://x-access-token:{token}@github.com/ShaneRunham/{name}.git"
    # GitHub forwards renamed repos: make sure this name is itself a public repo, never a forward to a private one
    req = urllib.request.Request(f"https://api.github.com/repos/ShaneRunham/{name}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as f:
        info = json.load(f)
    if info["full_name"] != f"ShaneRunham/{name}" or info["private"]:
        return f"NOT pushed: {name} on GitHub is {info['full_name']} (private={info['private']})"
    if not os.path.isdir(os.path.join(repo, ".git")):
        os.makedirs(repo, exist_ok=True)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.name", "Shane Runham")
        git(repo, "config", "user.email", "118390486+ShaneRunham@users.noreply.github.com")  # shows Shane as contributor
        if subprocess.run(["git", "-C", repo, "fetch", "-q", url, "main"], capture_output=True).returncode == 0:
            git(repo, "reset", "-q", "--soft", "FETCH_HEAD")
    for entry in os.listdir(repo):
        if entry != ".git":
            p = os.path.join(repo, entry)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copytree(out, repo, dirs_exist_ok=True)
    git(repo, "add", "-A")
    if not git(repo, "status", "--porcelain").strip():
        return "no changes"
    if dry:
        return "would commit:\n" + git(repo, "status", "--short")
    git(repo, "commit", "-q", "-m", message)
    r = subprocess.run(["git", "-C", repo, "push", "-q", url, "HEAD:main"], capture_output=True, text=True,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, timeout=120)
    return "pushed" if r.returncode == 0 else "push failed: " + r.stderr.replace(token, "***").strip()[-300:]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    src = os.path.realpath(args[0] if args else os.getcwd())
    targets = REPOS.get(os.path.basename(src))
    if not targets:
        return
    clean, reals = scrubber()
    subject = git(src, "log", "-1", "--format=%s").strip()
    for name, sub, extra in targets:
        with tempfile.TemporaryDirectory() as out:
            build(src, sub, extra, clean, out)
            shutil.copytree(os.path.join(OVERLAY, name), out, dirs_exist_ok=True)
            bad = problems(out, reals)
            if bad:
                print(f"{name}: NOT published, personal details left:\n  " + "\n  ".join(bad[:20]))
                continue
            print(f"{name}: " + publish(name, out, clean(subject), dry))


if __name__ == "__main__":
    main()
