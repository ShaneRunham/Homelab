#!/usr/bin/env python3
"""Read-only inspection bot for one Discord server. /inspect (or every Monday 10:00) checks roles, permissions, bots,
channels and safety settings and posts the report in #bot-report. It never changes anything in the server: the only
thing it ever sends is the report."""
import datetime as dt
import logging
import os
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

import checks

load_dotenv()
TOKEN = os.environ["INSPECT_BOT_TOKEN"]
GUILD_ID = int(os.environ.get("GUILD_ID") or 0)
REPORT_CHANNEL = os.environ.get("REPORT_CHANNEL", "bot-report")
WEEKLY = dt.time(10, 0, tzinfo=ZoneInfo("Europe/London"))
COLOUR = {checks.RED: 0xE5484D, checks.AMBER: 0xF5A524, checks.GREEN: 0x30A46C, checks.INFO: 0x8B8D98}
NO_PINGS = discord.AllowedMentions.none()

log = logging.getLogger("inspect-bot")


class InspectBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True  # for role member counts and bots; a privileged intent (Developer Portal)
        super().__init__(intents=intents, allowed_mentions=NO_PINGS)
        self.tree = app_commands.CommandTree(self)

    def guild(self) -> discord.Guild | None:
        if GUILD_ID:
            return self.get_guild(GUILD_ID)
        return self.guilds[0] if len(self.guilds) == 1 else None

    async def on_ready(self):
        if not weekly.is_running():
            weekly.start()
        await self.set_up()

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
        channel = discord.utils.get(g.text_channels, name=REPORT_CHANNEL)
        if not channel:
            raise RuntimeError(f"No #{REPORT_CHANNEL} channel I can see")
        if not g.chunked:
            await g.chunk()
        automod = await fetch_or_none(g.fetch_automod_rules())
        webhooks = await fetch_or_none(g.webhooks())
        sections = checks.inspect(g, automod=automod, webhooks=webhooks, members_loaded=g.chunked)
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
                    f"{checks.ICON[checks.GREEN]} {counts[checks.GREEN]} fine\n-# {who}. This bot only reads; "
                    f"it changes nothing.",
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


if __name__ == "__main__":
    bot.run(TOKEN, log_level=logging.INFO, root_logger=True)
