"""Weekly layout backup (2026-11-27): everything needed to rebuild the server after a raid or a bad edit.

Saves backups/auto-<date>.json: server settings, every role (name, colour, permissions, order...), every category
and channel (name, place, topic, permission overwrites for roles and members...) and which roles each member has.
Keeps the newest KEEP auto backups; manual backups (fix.py, layout-*) are never deleted.
Read-only: it only reads the server. Restoring is done by hand or with a script written from the file when needed.
"""
import datetime as dt
import json
from pathlib import Path

import discord

BACKUPS = Path(__file__).resolve().parent / "backups"
KEEP = 12  # about three months of weekly backups


def overwrites(ch) -> dict:
    out = {}
    for target, o in ch.overwrites.items():
        allow, deny = o.pair()
        kind = "role" if isinstance(target, discord.Role) else "member"
        out[str(target.id)] = {"type": kind, "name": target.name, "allow": allow.value, "deny": deny.value}
    return out


def snapshot(g: discord.Guild) -> dict:
    channels = {}
    for ch in g.channels:
        c = {"name": ch.name, "type": str(ch.type), "position": ch.position, "category": ch.category_id,
             "category_name": ch.category.name if ch.category else None, "overwrites": overwrites(ch)}
        for attr in ("topic", "nsfw", "slowmode_delay", "bitrate", "user_limit", "rtc_region"):
            v = getattr(ch, attr, None)
            if v is not None:
                c[attr] = str(v) if attr == "rtc_region" else v
        channels[str(ch.id)] = c
    return {
        "taken": dt.datetime.now().isoformat(timespec="seconds"), "guild": g.id, "name": g.name,
        "settings": {
            "description": g.description, "verification_level": g.verification_level.value,
            "explicit_content_filter": g.explicit_content_filter.value,
            "default_notifications": g.default_notifications.value, "mfa_level": g.mfa_level.value,
            "afk_channel": g.afk_channel.id if g.afk_channel else None, "afk_timeout": g.afk_timeout,
            "system_channel": g.system_channel.id if g.system_channel else None,
            "icon": str(g.icon.url) if g.icon else None, "splash": str(g.splash.url) if g.splash else None,
        },
        "roles": {str(r.id): {"name": r.name, "position": r.position, "colour": r.colour.value,
                              "hoist": r.hoist, "mentionable": r.mentionable, "managed": r.managed,
                              "permissions": r.permissions.value, "unicode_emoji": r.unicode_emoji,
                              "icon": str(r.icon.url) if r.icon else None}
                  for r in g.roles},
        "channels": channels,
        "members": {str(m.id): {"name": m.name, "nick": m.nick,
                                "roles": [r.id for r in m.roles if not r.is_default()]}
                    for m in g.members if not m.bot},
    }


def save(g: discord.Guild, now: dt.datetime | None = None) -> Path:
    BACKUPS.mkdir(exist_ok=True)
    path = BACKUPS / f"auto-{(now or dt.datetime.now()):%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(snapshot(g), indent=1, ensure_ascii=False))
    prune()
    return path


def prune(keep: int = KEEP) -> list[Path]:
    old = sorted(BACKUPS.glob("auto-*.json"))[:-keep]
    for p in old:
        p.unlink()
    return old
