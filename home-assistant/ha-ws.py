#!/usr/bin/env python3
"""Send websocket API commands to the local Home Assistant and print each result.
Usage: ha-ws.py '{"type": "config_entries/flow/progress"}' ['{...}' ...]
Uses the long-lived token in ~/homelab/home-assistant/token."""
import asyncio, json, sys, pathlib, aiohttp

TOKEN = pathlib.Path.home().joinpath("homelab/home-assistant/token").read_text().strip()

async def main(msgs):
    async with aiohttp.ClientSession() as s, s.ws_connect("http://127.0.0.1:8123/api/websocket") as ws:
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": TOKEN})
        if (await ws.receive_json())["type"] != "auth_ok":
            sys.exit("auth failed")
        for i, m in enumerate(msgs, 1):
            await ws.send_json({"id": i, **json.loads(m)})
            while (r := await ws.receive_json()).get("id") != i or r["type"] != "result":
                pass
            print(json.dumps(r.get("result") if r["success"] else r["error"], indent=1))

asyncio.run(main(sys.argv[1:]))
