"""One-off: rename members to "ServerName (@RobloxUsername)".

Looks up each member's linked Roblox account through Bloxlink's server API (BLOXLINK_API_KEY in .env),
then the names from Roblox. Members with no Bloxlink link are listed, not touched.
Dry run by default; `--apply` renames. Needs Manage Nicknames and a role above the members.
Run: ~/.local/share/homelab-bot-venv/bin/python rename.py [--apply]
"""
import asyncio
import os
import sys

import json
import re
from pathlib import Path

import aiohttp
import discord
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
APPLY = "--apply" in sys.argv
NAMES = Path(__file__).resolve().parent / "names.json"  # member id -> server name before any "(@...)" was added
SUFFIX = re.compile(r" \(@[^)]*\)$")


def nickname(display, username):
    tail = f" (@{username})"
    if len(display) + len(tail) > 32:  # Discord's nickname limit
        display = display[: max(0, 32 - len(tail))]
    return (display + tail) if display else f"@{username}"[:32]


async def roblox_id(s, guild_id, member_id):
    url = f"https://api.blox.link/v4/public/guilds/{guild_id}/discord-to-roblox/{member_id}"
    for _ in range(3):
        async with s.get(url, headers={"Authorization": os.environ["BLOXLINK_API_KEY"]}) as r:
            if r.status == 429:
                await asyncio.sleep(10)
                continue
            data = await r.json(content_type=None)
            return data.get("robloxID")
    return None


async def run(g):
    me = g.me
    rename, linked_ok, unlinked, cant = [], 0, [], []
    names = json.loads(NAMES.read_text()) if NAMES.exists() else {}
    for m in g.members:  # remember names while they're still the person's own
        if not m.bot and str(m.id) not in names and not SUFFIX.search(m.display_name):
            names[str(m.id)] = m.display_name
    NAMES.write_text(json.dumps(names, indent=1, ensure_ascii=False))
    async with aiohttp.ClientSession() as s:
        for m in sorted((m for m in g.members if not m.bot), key=lambda m: m.name):
            if m == g.owner or m.top_role >= me.top_role:
                cant.append(m.name)
                continue
            rid = await roblox_id(s, g.id, m.id)
            await asyncio.sleep(1)
            if not rid:
                unlinked.append(m.name)
                continue
            async with s.get(f"https://users.roblox.com/v1/users/{rid}") as r:
                u = await r.json()
            # remembered server name; if Bloxlink renamed them before we saw them, their Discord display name
            base = names.get(str(m.id)) or m.global_name or m.name
            new = nickname(base, u["name"])
            if m.nick == new:
                linked_ok += 1
            else:
                rename.append((m, new))
    print(f"\nRENAME ({len(rename)}):")
    for m, new in rename:
        print(f"  {m.display_name}  ->  {new}   [{m.name}]")
    print(f"\nAlready right: {linked_ok}")
    print(f"\nNOT LINKED to Bloxlink, must press Verify ({len(unlinked)}): {', '.join(unlinked)}")
    print(f"\nCan't rename (owner/role at or above the bot) ({len(cant)}): {', '.join(cant)}")
    if not APPLY:
        print("\nDry run. Nothing changed. Add --apply to rename.")
        return
    if not me.guild_permissions.manage_nicknames:
        print("\nStopped: the bot needs Manage Nicknames.")
        return
    done = 0
    for m, new in rename:
        try:
            await m.edit(nick=new, reason="inspect-bot: Bloxlink-style nickname")
            done += 1
        except discord.HTTPException as e:
            print("  x", m.name, e)
    print(f"\nRenamed {done} of {len(rename)}.")


intents = discord.Intents.none()
intents.guilds = intents.members = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    try:
        await run(client.get_guild(int(os.environ["GUILD_ID"])))
    finally:
        await client.close()


asyncio.run(client.start(os.environ["INSPECT_BOT_TOKEN"]))
