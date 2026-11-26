"""One-off: rename members to "ServerName (@RobloxUsername)".

Looks up each member's linked Roblox account through Bloxlink's server API (BLOXLINK_API_KEY in .env),
then the names from Roblox. Members with no Bloxlink link are listed, not touched.
Dry run by default; `--apply` renames. Needs Manage Nicknames and a role above the members.
Run: ~/.local/share/homelab-bot-venv/bin/python rename.py [--apply]
"""
import asyncio
import os
import sys

import aiohttp
import discord
from dotenv import load_dotenv

from nicknames import SUFFIX, base_name, load_names, nickname, roblox_username, save_names

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
APPLY = "--apply" in sys.argv


async def run(g):
    me = g.me
    rename, linked_ok, unlinked, cant = [], 0, [], []
    names = load_names()
    for m in g.members:  # remember names while they're still the person's own
        if not m.bot and str(m.id) not in names and not SUFFIX.search(m.display_name):
            names[str(m.id)] = m.display_name
    save_names(names)
    async with aiohttp.ClientSession() as s:
        for m in sorted((m for m in g.members if not m.bot), key=lambda m: m.name):
            if m == g.owner or m.top_role >= me.top_role:
                cant.append(m.name)
                continue
            username = await roblox_username(s, g.id, m.id)
            await asyncio.sleep(1)
            if not username:
                unlinked.append(m.name)
                continue
            new = nickname(base_name(names, m), username)
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
