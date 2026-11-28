#!/usr/bin/env python3
"""Inspection bot for one Discord server. /inspect (or every Monday 10:00) checks roles, permissions, bots,
channels, safety settings and member activity and posts the report in #bot-report.
Two things it does besides reporting (2026-11-26):
- Activity: notes when each member last sent a message or joined voice (times only, never message content),
  kept in activity.json, so the report can list members quiet for 2+ weeks.
- Names: when Bloxlink renames someone to "RobloxName (@RobloxUser)", it renames them to
  "TheirServerName (@RobloxUser)", using the names remembered in names.json (see nicknames.py).
- Backup: every Sunday 04:00 it saves the whole layout to backups/auto-*.json (snapshot.py), keeping 12.
It changes nothing else: no roles, channels or messages."""
import datetime as dt
import json
import logging
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

import checks
import nicknames
import snapshot

load_dotenv()
TOKEN = os.environ["INSPECT_BOT_TOKEN"]
GUILD_ID = int(os.environ.get("GUILD_ID") or 0)
REPORT_CHANNEL = os.environ.get("REPORT_CHANNEL", "bot-report")
WEEKLY = dt.time(10, 0, tzinfo=ZoneInfo("Europe/London"))
BACKUP_AT = dt.time(4, 0, tzinfo=ZoneInfo("Europe/London"))  # Sundays: snapshot.py layout backup
WEEKLY_ON = os.environ.get("WEEKLY_REPORT", "on") != "off"  # Shane turned it off 2026-11-27; /inspect still works
COLOUR = {checks.RED: 0xE5484D, checks.AMBER: 0xF5A524, checks.GREEN: 0x30A46C, checks.INFO: 0x8B8D98}
NO_PINGS = discord.AllowedMentions.none()
# Decisions already made, so /inspect stops flagging them (comma-separated role names, in .env)
ACCEPT_ADMIN = [n.strip() for n in os.environ.get("ACCEPT_ADMIN_ROLES", "").split(",") if n.strip()]
KEEP_ROLES = [n.strip() for n in os.environ.get("KEEP_EMPTY_ROLES", "").split(",") if n.strip()]
ACTIVITY = Path(__file__).resolve().parent / "activity.json"

log = logging.getLogger("inspect-bot")


class InspectBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True  # for role member counts and bots; a privileged intent (Developer Portal)
        intents.guild_messages = True  # activity: when someone posts (not what; no message content intent)
        intents.voice_states = True  # activity: when someone joins voice
        super().__init__(intents=intents, allowed_mentions=NO_PINGS)
        self.tree = app_commands.CommandTree(self)
        data = json.loads(ACTIVITY.read_text()) if ACTIVITY.exists() else {}
        self.since = dt.datetime.fromisoformat(data["since"]) if "since" in data else discord.utils.utcnow()
        self.seen = {int(k): dt.datetime.fromisoformat(v) for k, v in data.get("seen", {}).items()}
        self.dirty = "since" not in data
        self.names = nicknames.load_names()

    def guild(self) -> discord.Guild | None:
        if GUILD_ID:
            return self.get_guild(GUILD_ID)
        return self.guilds[0] if len(self.guilds) == 1 else None

    async def on_ready(self):
        if WEEKLY_ON and not weekly.is_running():
            weekly.start()
        if not save_activity.is_running():
            save_activity.start()
        if not weekly_backup.is_running():
            weekly_backup.start()
        await self.set_up()
        await self.show_status()

    async def show_status(self):
        """Profile status: "Watching 41 riders 🏍️", updated as people join and leave."""
        g = self.guild()
        if g:
            n = sum(1 for m in g.members if not m.bot)
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                                 name=f"{n} riders 🏍️"))

    async def on_member_remove(self, member):
        if member.guild == self.guild():
            await self.show_status()

    # --- activity -------------------------------------------------------------
    def saw(self, member):
        if member.guild == self.guild() and not member.bot:
            self.seen[member.id] = discord.utils.utcnow()
            self.dirty = True

    async def on_message(self, message: discord.Message):
        if isinstance(message.author, discord.Member):
            self.saw(message.author)

    async def on_voice_state_update(self, member, before, after):
        if after.channel and after.channel != before.channel:
            self.saw(member)

    def save_activity(self):
        data = {"since": self.since.isoformat(), "seen": {str(k): v.isoformat() for k, v in self.seen.items()}}
        ACTIVITY.write_text(json.dumps(data))
        self.dirty = False

    # --- names ----------------------------------------------------------------
    async def on_member_join(self, member):
        if member.guild == self.guild() and not member.bot:
            self.remember(member)
            await self.show_status()

    def remember(self, member):
        """Keep the member's own server name, as long as it isn't a "(@roblox)" one."""
        if not nicknames.SUFFIX.search(member.display_name) and self.names.get(str(member.id)) != member.display_name:
            self.names[str(member.id)] = member.display_name
            nicknames.save_names(self.names)

    async def on_member_update(self, before, after):
        if after.bot or after.guild != self.guild() or before.nick == after.nick:
            return
        if not nicknames.SUFFIX.search(after.display_name):
            self.remember(after)  # they changed their own name: use it from now on
            return
        if "BLOXLINK_API_KEY" not in os.environ:
            return
        async with aiohttp.ClientSession() as s:  # trust Bloxlink's link, not whatever is in the nickname
            username = await nicknames.roblox_username(s, after.guild.id, after.id)
        if not username:
            return
        want = nicknames.nickname(nicknames.base_name(self.names, after), username)
        if after.nick != want:  # our own edit comes back here and stops at this check
            old = after.nick
            try:
                await after.edit(nick=want, reason="inspect-bot: ServerName (@RobloxUser)")
                log.info("Renamed %s: %r -> %r", after, old, want)
            except discord.HTTPException as e:
                log.warning("Couldn't rename %s: %s", after, e)

    async def on_guild_join(self, _guild):
        await self.set_up()  # invited while running: add /inspect straight away, no restart needed

    async def set_up(self):
        g = self.guild()
        if not g:
            log.warning("Not in the server yet (GUILD_ID=%s, in %d servers); waiting for the invite",
                        GUILD_ID, len(self.guilds))
            return
        self.tree.copy_global_to(guild=g)
        await self.tree.sync(guild=g)
        log.info("Ready in %s", g.name)

    async def report(self, g: discord.Guild, who: str) -> discord.TextChannel:
        channel = next((c for c in g.text_channels if REPORT_CHANNEL in c.name), None)  # survives an emoji prefix
        if not channel:
            raise RuntimeError(f"No #{REPORT_CHANNEL} channel I can see")
        if not g.chunked:
            await g.chunk()
        automod = await fetch_or_none(g.fetch_automod_rules())
        webhooks = await fetch_or_none(g.webhooks())
        sections = checks.inspect(g, automod=automod, webhooks=webhooks, members_loaded=g.chunked,
                                  activity=(self.seen, self.since), accepted_admin=ACCEPT_ADMIN,
                                  keep_roles=KEEP_ROLES)
        for embed in build_embeds(g, sections, who):
            await channel.send(embed=embed)
        return channel


async def fetch_or_none(coro):
    try:
        return await coro
    except discord.Forbidden:
        return None


def build_embeds(g: discord.Guild, sections: list[checks.Section], who: str) -> list[discord.Embed]:
    counts = {lvl: sum(1 for s in sections for l, _ in s.findings if l == lvl) for lvl in checks.ORDER}
    worst = next((lvl for lvl in (checks.RED, checks.AMBER) if counts[lvl]), checks.GREEN)
    summary = discord.Embed(
        title=f"Server inspection: {g.name}",
        description=f"{checks.ICON[checks.RED]} {counts[checks.RED]} to fix now · "
                    f"{checks.ICON[checks.AMBER]} {counts[checks.AMBER]} to look at · "
                    f"{checks.ICON[checks.GREEN]} {counts[checks.GREEN]} fine\n-# {who}. This report changes "
                    f"nothing; the bot only ever fixes Bloxlink nicknames.",
        colour=COLOUR[worst], timestamp=discord.utils.utcnow())
    out = [summary]
    for s in sections:
        lines = [f"{checks.ICON[l]} {t}" for l, t in sorted(s.findings, key=lambda f: checks.ORDER.index(f[0]))]
        out.append(discord.Embed(title=s.title, description=fit(lines), colour=COLOUR[s.worst]))
    return out


def fit(lines: list[str], limit: int = 4000) -> str:
    """Join lines, dropping the tail with a count if they don't fit in one embed."""
    out, used = [], 0
    for i, line in enumerate(lines):
        line = line if len(line) <= 1000 else line[:997] + "…"
        if used + len(line) + 1 > limit - 40:
            out.append(f"…and {len(lines) - i} more")
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out)


bot = InspectBot()


@bot.tree.command(description="Check the server's roles, permissions, bots, channels and safety settings")
@app_commands.default_permissions(manage_messages=True)
@app_commands.guild_only()
async def inspect(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        channel = await bot.report(interaction.guild, f"Asked for by {interaction.user.display_name}")
        await interaction.followup.send(f"Report posted in {channel.mention}.", ephemeral=True)
    except Exception as e:
        log.exception("inspect failed")
        await interaction.followup.send(f"Inspection failed: {e}", ephemeral=True)


@tasks.loop(time=WEEKLY)
async def weekly():
    if dt.datetime.now(WEEKLY.tzinfo).weekday() != 0:  # Mondays only
        return
    g = bot.guild()
    if g:
        try:
            await bot.report(g, "Weekly check")
        except Exception:
            log.exception("weekly report failed")


@tasks.loop(time=BACKUP_AT)
async def weekly_backup():
    if dt.datetime.now(BACKUP_AT.tzinfo).weekday() != 6:  # Sundays only
        return
    g = bot.guild()
    if g:
        try:
            if not g.chunked:
                await g.chunk()
            log.info("Layout backup saved: %s", snapshot.save(g).name)
        except Exception:
            log.exception("layout backup failed")


@tasks.loop(minutes=10)
async def save_activity():
    if bot.dirty:
        bot.save_activity()


if __name__ == "__main__":
    bot.run(TOKEN, log_level=logging.INFO, root_logger=True)
