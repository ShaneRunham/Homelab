#!/usr/bin/env python3
"""One-off fixes for the server after /inspect (2026-11-26). Separate from bot.py, which stays read-only.

    python fix.py <step> [<step> ...]            dry run: prints what would change, changes nothing
    python fix.py <step> [<step> ...] --apply    backs up, then applies
    python fix.py restore backups/<file>.json    puts permissions/settings back from a backup

Steps (run them in this order; the owner agrees to each first):
    mention      @everyone can't mention @everyone                                  (#1)
    personal     Mention @everyone off for BackWheelBandit, 🌊, Graphic designer     (#3)
    scouse       Scouse matic💯 cleared to a name/colour role                        (#3)
    staff        + and Key: Administrator → staff permissions                        (#2)
    bots         Dyno, Arcane, Jockie Music, Welcomer: Administrator → what they need (#4)
    safety       verification Medium, media filter for all members                   (#6, #7)
    automod      mention-spam + spam AutoMod rules                                    (#7)
    verified     create Verified, move RoVer under Staff, give Verified to every member
    verifychannel  create #verify in Flying in and out (see + /verify, no chat) with the how-to message
    flyingout    #flying-out read-only (Carl-bot and Welcomer can still post)
    lock         hide categories from @everyone, show to Verified; skips private channels and channels outside
                 categories (--open "name,name": a category holding one of these stays open)

Needs the bot to have Manage Roles, Manage Server and Manage Channels, with its role just under Founder.
"""
import asyncio
import datetime as dt
import json
import os
import sys
import traceback
from pathlib import Path

import discord
from dotenv import load_dotenv

load_dotenv()
HERE = Path(__file__).resolve().parent
P = discord.Permissions

DANGEROUS_OFF = dict(administrator=False, manage_guild=False, manage_roles=False, manage_channels=False,
                     manage_webhooks=False, mention_everyone=False)
STAFF_ON = dict(kick_members=True, ban_members=True, moderate_members=True, manage_messages=True,
                manage_nicknames=True, view_audit_log=True, mute_members=True, deafen_members=True, move_members=True)
BASIC = dict(view_channel=True, send_messages=True, embed_links=True, read_message_history=True)
BOT_PERMS = {
    "jockie music": P(**BASIC, connect=True, speak=True, use_voice_activation=True),
    "welcomer": P(**BASIC, attach_files=True, manage_roles=True),
    "arcane": P(**BASIC, manage_roles=True),
    "rover": P(**BASIC, manage_roles=True, manage_nicknames=True),
    "dyno": P(**BASIC, attach_files=True, add_reactions=True, manage_messages=True, manage_roles=True,
              manage_nicknames=True, kick_members=True, ban_members=True, moderate_members=True, view_audit_log=True),
}
# Everything risky is turned off on bot roles, then each bot gets back what it needs from BOT_PERMS
BOT_RISKY = ["administrator", "manage_guild", "manage_channels", "manage_webhooks", "mention_everyone", "manage_roles",
             "kick_members", "ban_members", "moderate_members", "manage_messages", "manage_nicknames",
             "manage_threads", "manage_expressions", "view_audit_log", "manage_events"]
PERSONAL = ["BackWheelBandit", "🌊", "Graphic designer / SAFE 🔒"]
VERIFY_TEXT = ("👋 **Welcome to DPGS!**\n"
               "To unlock the server, type `/verify` and link your Roblox account. "
               "Your nickname will change to your Roblox name.\n\n"
               "Changed your Roblox name? Type `/update`.")
AUTOMOD_EXEMPT = ["Founder", "Co Owner", "Staff", "Dyno", "Welcomer"]


def norm(s: str) -> str:
    return "".join(ch for ch in s.casefold() if not ch.isspace())


def find_role(g, name):
    want = norm(name)
    hits = [r for r in g.roles if norm(r.name) == want] or [r for r in g.roles if norm(r.name).startswith(want)]
    return hits[0] if len(hits) == 1 else None


def diff(before: P, after: P) -> str:
    on = [k for k, v in after if v and not getattr(before, k)]
    off = [k for k, v in before if v and not getattr(after, k)]
    return " ".join([f"+{k}" for k in on] + [f"-{k}" for k in off]) or "(no change)"


class Plan:
    """A list of (description, coroutine factory). Built from the live server, then printed or applied."""

    def __init__(self):
        self.items, self.problems = [], []

    def add(self, text, action):
        self.items.append((text, action))

    def role_perms(self, role, new: P):
        if role.permissions.value != new.value:
            self.add(f"Role {role.name}: {diff(role.permissions, new)}",
                     lambda: role.edit(permissions=new, reason="inspect-bot fix"))


async def build(g: discord.Guild, steps, open_names) -> Plan:
    plan = Plan()
    me = g.me

    def need(name):
        r = find_role(g, name)
        if not r:
            plan.problems.append(f"Role not found (or more than one match): {name}")
        elif r >= me.top_role:
            plan.problems.append(f"{r.name} is at or above my role: move Server Inspector above it first")
            return None
        return r

    if "mention" in steps:
        p = P(g.default_role.permissions.value)
        p.mention_everyone = False
        plan.role_perms(g.default_role, p)

    if "personal" in steps:
        for name in PERSONAL:
            if r := need(name):
                p = P(r.permissions.value)
                p.mention_everyone = False
                plan.role_perms(r, p)

    if "scouse" in steps:
        if r := need("Scouse matic"):
            plan.role_perms(r, P.none())

    if "staff" in steps:
        for name in ("+", "Key"):
            if r := need(name):
                p = P(r.permissions.value)
                p.update(**DANGEROUS_OFF, **STAFF_ON)
                plan.role_perms(r, p)

    if "bots" in steps:
        for m in g.members:
            key = m.name.casefold()
            if not m.bot or key not in BOT_PERMS:
                continue
            role = next((r for r in g.roles if r.tags and r.tags.bot_id == m.id), None)
            if not role:
                plan.problems.append(f"No own role found for bot {m.name}")
                continue
            if role >= me.top_role:
                plan.problems.append(f"{role.name} is at or above my role")
                continue
            p = P(role.permissions.value)
            p.update(**{k: False for k in BOT_RISKY})  # keep the harmless bits it has, drop the risky ones
            plan.role_perms(role, p | BOT_PERMS[key])
            other = [r.name for r in m.roles if r != role and r.permissions.administrator]
            if other:
                plan.problems.append(f"{m.name} also gets Administrator from {', '.join(other)}: fix that role too")
        missing = set(BOT_PERMS) - {m.name.casefold() for m in g.members if m.bot}
        if missing:
            plan.problems.append(f"Bots not found: {', '.join(sorted(missing))}")

    if "safety" in steps:
        if g.verification_level < discord.VerificationLevel.medium:
            plan.add(f"Verification level {g.verification_level.name} → medium",
                     lambda: g.edit(verification_level=discord.VerificationLevel.medium))
        if g.explicit_content_filter != discord.ContentFilter.all_members:
            plan.add(f"Explicit media filter {g.explicit_content_filter.name} → all_members",
                     lambda: g.edit(explicit_content_filter=discord.ContentFilter.all_members))

    if "automod" in steps:
        try:
            rules = await g.fetch_automod_rules()
        except discord.Forbidden:
            plan.problems.append("Can't read AutoMod rules: I need Manage Server")
            rules = None
    if "automod" in steps and rules is not None:
        have = {r.trigger.type for r in rules}
        exempt = [r for n in AUTOMOD_EXEMPT if (r := find_role(g, n))]
        T, A = discord.AutoModRuleTriggerType, discord.AutoModRuleAction
        if T.mention_spam not in have:
            plan.add("AutoMod: block messages with 5+ mentions and time out the sender for 10 minutes "
                     f"(exempt: {', '.join(r.name for r in exempt)})",
                     lambda: g.create_automod_rule(
                         name="Mention spam", event_type=discord.AutoModRuleEventType.message_send,
                         trigger=discord.AutoModTrigger(type=T.mention_spam, mention_limit=5),
                         actions=[A(custom_message="Too many mentions."), A(duration=dt.timedelta(minutes=10))],
                         enabled=True, exempt_roles=exempt, reason="inspect-bot fix"))
        if T.spam not in have:
            plan.add("AutoMod: block messages Discord flags as spam",
                     lambda: g.create_automod_rule(
                         name="Spam content", event_type=discord.AutoModRuleEventType.message_send,
                         trigger=discord.AutoModTrigger(type=T.spam), actions=[A()],
                         enabled=True, exempt_roles=exempt, reason="inspect-bot fix"))

    if "verified" in steps:
        verified = find_role(g, "Verified")
        rover = next((m for m in g.members if m.bot and m.name.casefold() == "rover"), None)
        rover_role = next((r for r in g.roles if rover and r.tags and r.tags.bot_id == rover.id), None)
        staff = find_role(g, "Staff")
        if not rover_role or not staff:
            plan.problems.append("RoVer's role or Staff not found")
        else:
            state = {}

            async def make_verified():
                state["v"] = verified or await g.create_role(name="Verified", permissions=P.none(),
                                                             reason="inspect-bot: RoVer verified role")
            plan.add("Create role Verified (no permissions)" if not verified else "Use existing role Verified",
                     make_verified)
            target = min(staff.position, me.top_role.position) - 1
            plan.add(f"Move RoVer's role from position {rover_role.position} to {target} (just under "
                     f"{'Staff' if staff.position <= me.top_role.position else me.top_role.name}), above every member role",
                     lambda: rover_role.edit(position=target, reason="inspect-bot: RoVer can rename"))
            people = [m for m in g.members if not m.bot and (not verified or verified not in m.roles)]

            async def give_all():
                for i, m in enumerate(people, 1):
                    await m.add_roles(state["v"], reason="inspect-bot: existing member, keep access")
                    if i % 25 == 0:
                        print(f"    {i}/{len(people)}")
            plan.add(f"Give Verified to {len(people)} existing members (bots left out)", give_all)

    if "lock" in steps:
        verified = find_role(g, "Verified")
        if not verified:
            plan.problems.append("No Verified role yet: run the verified step first")
        else:
            keep = {norm(n) for n in open_names}
            everyone = g.default_role
            for c in g.categories:
                if any(norm(ch.name).startswith(k) for ch in c.channels for k in keep):
                    plan.problems.append(f"Category {c.name} has an open channel in it: left as it is")
                    continue
                plan.add(f"Category {c.name}: @everyone can't see it, Verified can", lock_action(c, g, verified))
                for ch in c.channels:
                    if not ch.permissions_for(everyone).view_channel and ch.overwrites_for(everyone).view_channel is False:
                        plan.problems.append(f"#{ch.name} is already private: left as it is")
                    elif not ch.permissions_synced:
                        plan.add(f"  #{ch.name} (own permissions, kept): same", lock_action(ch, g, verified))
            # Channels outside categories (trap, bot-report, private ones) are never touched

    if "verifychannel" in steps:
        cat = next((c for c in g.categories if norm(c.name).startswith("flyingin")), None)
        rover = next((m for m in g.members if m.bot and m.name.casefold() == "rover"), None)
        if not cat or not rover:
            plan.problems.append("Category 'Flying in and out' or RoVer not found")
        elif any(norm(ch.name) in ("verify", "verification") for ch in g.channels):
            plan.problems.append("#verify already exists")
        else:
            ows = {g.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False,
                                                               send_messages_in_threads=False,
                                                               create_public_threads=False, add_reactions=False,
                                                               use_application_commands=True),
                   rover: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True),
                   me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True)}

            async def make_verify():
                ch = await g.create_text_channel("verification", category=cat, position=0, overwrites=ows,
                                                 topic="Type /verify to link your Roblox account and unlock the server",
                                                 reason="inspect-bot: RoVer verification channel")
                await ch.send(VERIFY_TEXT)
            plan.add(f"Create #verify at the top of {cat.name}: everyone sees it and can use /verify, can't chat; "
                     f"post the how-to message", make_verify)

    if "flyingout" in steps:
        ch = next((c for c in g.text_channels if norm(c.name).startswith("flying-out")), None)
        posters = [m for m in g.members if m.bot and m.name.casefold() in ("carl-bot", "welcomer")]
        if not ch:
            plan.problems.append("#flying-out not found")
        else:
            async def read_only():
                ow = ch.overwrites_for(g.default_role)
                ow.send_messages = ow.send_messages_in_threads = ow.create_public_threads = False
                await ch.set_permissions(g.default_role, overwrite=ow, reason="inspect-bot: read-only")
                for m in posters:
                    await ch.set_permissions(m, view_channel=True, send_messages=True, embed_links=True,
                                             reason="inspect-bot: can still post leave messages")
            plan.add(f"#{ch.name}: read-only for everyone; {', '.join(m.name for m in posters)} can still post",
                     read_only)
    return plan


def lock_action(ch, g, verified):
    """Adds to the existing overrides (so read-only channels stay read-only) instead of replacing them."""
    async def run():
        # Let Verified and this bot in first: hiding from @everyone first would hide the channel from the bot too
        for target, see in ((verified, True), (g.me, True), (g.default_role, False)):
            ow = ch.overwrites_for(target)
            ow.view_channel = see
            await ch.set_permissions(target, overwrite=ow, reason="inspect-bot: verify to see")
    return run


def backup(g: discord.Guild) -> Path:
    data = {
        "taken": dt.datetime.now().isoformat(timespec="seconds"), "guild": g.id,
        "verification_level": g.verification_level.value, "explicit_content_filter": g.explicit_content_filter.value,
        "roles": {str(r.id): {"name": r.name, "permissions": r.permissions.value, "position": r.position}
                  for r in g.roles},
        "overwrites": {str(c.id): {str(t.id): [o.pair()[0].value, o.pair()[1].value]
                                   for t, o in c.overwrites.items() if isinstance(t, discord.Role)}
                       for c in g.channels},
    }
    path = HERE / "backups" / f"{g.id}-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return path


async def restore(g: discord.Guild, path: Path):
    """Puts role permissions, guild settings and role overwrites back. Leaves AutoMod rules, the Verified role
    and role positions alone (delete/move those by hand if wanted)."""
    data = json.loads(path.read_text())
    for rid, r in data["roles"].items():
        role = g.get_role(int(rid))
        if role and role.permissions.value != r["permissions"] and role < g.me.top_role:
            print(f"Role {role.name}: {diff(role.permissions, P(r['permissions']))}")
            await role.edit(permissions=P(r["permissions"]), reason="inspect-bot restore")
    await g.edit(verification_level=discord.VerificationLevel(data["verification_level"]),
                 explicit_content_filter=discord.ContentFilter(data["explicit_content_filter"]))
    for cid, ows in data["overwrites"].items():
        ch = g.get_channel(int(cid))
        if not ch:
            continue
        for t, o in ch.overwrites.items():
            if isinstance(t, discord.Role) and str(t.id) not in ows:
                print(f"#{ch.name}: remove override for {t.name}")
                await ch.set_permissions(t, overwrite=None)
        for rid, (allow, deny) in ows.items():
            role = g.get_role(int(rid))
            want = discord.PermissionOverwrite.from_pair(P(allow), P(deny))
            if role and ch.overwrites_for(role) != want:
                print(f"#{ch.name}: put back override for {role.name}")
                await ch.set_permissions(role, overwrite=want)


async def main(args):
    apply = "--apply" in args
    open_names = []
    if "--open" in args:
        open_names = [n.strip() for n in args[args.index("--open") + 1].split(",") if n.strip()]
    steps = [a for a in args if not a.startswith("--") and a not in open_names and "," not in a]

    intents = discord.Intents.none()
    intents.guilds = intents.members = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            g = client.get_guild(int(os.environ["GUILD_ID"]))
            if not g.chunked:
                await g.chunk()
            if steps and steps[0] == "restore":
                await restore(g, Path(steps[1]))
                return
            plan = await build(g, set(steps), open_names)
            for p in plan.problems:
                print(f"⚠ {p}")
            print(f"\n{len(plan.items)} changes{'' if apply else ' (dry run: nothing changed)'}:")
            for text, _ in plan.items:
                print(f"  • {text}")
            if apply and plan.items:
                print(f"\nBackup: {backup(g)}")
                for text, action in plan.items:
                    try:
                        await action()
                        print(f"✓ {text}")
                    except discord.HTTPException as e:
                        print(f"✗ {text}: {e}")
        except Exception:
            traceback.print_exc()
        finally:
            await client.close()

    await client.start(os.environ["INSPECT_BOT_TOKEN"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    asyncio.run(main(sys.argv[1:]))
