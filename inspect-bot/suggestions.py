"""Suggestions (2026-11-28, Shane): a clean, button-only suggestions channel for DPGS. No commands.

Members press "Make a suggestion" in #💡・suggestions (they can't type there) and fill in a form: category, idea, why
(30+ characters), what would change. Limits: Verified, 7+ days in the server, one a day (Higher Ups and above skip these).
Every idea goes to the private #🔒・suggestion-queue first; staff (Higher Ups and every role above it) press
Post it / Bin it / Already suggested / Pass to BLS. Posted ideas get a card with 👍/👎 (one vote each) and a thread.
After 7 days voting closes: +5 or more is 🔥 Popular (flagged in the queue), otherwise 💤 and the thread is archived.
Staff then mark Accepted / In progress / Denied from the queue card. BLS ideas can be passed to #🎮・bls-suggestions
(private, Higher Ups and above) with the vote count, for the member who moderates in Bike Life Society.
The suggester gets a DM at each step. State: suggestions.json (gitignored).

Buttons carry their own ids (custom_id "sg:<action>:<number>"), so they keep working after a restart.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from pathlib import Path

import discord

FILE = Path(__file__).resolve().parent / "suggestions.json"
PUBLIC, QUEUE, BLS = "suggestions", "suggestion-queue", "bls-suggestions"  # channel names end with these
STAFF_FLOOR = "Higher Ups"  # this role and every role above it count as staff
MIN_DAYS, PER_DAY_SECS, VOTE_DAYS, POPULAR = 7, 86400, 7, 5
MIN_WHY = 30
# Member ids that skip the limits without being staff, for testing (.env SUGGEST_SKIP_LIMITS, comma-separated)
def skip_ids() -> set[int]:  # read when used: bot.py loads .env after importing this module
    return {int(x) for x in os.environ.get("SUGGEST_SKIP_LIMITS", "").split(",") if x.strip().isdigit()}
CATEGORIES = {
    "discord": "💬 Discord server", "rideouts": "🏍️ Rideouts & events", "ranks": "🏆 Ranks & tryouts",
    "bls": "🎮 BLS", "other": "✨ Other",
}
STATUS = {  # status -> (label on the card, colour)
    "queued": ("⏳ Waiting for staff", 0x8B8D98), "open": ("🗳️ Voting open", 0xFF286E),
    "popular": ("🔥 Popular", 0xF5A524), "quiet": ("💤 Not enough support", 0x5C5F66),
    "accepted": ("✅ Accepted", 0x30A46C), "progress": ("🛠️ In progress", 0x3B82F6),
    "denied": ("❌ Denied", 0xE5484D), "bls": ("📨 Passed to BLS", 0x8E4EC6),
    "binned": ("🗑️ Binned", 0x5C5F66), "duplicate": ("🔁 Already suggested", 0x5C5F66),
}
log = logging.getLogger("inspect-bot.suggestions")


# --- state --------------------------------------------------------------------
def load() -> dict:
    return json.loads(FILE.read_text()) if FILE.exists() else {"next": 1, "items": {}, "last": {}}


def save(st: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False))
    tmp.replace(FILE)


def can_submit(st: dict, member, now: float, staff: bool) -> str | None:
    """None if this member may send a suggestion now, else the reason they can't (shown only to them)."""
    if staff or member.id in skip_ids():
        return None
    if not any(r.name == "Verified" for r in member.roles):
        return "Verify first in ✅・verification, then you can make suggestions."
    joined = member.joined_at.timestamp() if member.joined_at else now
    if now - joined < MIN_DAYS * 86400:
        days = int(-(-(joined + MIN_DAYS * 86400 - now) // 86400))  # rounded up
        return f"You can make suggestions once you've been here {MIN_DAYS} days ({plural(days, 'day')} to go)."
    last = st["last"].get(str(member.id), 0)
    if now - last < PER_DAY_SECS:
        hours = int(-(-(last + PER_DAY_SECS - now) // 3600))  # rounded up
        return f"One suggestion a day. You can make another in {plural(hours, 'hour')}."
    return None


def vote(item: dict, uid: int, way: int) -> int:
    """Press 👍 (1) or 👎 (-1): a second press of the same takes the vote back, the other one switches it."""
    votes = item.setdefault("votes", {})
    if votes.get(str(uid)) == way:
        del votes[str(uid)]
        return 0
    votes[str(uid)] = way
    return way


def tally(item: dict) -> tuple[int, int]:
    v = item.get("votes", {}).values()
    return sum(1 for x in v if x > 0), sum(1 for x in v if x < 0)


def close_due(st: dict, now: float) -> list[dict]:
    """Close voting on posted ideas older than VOTE_DAYS: popular (+POPULAR or more) or quiet. Returns those closed."""
    done = []
    for item in st["items"].values():
        if item["status"] == "open" and now - item["posted"] >= VOTE_DAYS * 86400:
            up, down = tally(item)
            item["status"] = "popular" if up - down >= POPULAR else "quiet"
            item["closed"] = now
            done.append(item)
    return done


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# --- what it looks like -------------------------------------------------------
def card(item: dict, guild: discord.Guild, staff_view: bool = False) -> discord.Embed:
    label, colour = STATUS[item["status"]]
    e = discord.Embed(title=f"💡 #{item['n']} · {CATEGORIES[item['cat']]}", colour=colour,
                      description=f"### {item['idea']}\n{item['why']}")
    if item.get("change"):
        e.add_field(name="What would change", value=item["change"][:1000], inline=False)
    line = label
    if item.get("reason"):
        line += f": {item['reason']}"
    if item["status"] == "duplicate" and item.get("dupe_of"):
        line += f" (see #{item['dupe_of']})"
    if item["status"] in ("popular", "quiet", "accepted", "progress", "denied", "bls") and item.get("posted"):
        up, down = tally(item)
        line += f" · {up} 👍 / {down} 👎"
    e.add_field(name="Status", value=line, inline=False)
    who = guild.get_member(item["author"])
    name = who.display_name if who else "someone who left"
    e.set_footer(text=f"Suggested by {name}" + (f" · handled by {item['by']}" if staff_view and item.get("by") else ""))
    e.timestamp = dt.datetime.fromtimestamp(item["created"], dt.timezone.utc)
    return e


def btn(label, cid, style=discord.ButtonStyle.secondary, emoji=None, disabled=False):
    return discord.ui.Button(label=label, custom_id=cid, style=style, emoji=emoji, disabled=disabled)


def view(*buttons) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    for b in buttons:
        v.add_item(b)
    return v


def public_view(item: dict) -> discord.ui.View:
    up, down = tally(item)
    shut = item["status"] != "open"
    n = item["n"]
    return view(btn(str(up), f"sg:up:{n}", discord.ButtonStyle.success, "👍", shut),
                btn(str(down), f"sg:down:{n}", discord.ButtonStyle.danger, "👎", shut))


def queue_view(item: dict) -> discord.ui.View:
    n, s = item["n"], item["status"]
    if s == "queued":
        b = [btn("Post it", f"sg:post:{n}", discord.ButtonStyle.success, "✅"),
             btn("Bin it", f"sg:bin:{n}", discord.ButtonStyle.danger, "🗑️"),
             btn("Already suggested", f"sg:dupe:{n}", emoji="🔁")]
    elif s in ("open", "popular", "quiet", "progress"):
        b = [btn("Accepted", f"sg:accept:{n}", discord.ButtonStyle.success, "✅"),
             btn("In progress", f"sg:progress:{n}", discord.ButtonStyle.primary, "🛠️", s == "progress"),
             btn("Denied", f"sg:deny:{n}", discord.ButtonStyle.danger, "❌")]
    else:
        b = []
    if item["cat"] == "bls" and s not in ("bls", "binned", "duplicate", "denied"):
        b.append(btn("Pass to BLS", f"sg:pass:{n}", discord.ButtonStyle.primary, "📨"))
    return view(*b)


PANEL_TEXT = ("## 💡 Got an idea for DPGS?\n"
              "Ideas for our **Discord**, **rideouts & events**, **ranks & tryouts**, or **Bike Life Society**.\n"
              "1. Press the button and fill in the form. Say *why* it would help.\n"
              "2. Staff check every idea before it's posted here.\n"
              "3. Vote 👍 / 👎 and chat in the thread. After 7 days the best ones go to staff.\n"
              "-# BLS ideas go to BLS staff through our in-game mod. We can't promise they'll be added, that's up to BLS. "
              "Verified members, 7+ days in the server, one suggestion a day.")


def panel_view() -> discord.ui.View:
    return view(btn("Make a suggestion", "sg:new:0", discord.ButtonStyle.primary, "💡"))


# --- forms ----------------------------------------------------------------------
class SuggestForm(discord.ui.Modal, title="Make a suggestion"):
    def __init__(self, box: "Suggestions"):
        super().__init__(timeout=900)
        self.box = box
        self.cat = discord.ui.Select(placeholder="Pick one", options=[
            discord.SelectOption(label=v.split(" ", 1)[1], value=k, emoji=v.split(" ", 1)[0]) for k, v in CATEGORIES.items()])
        self.idea = discord.ui.TextInput(label="Your idea", max_length=100, placeholder="One line, e.g. Sunday night rideouts")
        self.why = discord.ui.TextInput(label="Why would it make DPGS better?", style=discord.TextStyle.paragraph,
                                        min_length=MIN_WHY, max_length=600)
        self.change = discord.ui.TextInput(label="What would need to change? (optional)", required=False,
                                           style=discord.TextStyle.paragraph, max_length=400)
        self.add_item(discord.ui.Label(text="What's it about?", component=self.cat))
        for item in (self.idea, self.why, self.change):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await self.box.submit(interaction, self.cat.values[0], self.idea.value.strip(), self.why.value.strip(),
                              self.change.value.strip())


class ReasonForm(discord.ui.Modal):
    def __init__(self, box: "Suggestions", action: str, n: int, title: str, label: str, required=False, placeholder=None):
        super().__init__(title=title, timeout=900)
        self.box, self.action, self.n = box, action, n
        self.text = discord.ui.TextInput(label=label, required=required, max_length=300, placeholder=placeholder)
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        await self.box.staff_action(interaction, self.action, self.n, self.text.value.strip())


# --- the feature ------------------------------------------------------------------
class Suggestions:
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.st = load()

    def channel(self, g: discord.Guild, suffix: str):
        return next((c for c in g.text_channels if c.name.endswith("・" + suffix) or c.name == suffix), None)

    def is_staff(self, member) -> bool:
        floor = discord.utils.get(member.guild.roles, name=STAFF_FLOOR)
        return member.guild_permissions.administrator or bool(floor and member.top_role >= floor)

    async def handle(self, interaction: discord.Interaction) -> bool:
        """Called for every interaction; True if it was one of ours."""
        cid = (interaction.data or {}).get("custom_id", "") if interaction.type == discord.InteractionType.component else ""
        if not cid.startswith("sg:"):
            return False
        _, action, n = cid.split(":")
        n = int(n)
        try:
            if action == "new":
                why_not = can_submit(self.st, interaction.user, discord.utils.utcnow().timestamp(),
                                     self.is_staff(interaction.user))
                if why_not:
                    await interaction.response.send_message(why_not, ephemeral=True)
                else:
                    await interaction.response.send_modal(SuggestForm(self))
            elif action in ("up", "down"):
                await self.vote(interaction, n, 1 if action == "up" else -1)
            elif not self.is_staff(interaction.user):
                await interaction.response.send_message("Only Higher Ups and above can do that.", ephemeral=True)
            elif action == "bin":
                await interaction.response.send_modal(ReasonForm(
                    self, "bin", n, "Bin it", "Reason (sent to them, optional)", placeholder=
                    "e.g. Already planned / Out of our hands / Not enough detail"))
            elif action == "deny":
                await interaction.response.send_modal(ReasonForm(self, "deny", n, "Deny it", "Reason (optional)"))
            elif action == "dupe":
                await interaction.response.send_modal(ReasonForm(
                    self, "dupe", n, "Already suggested", "Number of the original suggestion", True, "e.g. 4"))
            else:
                await self.staff_action(interaction, action, n, "")
        except Exception:
            log.exception("suggestions: %s failed", cid)
            if not interaction.response.is_done():
                await interaction.response.send_message("Something went wrong. Try again in a minute.", ephemeral=True)
        return True

    async def submit(self, interaction, cat, idea, why, change):
        g, now = interaction.guild, discord.utils.utcnow().timestamp()
        why_not = can_submit(self.st, interaction.user, now, self.is_staff(interaction.user))
        if why_not:
            return await interaction.response.send_message(why_not, ephemeral=True)
        queue = self.channel(g, QUEUE)
        n = self.st["next"]
        item = {"n": n, "author": interaction.user.id, "cat": cat, "idea": idea, "why": why, "change": change,
                "created": now, "status": "queued", "votes": {}}
        msg = await queue.send(embed=card(item, g, True), view=queue_view(item))
        item["queue_msg"] = msg.id
        self.st["items"][str(n)] = item
        self.st["next"] = n + 1
        self.st["last"][str(interaction.user.id)] = now
        save(self.st)
        await interaction.response.send_message(f"Sent to staff for review 👍 (suggestion #{n}). You'll get a DM when "
                                                "it's looked at.", ephemeral=True)

    async def vote(self, interaction, n, way):
        item = self.st["items"].get(str(n))
        if not item or item["status"] != "open":
            return await interaction.response.send_message("Voting on this one has closed.", ephemeral=True)
        if not any(r.name == "Verified" for r in interaction.user.roles):
            return await interaction.response.send_message("Verify first to vote.", ephemeral=True)
        vote(item, interaction.user.id, way)
        save(self.st)
        await interaction.response.edit_message(view=public_view(item))

    async def staff_action(self, interaction, action, n, text):
        g = interaction.guild
        item = self.st["items"].get(str(n))
        if not item:
            return await interaction.response.send_message("I can't find that suggestion.", ephemeral=True)
        allowed = {"post": ("queued",), "bin": ("queued",), "dupe": ("queued",),
                   "accept": ("open", "popular", "quiet", "progress"), "progress": ("open", "popular", "quiet"),
                   "deny": ("open", "popular", "quiet", "progress"),
                   "pass": ("queued", "open", "popular", "quiet", "progress", "accepted")}
        if item["status"] not in allowed.get(action, ()):
            return await interaction.response.send_message("Someone already handled this one.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        item["by"] = interaction.user.display_name
        dm = None
        if action == "post":
            await self.post_public(g, item)
            dm = f"Your suggestion **#{n}** ({item['idea']}) has been posted for voting in {self.channel(g, PUBLIC).mention}."
        elif action == "bin":
            item["status"], item["reason"] = "binned", text
            dm = f"Your suggestion **#{n}** ({item['idea']}) wasn't posted" + (f": {text}" if text else ".") + \
                 " Thanks for the idea all the same."
        elif action == "dupe":
            orig = text.lstrip("#").strip()
            if orig not in self.st["items"] or orig == str(n):
                return await interaction.followup.send(f"There's no suggestion #{orig}.", ephemeral=True)
            item["status"], item["dupe_of"] = "duplicate", int(orig)
            o = self.st["items"][orig]
            link = f" Vote on it here: {self.link(g, o)}" if o.get("public_msg") else ""
            dm = f"Your suggestion **#{n}** has already been suggested as #{orig} ({o['idea']}).{link}"
        elif action in ("accept", "progress", "deny"):
            item["status"] = {"accept": "accepted", "progress": "progress", "deny": "denied"}[action]
            item["reason"] = text if action == "deny" else item.get("reason")
            label = STATUS[item["status"]][0]
            dm = f"Update on your suggestion **#{n}** ({item['idea']}): **{label}**" + (f": {text}" if text else ".")
        elif action == "pass":
            if item["status"] == "queued":  # passed straight away, without a public vote
                item["posted"] = None
            await self.pass_to_bls(g, item, interaction.user)
            item["status"] = "bls"
            dm = f"Your BLS suggestion **#{n}** ({item['idea']}) has been passed to our in-game mod for BLS staff. " \
                 "It's up to BLS whether it's added."
        save(self.st)
        await self.refresh(g, item)
        note = await self.dm(g, item, dm)
        await interaction.followup.send(f"Done: #{n} is now **{STATUS[item['status']][0]}**.{note}", ephemeral=True)

    async def post_public(self, g, item):
        item["status"], item["posted"] = "open", discord.utils.utcnow().timestamp()
        msg = await self.channel(g, PUBLIC).send(embed=card(item, g), view=public_view(item))
        item["public_msg"] = msg.id
        try:
            thread = await msg.create_thread(name=f"💬 #{item['n']} {item['idea']}"[:100], auto_archive_duration=10080)
            item["thread"] = thread.id
        except discord.HTTPException as e:
            log.warning("suggestions: no thread for #%s: %s", item["n"], e)

    async def pass_to_bls(self, g, item, staff):
        e = card(item, g)
        up, down = tally(item)
        backing = f"DPGS backs this: {up} 👍 / {down} 👎" if item.get("posted") else "Passed straight away by staff (no vote)"
        await self.channel(g, BLS).send(f"📨 **For BLS staff**, passed on by {staff.mention}. {backing}.", embed=e,
                                        allowed_mentions=discord.AllowedMentions.none())

    def link(self, g, item) -> str:
        return f"https://discord.com/channels/{g.id}/{self.channel(g, PUBLIC).id}/{item['public_msg']}"

    async def refresh(self, g, item):
        """Redraw the queue card and the public card after a change."""
        try:
            qm = await self.channel(g, QUEUE).fetch_message(item["queue_msg"])
            await qm.edit(embed=card(item, g, True), view=queue_view(item))
        except discord.HTTPException as e:
            log.warning("suggestions: queue card #%s: %s", item["n"], e)
        if item.get("public_msg"):
            try:
                pm = await self.channel(g, PUBLIC).fetch_message(item["public_msg"])
                await pm.edit(embed=card(item, g), view=public_view(item))
            except discord.HTTPException as e:
                log.warning("suggestions: public card #%s: %s", item["n"], e)

    async def dm(self, g, item, text) -> str:
        if not text:
            return ""
        who = g.get_member(item["author"])
        try:
            await who.send(text)
            return ""
        except (discord.HTTPException, AttributeError):
            return " (Couldn't DM them: DMs closed or they left.)"

    async def tick(self, g):
        """Hourly: close voting that has run VOTE_DAYS; flag popular ones in the queue, archive quiet threads."""
        done = close_due(self.st, discord.utils.utcnow().timestamp())
        if not done:
            return
        save(self.st)
        for item in done:
            await self.refresh(g, item)
            if item["status"] == "popular":
                up, down = tally(item)
                await self.channel(g, QUEUE).send(f"🔥 **#{item['n']} is popular** ({up} 👍 / {down} 👎): {item['idea']}. "
                                                  "Decide on its card above.")
            if item.get("thread"):
                try:
                    t = g.get_thread(item["thread"]) or await g.fetch_channel(item["thread"])
                    await t.edit(archived=True)
                except discord.HTTPException as e:
                    log.warning("suggestions: archive thread #%s: %s", item["n"], e)

    async def ensure_panel(self, g):
        """Post the pinned panel in the public channel once (and again if it was deleted)."""
        ch = self.channel(g, PUBLIC)
        if not ch:
            return
        if self.st.get("panel"):
            try:
                await ch.fetch_message(self.st["panel"])
                return
            except discord.NotFound:
                pass
        msg = await ch.send(PANEL_TEXT, view=panel_view())
        try:
            await msg.pin()
        except discord.HTTPException:
            pass  # pinning needs Manage Messages (Pin Messages); the panel is first in the channel anyway
        self.st["panel"] = msg.id
        save(self.st)
