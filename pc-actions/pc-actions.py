#!/usr/bin/env python3
"""PC buttons for the Home Assistant panel. Listens on 127.0.0.1:5403 (PC only).
POST /lock     lock the screen (KDE)
POST /vscode   open VS Code on the PC's screen
POST /poweroff log out and shut down cleanly (KDE), falling back to systemctl poweroff
POST /restart-container/<name>  restart a Docker container (only names `docker ps -a` lists; runs under sg docker)
POST /restart-unit/<unit>       restart one of the user services the Discord bot watches (collect.USER_UNITS)
Same methods as the Discord bot's PC controls. Used by HA's buttons and the action buttons on alert notifications."""
import os, re, subprocess, sys, time

sys.path.insert(0, os.path.expanduser("~/homelab/discord-bot"))
from collect import USER_UNITS  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=20).returncode == 0


ACTIONS = {
    "/lock": lambda: run("qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock")
                     or run("loginctl", "lock-sessions"),
    # Its own transient unit, so VS Code isn't tied to (or killed with) this service.
    "/vscode": lambda: run("systemd-run", "--user", "--collect", f"--unit=vscode-from-ha-{int(time.time())}", "/usr/bin/code"),
    "/poweroff": lambda: run("qdbus", "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logoutAndShutdown")
                         or run("systemctl", "poweroff"),
}


def restart(kind, name):
    if kind == "container":
        names = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"], capture_output=True, text=True,
                               timeout=20).stdout.split()
        return name in names and run("docker", "restart", name)
    return name in USER_UNITS and run("systemctl", "--user", "restart", name)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        m = re.fullmatch(r"/restart-(container|unit)/([\w@.-]+)", self.path)
        if m:
            return self.reply(200, "ok") if restart(*m.groups()) else self.reply(502, "failed")
        action = ACTIONS.get(self.path)
        if not action:
            return self.reply(404, "unknown action")
        self.reply(200, "ok") if action() else self.reply(502, "failed")

    def reply(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(text.encode())

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


ThreadingHTTPServer(("127.0.0.1", 5403), Handler).serve_forever()
