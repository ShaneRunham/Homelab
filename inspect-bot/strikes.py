"""Rideout strikes (2026-11-28, Shane): a staff record of who broke the rideout rules. No commands.

Staff (Higher Ups and every role above it) long-press / right-click a member > Apps > "⚠️ Give strike", pick the rule
broken, add a note and (optionally) which ride. Each strike is posted in #🔒・strike-log with ↩️ Remove and 📋 Record.
Strikes expire after 60 days. The member gets a DM: 1 = warning, 2 = final warning. At 3+ active strikes the log pings
Higher Ups: 3 = sit out the next rideout, 4+ = demotion or removal. Staff carry out the punishment, the bot only keeps
the record. #📜・rideout-rules holds the rules card. State: strikes.json (gitignored).

Buttons carry their own ids (custom_id "stk:<action>:<number>"), so they keep working after a restart.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import discord

from suggestions import STAFF_FLOOR

FILE = Path(__file__).resolve().parent / "strikes.json"
LOG, RULES_CH = "strike-log", "rideout-rules"  # channel names end with these
EXPIRE_DAYS = 60
RED, AMBER, GREY = 0xE5484D, 0xF5A524, 0x5C5F66
RULES = {  # key -> (short name, the rule as written on the rules card)
    "lead": ("Follow the lead", "The host sets the route and the pace."),
    "formation": ("Stay in formation", "No racing ahead or wandering off on your own."),
    "ramming": ("No ramming or griefing", "Not crew, not randoms, not anyone."),
    "late": ("Be on time", "Late? Catch up quietly, don't hold the ride up."),
    "host": ("Host's word is final", "Arguments go to staff after the ride, not in-game."),
    "respect": ("Represent DPGS", "No toxicity in chat or voice."),
}
log = logging.getLogger("inspect-bot.strikes")


# --- state and rules ------------------------------------------------------------
def load() -> dict:
    return json.loads(FILE.read_text()) if FILE.exists() else {"next": 1, "items": {}}


def save(st: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False))
    tmp.replace(FILE)


def active(st: dict, member_id: int, now: float) -> list[dict]:
    """This member's strikes that aren't removed or older than 60 days, oldest first."""
    cut = now - EXPIRE_DAYS * 86400
    return sorted((s for s in st["items"].values()
                   if s["member"] == member_id and not s.get("removed") and s["at"] > cut), key=lambda s: s["at"])


def step(count: int) -> tuple[str, bool]:
    """What this many active strikes means, and whether staff should be pinged."""
    if count <= 1:
        return "Warning", False
    if count == 2:
        return "Final warning", False
    if count == 3:
        return "Sit out the next rideout", True
    return "Demotion or removal: staff decide", True


def rules_text() -> str:
    lines = ["## 📜 Rideout rules", "Ride like DPGS. Break these and you get a strike."]
    lines += [f"{i}. **{name}.** {text}" for i, (name, text) in enumerate(RULES.values(), 1)]
    lines += ["### ⚠️ Strikes",
              "**1** warning · **2** final warning · **3** sit out the next rideout · **4** demotion or removal",
              f"-# Strikes expire after {EXPIRE_DAYS} days. Think one's unfair? Message a Higher Up.",
              "### ⚔ DPGS — Earn your spot."]
    return "\n".join(lines)


# --- display -----------------------------------------------------------------------
def card(s: dict, g: discord.Guild, count: int) -> discord.Embed:
    who = g.get_member(s["member"])
    label, _ = step(count)
    e = discord.Embed(colour=GREY if s.get("removed") else (RED if count >= 3 else AMBER),
                      title=f"⚠️ Strike #{s['n']} · {RULES[s['rule']][0]}",
                      description=f"**{who.mention if who else s.get('name', 'someone who left')}**\n{s['note']}")
    if s.get("ride"):
        e.add_field(name="Ride", value=s["ride"][:200], inline=True)
    e.add_field(name="Active strikes", value=f"{count} · {label}", inline=True)
    if s.get("removed"):
        e.add_field(name="Removed", value=f"by {s['removed']}" + (f": {s['why']}" if s.get("why") else ""), inline=False)
    e.set_footer(text=f"Given by {s['by']}")
    e.timestamp = dt.datetime.fromtimestamp(s["at"], dt.timezone.utc)
    return e


def log_view(s: dict) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(discord.ui.Button(label="Remove", emoji="↩️", custom_id=f"stk:remove:{s['n']}",
                                 disabled=bool(s.get("removed"))))
    v.add_item(discord.ui.Button(label="Record", emoji="📋", custom_id=f"stk:record:{s['n']}"))
    return v


def record_text(st: dict, member_id: int, name: str, now: float) -> str:
    mine = sorted((s for s in st["items"].values() if s["member"] == member_id), key=lambda s: s["at"], reverse=True)
    if not mine:
        return f"**{name}** has a clean record. 🏍️"
    act = active(st, member_id, now)
    lines = [f"## 📋 {name}", f"**{len(act)} active** · {step(len(act))[0] if act else 'nothing active'} · "
                              f"{len(mine)} ever"]
    for s in mine[:15]:
        state = "removed" if s.get("removed") else ("expired" if s not in act else "active")
        lines.append(f"`#{s['n']}` <t:{int(s['at'])}:d> **{RULES[s['rule']][0]}** ({state}): {s['note'][:80]}")
    return "\n".join(lines)


def dm_text(s: dict, count: int, guild_name: str) -> str:
    label, _ = step(count)
    text = (f"⚠️ **You got a rideout strike in {guild_name}.**\n"
            f"**Rule:** {RULES[s['rule']][0]}. {RULES[s['rule']][1]}\n**What happened:** {s['note']}\n"
            f"**Active strikes:** {count} · **{label}**\n")
    if count == 1:
        text += "This is a warning. Keep it clean and it expires in 60 days.\n"
    elif count == 2:
        text += "This is your final warning. One more and you sit out the next rideout.\n"
    else:
        text += "Staff will be in touch about what happens next.\n"
    return text + "-# Think this is unfair? Message a Higher Up."


# --- forms ---------------------------------------------------------------------------
class StrikeForm(discord.ui.Modal):
    def __init__(self, box: "Strikes", member: discord.Member):
        super().__init__(title=f"Strike for {member.display_name}"[:45], timeout=900)
        self.box, self.member = box, member
        self.rule = discord.ui.Select(placeholder="Pick one", options=[
            discord.SelectOption(label=name, value=k, description=text[:100]) for k, (name, text) in RULES.items()])
        self.note = discord.ui.TextInput(label="What happened?", style=discord.TextStyle.paragraph, min_length=5,
                                         max_length=300, placeholder="e.g. Kept ramming riders at the docks")
        self.ride = discord.ui.TextInput(label="Which ride? (optional)", required=False, max_length=100,
                                         placeholder="e.g. Sunday night rideout")
        self.add_item(discord.ui.Label(text="Which rule did they break?", component=self.rule))
        self.add_item(self.note)
        self.add_item(self.ride)

    async def on_submit(self, interaction: discord.Interaction):
        await self.box.give(interaction, self.member, self.rule.values[0], self.note.value.strip(),
                            self.ride.value.strip())


class RemoveForm(discord.ui.Modal, title="Remove strike"):
    def __init__(self, box: "Strikes", n: int):
        super().__init__(timeout=900)
        self.box, self.n = box, n
        self.why = discord.ui.TextInput(label="Why? (optional)", required=False, max_length=200,
                                        placeholder="e.g. Wrong person / Appeal accepted")
        self.add_item(self.why)

    async def on_submit(self, interaction: discord.Interaction):
        await self.box.remove(interaction, self.n, self.why.value.strip())


# --- the feature -------------------------------------------------------------------
class Strikes:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.st = load()

    def channel(self, g: discord.Guild, suffix: str):
        return next((c for c in g.text_channels if c.name.endswith("・" + suffix) or c.name == suffix), None)

    def is_staff(self, member) -> bool:
        floor = discord.utils.get(member.guild.roles, name=STAFF_FLOOR)
        return member.guild_permissions.administrator or bool(floor and member.top_role >= floor)

    async def open_form(self, interaction: discord.Interaction, member: discord.Member):
        """The "⚠️ Give strike" app (member menu)."""
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("Only Higher Ups and above can give strikes.", ephemeral=True)
        if member.bot or member == interaction.user:
            return await interaction.response.send_message("You can't strike a bot or yourself.", ephemeral=True)
        await interaction.response.send_modal(StrikeForm(self, member))

    async def handle(self, interaction: discord.Interaction) -> bool:
        """Called for every interaction; True if it was one of ours."""
        cid = (interaction.data or {}).get("custom_id", "") if interaction.type == discord.InteractionType.component else ""
        if not cid.startswith("stk:"):
            return False
        _, action, n = cid.split(":")
        try:
            if not self.is_staff(interaction.user):
                await interaction.response.send_message("Only Higher Ups and above can do that.", ephemeral=True)
            elif action == "remove":
                await interaction.response.send_modal(RemoveForm(self, int(n)))
            elif action == "record":
                s = self.st["items"][n]
                who = interaction.guild.get_member(s["member"])
                await interaction.response.send_message(record_text(
                    self.st, s["member"], who.display_name if who else s.get("name", "?"),
                    discord.utils.utcnow().timestamp()), ephemeral=True)
        except Exception:
            log.exception("strikes: %s failed", cid)
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went wrong. Try again in a minute.", ephemeral=True)
        return True

    async def give(self, interaction, member, rule, note, ride):
        g, now = interaction.guild, discord.utils.utcnow().timestamp()
        n = self.st["next"]
        s = {"n": n, "member": member.id, "name": member.display_name, "rule": rule, "note": note, "ride": ride,
             "by": interaction.user.display_name, "at": now}
        self.st["items"][str(n)] = s
        self.st["next"] = n + 1
        save(self.st)
        count = len(active(self.st, member.id, now))
        label, ping = step(count)
        ch = self.channel(g, LOG)
        if ch:
            hu = discord.utils.get(g.roles, name=STAFF_FLOOR)
            text = f"🚨 {hu.mention if hu else 'Staff'}: **{member.display_name}** is on {count} strikes. **{label}.**" \
                if ping else None
            msg = await ch.send(text, embed=card(s, g, count), view=log_view(s),
                                allowed_mentions=discord.AllowedMentions(roles=[hu] if hu else False))
            s["log"] = msg.id
            save(self.st)
        try:
            await member.send(dm_text(s, count, g.name))
            told = "They've been sent a DM."
        except discord.HTTPException:
            told = "Their DMs are closed, so tell them yourself."
        await interaction.response.send_message(
            f"⚠️ Strike #{n} given to **{member.display_name}** ({count} active · {label}). {told}", ephemeral=True)

    async def remove(self, interaction, n: int, why: str):
        s = self.st["items"].get(str(n))
        if not s or s.get("removed"):
            return await interaction.response.send_message("That strike is already removed.", ephemeral=True)
        s["removed"], s["why"] = interaction.user.display_name, why
        save(self.st)
        count = len(active(self.st, s["member"], discord.utils.utcnow().timestamp()))
        await interaction.response.edit_message(content=None, embed=card(s, interaction.guild, count), view=log_view(s))
        who = interaction.guild.get_member(s["member"])
        if who:
            try:
                await who.send(f"↩️ Your rideout strike in {interaction.guild.name} "
                               f"(**{RULES[s['rule']][0]}**) was removed. You're on {count} active.")
            except discord.HTTPException:
                pass
