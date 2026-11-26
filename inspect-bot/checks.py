"""The inspection itself: looks at a server's roles, channels, bots and settings and returns findings.
Pure reading: nothing here calls Discord, it only looks at the objects discord.py already has in memory.
AutoMod rules and webhooks need extra API calls, so bot.py fetches them and passes them in (None = not allowed)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import discord

RED, AMBER, GREEN, INFO = "red", "amber", "green", "info"
ICON = {RED: "🔴", AMBER: "🟠", GREEN: "🟢", INFO: "ℹ️"}
ORDER = [RED, AMBER, INFO, GREEN]

# Permissions that can wreck a server in the wrong hands
DANGEROUS = {
    "administrator": "Administrator",
    "manage_guild": "Manage Server",
    "manage_roles": "Manage Roles",
    "manage_channels": "Manage Channels",
    "manage_webhooks": "Manage Webhooks",
    "ban_members": "Ban",
    "mention_everyone": "Mention @everyone",
}
# What makes a role "staff" (for the bot-above-staff check)
STAFF_PERMS = ("administrator", "manage_guild", "ban_members", "kick_members", "moderate_members")
VERIFY_BOTS = ("rover", "bloxlink", "rowifi", "verify")
DEAD_DAYS = 90
QUIET_DAYS = 14  # activity: members with no message or voice for this long
TEXT_TYPES = (discord.ChannelType.text, discord.ChannelType.news, discord.ChannelType.forum)


@dataclass
class Section:
    title: str
    findings: list[tuple[str, str]] = field(default_factory=list)

    def add(self, level: str, text: str):
        self.findings.append((level, text))

    @property
    def worst(self) -> str:
        levels = {lvl for lvl, _ in self.findings} or {GREEN}
        return next(lvl for lvl in ORDER if lvl in levels)


def perm_names(perms: discord.Permissions) -> list[str]:
    if perms.administrator:
        return ["Administrator"]
    return [label for key, label in DANGEROUS.items() if getattr(perms, key)]


def humans(role: discord.Role) -> list[discord.Member]:
    return [m for m in role.members if not m.bot]


def is_staff_role(role: discord.Role) -> bool:
    return not role.managed and not role.is_default() and any(getattr(role.permissions, p) for p in STAFF_PERMS)


def roles_section(guild: discord.Guild) -> Section:
    s = Section("Roles and permissions")
    everyone = guild.default_role
    bad = perm_names(everyone.permissions)
    if bad:
        s.add(RED, f"**@everyone** has {', '.join(bad)}. Remove it: every member gets this.")
    for role in sorted(guild.roles, key=lambda r: -r.position):
        if role.is_default() or role.managed:
            continue
        perms = perm_names(role.permissions)
        if not perms:
            continue
        people = len(humans(role))
        bots = len(role.members) - people
        who = plural(people, "member") + (f", {plural(bots, 'bot')}" if bots else "")
        if role.permissions.administrator:
            level = RED if people > 3 else AMBER
            s.add(level, f"**{role.name}** has Administrator ({who}). Keep this to the owner and one "
                         f"trusted admin role; give staff specific permissions instead.")
        else:
            s.add(INFO, f"**{role.name}** ({who}): {', '.join(perms)}. Check everyone in it is trusted.")
    if not s.findings:
        s.add(GREEN, "No role has dangerous permissions.")
    return s


def bots_section(guild: discord.Guild) -> Section:
    s = Section("Bots")
    bots = [m for m in guild.members if m.bot and m != guild.me]
    staff_top = max((r.position for r in guild.roles if is_staff_role(r)), default=0)
    verify = []
    for bot in sorted(bots, key=lambda m: m.name.lower()):
        p = bot.guild_permissions
        if p.administrator:
            s.add(RED, f"**{bot.name}** has Administrator. If this bot is hacked, the whole server is. Give it only "
                       f"the permissions it needs.")
        if staff_top and bot.top_role.position > staff_top:
            s.add(AMBER, f"**{bot.name}**'s role is above every staff role, so a hacked bot could strip staff. "
                         f"Move it below the staff roles (but above any roles it hands out).")
        if any(k in bot.name.lower() for k in VERIFY_BOTS):
            verify.append(bot)
            missing = [n for k, n in (("manage_nicknames", "Manage Nicknames"), ("manage_roles", "Manage Roles"))
                       if not getattr(p, k)]
            if missing and not p.administrator:
                s.add(AMBER, f"**{bot.name}** (verification) is missing {', '.join(missing)}, so it can't rename "
                             f"members or give the Verified role.")
    if len(verify) > 1:
        s.add(AMBER, f"{len(verify)} verification bots ({', '.join(b.name for b in verify)}). They fight over "
                     f"nicknames and roles: keep one.")
    s.add(INFO, f"{plural(len(bots), 'other bot')}: {', '.join(b.name for b in bots) or 'none'}. Remove any nobody uses.")
    return s


def channels_section(guild: discord.Guild, now: dt.datetime) -> Section:
    s = Section("Channels")
    everyone = guild.default_role
    text = [c for c in guild.channels if c.type in TEXT_TYPES]

    open_to_all = [c for c in text if c.permissions_for(everyone).view_channel]
    verified = [r for r in guild.roles if "verified" in r.name.lower() and "unverified" not in r.name.lower()]
    if verified and len(open_to_all) > 3:
        s.add(AMBER, f"{plural(len(open_to_all), 'channel')} visible to unverified members (@everyone): "
                     f"{names(open_to_all)}. Hide them from @everyone and let **{verified[0].name}** see them.")
    elif open_to_all:
        s.add(INFO, f"Visible to @everyone: {names(open_to_all)}.")

    for c in guild.channels:
        for target, ow in c.overwrites.items():
            if not hasattr(target, "is_default") or target.managed:  # roles only, not single members
                continue
            allowed, _ = ow.pair()
            granted = [n for k, n in (("manage_channels", "Manage Channel"), ("manage_roles", "Manage Permissions"),
                                      ("manage_webhooks", "Manage Webhooks"), ("mention_everyone", "Mention @everyone"),
                                      ("manage_messages", "Manage Messages")) if getattr(allowed, k)]
            if not granted:
                continue
            if target.is_default():
                s.add(RED, f"**#{c.name}** gives **@everyone** {', '.join(granted)}. Remove that override.")
            elif not is_staff_role(target):
                s.add(AMBER, f"**#{c.name}** gives **{target.name}** (not a staff role) {', '.join(granted)}.")

    dead = []
    for c in text:
        last = getattr(c, "last_message_id", None)
        when = discord.utils.snowflake_time(last) if last else c.created_at
        if (now - when).days > DEAD_DAYS:
            dead.append(c)
    if dead:
        s.add(AMBER, f"{plural(len(dead), 'channel')} with no messages in {DEAD_DAYS}+ days: {names(dead)}. Archive or delete.")
    if not s.findings:
        s.add(GREEN, "Nothing wrong found in channel permissions.")
    return s


def cleanup_section(guild: discord.Guild, members_loaded: bool) -> Section:
    s = Section("Role cleanup")
    roles = [r for r in guild.roles if not r.is_default() and not r.managed]
    if members_loaded:
        empty = [r for r in roles if not r.members]
        if empty:
            s.add(AMBER, f"{plural(len(empty), 'role')} nobody has: {names(empty, '')}. Delete the ones you don't need.")
    else:
        s.add(INFO, "Couldn't load the member list, so empty roles weren't checked (turn on the Server Members "
                    "intent in the Developer Portal).")
    seen: dict[str, int] = {}
    for r in roles:
        seen[r.name.strip().lower()] = seen.get(r.name.strip().lower(), 0) + 1
    dupes = [n for n, k in seen.items() if k > 1]
    if dupes:
        s.add(AMBER, f"Roles with the same name: {', '.join(dupes)}. Merge or rename.")
    if not s.findings:
        s.add(GREEN, "No empty or duplicate roles.")
    return s


def safety_section(guild: discord.Guild, automod: list | None, webhooks: list | None) -> Section:
    s = Section("Safety settings")
    v = guild.verification_level
    if v == discord.VerificationLevel.none:
        s.add(RED, "Verification level is **None**. Set Medium or higher (Server Settings › Safety Setup).")
    elif v < discord.VerificationLevel.medium:
        s.add(AMBER, f"Verification level is **{v.name}**. Medium or higher stops most throwaway accounts.")
    else:
        s.add(GREEN, f"Verification level: {v.name}.")

    if guild.mfa_level == discord.MFALevel.disabled:
        s.add(RED, "**2FA isn't required for moderation.** Turn it on (Safety Setup › Permissions), so a "
                   "staff member's stolen password can't be used to ban or delete.")
    else:
        s.add(GREEN, "2FA required for moderation.")

    if guild.explicit_content_filter == discord.ContentFilter.disabled:
        s.add(AMBER, "Explicit media filter is off. Set it to filter all members.")

    if automod is None:
        s.add(INFO, "Can't see AutoMod rules (needs Manage Server). Check Safety Setup › AutoMod by hand.")
    elif not automod:
        s.add(AMBER, "No AutoMod rules. Turn on spam, mention-spam and link filters.")
    else:
        on = [r for r in automod if r.enabled]
        s.add(GREEN, f"{plural(len(on), 'AutoMod rule')} on: {', '.join(r.name for r in on) or 'none'}.")

    if webhooks is None:
        s.add(INFO, "Can't list webhooks (needs Manage Webhooks). Check Server Settings › Integrations › Webhooks.")
    elif webhooks:
        lines = ", ".join(f"{w.name} in #{w.channel.name if w.channel else '?'}" for w in webhooks)
        s.add(INFO, f"{plural(len(webhooks), 'webhook')}: {lines}. Delete any you don't recognise.")
    return s


def activity_section(guild: discord.Guild, seen: dict[int, dt.datetime], since: dt.datetime,
                     now: dt.datetime) -> Section:
    """seen: member id -> last message/voice time, tracked from `since`. Members never seen count from when tracking
    began or when they joined, whichever is later."""
    s = Section("Activity")
    first = since + dt.timedelta(days=QUIET_DAYS)
    if now < first:
        s.add(INFO, f"Tracking messages and voice since {since:%d %b}. The first list of quiet members comes "
                    f"on {first:%d %b}.")
        return s
    quiet = []
    for m in guild.members:
        if m.bot:
            continue
        last = seen.get(m.id) or max(since, m.joined_at or since)
        days = (now - last).days
        if days >= QUIET_DAYS:
            quiet.append((days, m, m.id in seen))
    if not quiet:
        s.add(GREEN, f"Everyone has talked or been in voice in the last {QUIET_DAYS} days.")
        return s
    quiet.sort(key=lambda q: -q[0])
    shown = ", ".join(f"{m.display_name} ({d}d{'' if was else '+'})" for d, m, was in quiet[:40])
    more = f" and {len(quiet) - 40} more" if len(quiet) > 40 else ""
    s.add(AMBER, f"**{plural(len(quiet), 'member')} quiet for {QUIET_DAYS}+ days** (no messages or voice): "
                 f"{shown}{more}. `+` = not seen since tracking began.")
    return s


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def names(items, prefix="#", limit=15) -> str:
    shown = ", ".join(f"{prefix}{x.name}" for x in items[:limit])
    return shown + (f" and {len(items) - limit} more" if len(items) > limit else "")


def inspect(guild: discord.Guild, *, automod=None, webhooks=None, members_loaded=True, now=None,
            activity=None) -> list[Section]:
    """activity: (seen, since) from the bot's tracker, or None to leave the Activity section out."""
    now = now or discord.utils.utcnow()
    sections = [
        safety_section(guild, automod, webhooks),
        roles_section(guild),
        bots_section(guild),
        channels_section(guild, now),
        cleanup_section(guild, members_loaded),
    ]
    if activity:
        sections.append(activity_section(guild, *activity, now))
    return sections
