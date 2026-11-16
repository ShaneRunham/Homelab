#!/usr/bin/env python3
"""Lets Home Assistant drive the Govee H6008 with the packet code from ~/.local/bin/govee (the bulb is
Bluetooth-only). Runs on the govee venv's python (it needs bleak).

Listens on 127.0.0.1:5402. POST /run with JSON {"cmds": [["on"], ["brightness", 40]]} sends all the
commands over one Bluetooth connection. One request at a time, because the bulb takes a single
connection; requests fail while Screen Sync, the Govee GUI or the phone app holds it."""
import asyncio, importlib.machinery, json, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

govee = importlib.machinery.SourceFileLoader("govee", os.path.expanduser("~/.local/bin/govee")).load_module()
ALLOWED = {"on": 0, "off": 0, "brightness": 1, "color": 3, "white": 1}  # command -> number of int args
lock = threading.Lock()


def valid(cmd):
    return (isinstance(cmd, list) and cmd and cmd[0] in ALLOWED and len(cmd) == 1 + ALLOWED[cmd[0]]
            and all(isinstance(a, int) or (isinstance(a, str) and a.isdigit()) for a in cmd[1:]))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            cmds = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["cmds"]
            assert isinstance(cmds, list) and cmds and all(valid(c) for c in cmds)
        except Exception:
            return self.reply(400, "bad request")
        packets = []
        for name, *args in cmds:
            args = [int(a) for a in args]
            if name in ("on", "off"):
                packets.append(govee.power(name == "on"))
            elif name == "brightness":
                packets.append(govee.brightness(args[0]))
            elif name == "color":
                packets.append(govee.color(*(max(0, min(255, v)) for v in args)))
            elif name == "white":
                packets.append(govee.white(args[0]))
        with lock:
            try:
                asyncio.run(asyncio.wait_for(govee.send(*packets), 45))
            except BaseException as e:  # govee.connect() calls sys.exit when the bulb isn't visible
                return self.reply(502, f"light unreachable (Screen Sync, the GUI or the phone app may hold it): {e!r}"[:300])
        self.reply(200, "ok")

    def reply(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(text.encode())

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # A caller that hangs up mid-reply is normal, not a traceback.
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


QuietServer(("127.0.0.1", 5402), Handler).serve_forever()
