"""Shared by bot.py and rename.py: the "ServerName (@RobloxUsername)" nickname, the remembered server names
(names.json, gitignored) and the Bloxlink/Roblox lookups."""
import asyncio
import json
import os
import re
from pathlib import Path

NAMES = Path(__file__).resolve().parent / "names.json"  # member id -> server name before any "(@...)" was added
SUFFIX = re.compile(r" \(@[^)]*\)$")


def nickname(display: str, username: str) -> str:
    tail = f" (@{username})"
    if len(display) + len(tail) > 32:  # Discord's nickname limit
        display = display[: max(0, 32 - len(tail))]
    return (display + tail) if display else f"@{username}"[:32]


def load_names() -> dict:
    return json.loads(NAMES.read_text()) if NAMES.exists() else {}


def save_names(names: dict):
    NAMES.write_text(json.dumps(names, indent=1, ensure_ascii=False))


def base_name(names: dict, member) -> str:
    """The member's own server name: remembered, else their Discord display name."""
    return names.get(str(member.id)) or member.global_name or member.name


async def roblox_username(s, guild_id: int, member_id: int) -> str | None:
    """Linked Roblox username via Bloxlink's server API, or None if they never linked."""
    url = f"https://api.blox.link/v4/public/guilds/{guild_id}/discord-to-roblox/{member_id}"
    rid = None
    for _ in range(3):
        async with s.get(url, headers={"Authorization": os.environ["BLOXLINK_API_KEY"]}) as r:
            if r.status == 429:
                await asyncio.sleep(10)
                continue
            rid = (await r.json(content_type=None)).get("robloxID")
            break
    if not rid:
        return None
    async with s.get(f"https://users.roblox.com/v1/users/{rid}") as r:
        return (await r.json())["name"]
