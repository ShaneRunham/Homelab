"""Welcome and leave posts with a DPGS Rider Licence (2026-11-28, replaces Welcomer).

Join: in #🛬・flying-in, "Welcome @member 👋", a card with the "Get rolling" links, the licence (status UNVERIFIED,
or VERIFIED if they already have the role) and a "Verify here" button. When they get the Verified role later, the
licence on that post is redrawn as VERIFIED and the button is removed. Leave: in #🛫・flying-out, the licence greyed out and stamped REVOKED.
Off unless WELCOME_CARDS=on in .env (so it never doubles up with Welcomer). Post ids in welcome.json (gitignored).
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
from pathlib import Path

import discord

import licence

FILE = Path(__file__).resolve().parent / "welcome.json"
PINK, GREY = 0xFF286E, 0x5C5F66
JOIN, LEAVE = "flying-in", "flying-out"  # channel names end with these
VERIFY, RIDEOUTS, MAIN = "verification", "rideouts", "main-chat"
log = logging.getLogger("inspect-bot.welcome")


def load() -> dict:
    return json.loads(FILE.read_text()) if FILE.exists() else {}


def save(st: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1))
    tmp.replace(FILE)


def channel(g: discord.Guild, suffix: str):
    return next((c for c in g.text_channels if c.name.endswith("・" + suffix) or c.name == suffix), None)


def verified(member) -> bool:
    return any(r.name == "Verified" for r in member.roles)


def riders(g: discord.Guild) -> int:
    return sum(1 for m in g.members if not m.bot)


async def avatar(member) -> bytes:
    return await member.display_avatar.replace(size=512, static_format="png").read()


def welcome_embed(g: discord.Guild) -> tuple[discord.Embed, discord.ui.View]:
    ver, ride, main = channel(g, VERIFY), channel(g, RIDEOUTS), channel(g, MAIN)
    lines = ["## 🏍️ Welcome to DPGS",
             "You just rolled into **DontPanicGangers!**, a crew built on skill, loyalty and discipline. "
             "No shortcuts, no passengers. 💯",
             "### 🚦 Get rolling"]
    if ver:
        lines.append(f"✅ **Unlock the server** and find the server map: {ver.mention}")
    if ride:
        lines.append(f"🏍️ **Catch a rideout:** {ride.mention}")
    if main:
        lines.append(f"💬 **Say what's up:** {main.mention}")
    lines.append("### ⚔ DPGS — Earn your spot.")
    e = discord.Embed(colour=PINK, description="\n".join(lines))
    e.set_image(url="attachment://licence.png")
    v = discord.ui.View()
    if ver:
        v.add_item(discord.ui.Button(label="Verify here", emoji="✅", url=ver.jump_url))
    return e, v


class Welcome:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.st = load()

    async def card(self, member, number: int, status: str, revoked=False) -> discord.File:
        png = await asyncio.to_thread(licence.render, await avatar(member), member.display_name, number,
                                      (member.joined_at or discord.utils.utcnow()).date(), status, member.id,
                                      revoked, member.name)
        return discord.File(io.BytesIO(png), "licence.png")

    async def joined(self, member):
        ch = channel(member.guild, JOIN)
        if not self.enabled or not ch:
            return
        number = riders(member.guild)
        e, v = welcome_embed(member.guild)
        if verified(member):  # already verified when they join (rare): no button needed
            v = discord.utils.MISSING
        try:
            msg = await ch.send(f"Welcome {member.mention} 👋", embed=e, view=v,
                                file=await self.card(member, number, "verified" if verified(member) else "unverified"),
                                allowed_mentions=discord.AllowedMentions(users=True))
        except discord.HTTPException as ex:
            return log.warning("welcome: couldn't post for %s: %s", member, ex)
        self.st[str(member.id)] = {"msg": msg.id, "channel": ch.id, "number": number, "verified": verified(member)}
        save(self.st)

    async def verified_now(self, member):
        """They just got the Verified role: redraw their welcome licence as VERIFIED."""
        rec = self.st.get(str(member.id))
        if not self.enabled or not rec or rec.get("verified"):
            return
        try:
            msg = await member.guild.get_channel(rec["channel"]).fetch_message(rec["msg"])
            e, _ = welcome_embed(member.guild)
            await msg.edit(embed=e, view=None,  # verified: the "Verify here" button goes
                           attachments=[await self.card(member, rec["number"], "verified")])
        except (discord.HTTPException, AttributeError) as ex:
            return log.warning("welcome: couldn't update %s's licence: %s", member, ex)
        rec["verified"] = True
        save(self.st)

    async def left(self, member):
        ch = channel(member.guild, LEAVE)
        if not self.enabled or not ch:
            return
        rec = self.st.pop(str(member.id), None)
        number = rec["number"] if rec else riders(member.guild) + 1
        left_now = riders(member.guild)
        e = discord.Embed(colour=GREY, description=f"🛫 **{member.display_name}** has flown out. Licence revoked. "
                                                   f"{left_now} riders left.")
        e.set_image(url="attachment://licence.png")
        try:
            await ch.send(embed=e, file=await self.card(member, number, "verified", revoked=True),
                          allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException as ex:
            log.warning("welcome: couldn't post the leave for %s: %s", member, ex)
        save(self.st)
