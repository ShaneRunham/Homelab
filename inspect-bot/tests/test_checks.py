"""Offline tests for checks.py with stand-in server objects (no Discord connection)."""
import datetime as dt
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import discord

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import checks  # noqa: E402


class NS(SimpleNamespace):
    __hash__ = object.__hash__


NOW = dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc)


def role(name, pos, members=(), default=False, managed=False, **perms):
    r = NS(name=name, position=pos, members=list(members), managed=managed, permissions=discord.Permissions(**perms))
    r.is_default = lambda: default
    return r


def member(name, bot=False, top=None, id=0, joined=None, **perms):
    return NS(name=name, display_name=name, bot=bot, top_role=top, id=id, joined_at=joined,
              guild_permissions=discord.Permissions(**perms))


def channel(name, everyone_sees=True, last=NOW, overwrites=None):
    return NS(name=name, type=discord.ChannelType.text, overwrites=overwrites or {}, created_at=NOW,
              last_message_id=discord.utils.time_snowflake(last),
              permissions_for=lambda r: discord.Permissions(view_channel=everyone_sees))


def guild(roles, members=(), channels=(), me=None, **kw):
    g = NS(roles=roles, members=list(members), channels=list(channels), me=me,
           default_role=next(r for r in roles if r.is_default()),
           verification_level=kw.get("verification", discord.VerificationLevel.high),
           mfa_level=kw.get("mfa", discord.MFALevel.require_2fa),
           explicit_content_filter=kw.get("filter", discord.ContentFilter.all_members))
    return g


def levels(section):
    return [lvl for lvl, _ in section.findings]


class Checks(unittest.TestCase):
    def test_clean_server_is_green(self):
        everyone = role("@everyone", 0, default=True, view_channel=True)
        mod = role("Mod", 2, [member("a")], ban_members=True)
        g = guild([everyone, mod], channels=[channel("rules")])
        self.assertEqual(checks.inspect(g, automod=[NS(name="spam", enabled=True)], webhooks=[], now=NOW)[0].worst,
                         checks.GREEN)

    def test_everyone_with_admin_is_red(self):
        everyone = role("@everyone", 0, default=True, administrator=True)
        self.assertIn(checks.RED, levels(checks.roles_section(guild([everyone]))))

    def test_admin_role_with_many_people_is_red(self):
        everyone = role("@everyone", 0, default=True)
        admins = role("Admin", 3, [member(str(i)) for i in range(6)], administrator=True)
        self.assertEqual(checks.roles_section(guild([everyone, admins])).worst, checks.RED)

    def test_bot_with_admin_and_above_staff(self):
        everyone = role("@everyone", 0, default=True)
        staff = role("Mod", 2, kick_members=True)
        botrole = role("Shady", 5, managed=True, administrator=True)
        shady = member("Shady", bot=True, top=botrole, administrator=True)
        s = checks.bots_section(guild([everyone, staff, botrole], members=[shady]))
        self.assertEqual(levels(s)[:2], [checks.RED, checks.AMBER])

    def test_two_verification_bots(self):
        everyone = role("@everyone", 0, default=True)
        r = role("bots", 1, managed=True)
        bots = [member(n, bot=True, top=r, manage_nicknames=True, manage_roles=True) for n in ("RoVer", "Bloxlink")]
        s = checks.bots_section(guild([everyone, r], members=bots))
        self.assertTrue(any("2 verification bots" in t for _, t in s.findings))

    def test_rover_without_nickname_permission(self):
        everyone = role("@everyone", 0, default=True)
        r = role("RoVer", 1, managed=True)
        s = checks.bots_section(guild([everyone, r], members=[member("RoVer", bot=True, top=r)]))
        self.assertTrue(any("can't rename" in t for _, t in s.findings))

    def test_channels_open_to_unverified_and_dead(self):
        everyone = role("@everyone", 0, default=True)
        verified = role("Verified", 1)
        chans = [channel(f"c{i}") for i in range(5)] + [channel("old", last=NOW - dt.timedelta(days=200))]
        s = checks.channels_section(guild([everyone, verified], channels=chans), NOW)
        texts = " ".join(t for _, t in s.findings)
        self.assertIn("visible to unverified", texts)
        self.assertIn("#old", texts)

    def test_override_giving_everyone_webhooks_is_red(self):
        everyone = role("@everyone", 0, default=True)
        ow = discord.PermissionOverwrite(manage_webhooks=True)
        s = checks.channels_section(guild([everyone], channels=[channel("chat", overwrites={everyone: ow})]), NOW)
        self.assertEqual(s.worst, checks.RED)

    def test_empty_and_duplicate_roles(self):
        everyone = role("@everyone", 0, default=True)
        rs = [everyone, role("Fans", 1), role("fans ", 2, [member("x")])]
        s = checks.cleanup_section(guild(rs), members_loaded=True)
        texts = " ".join(t for _, t in s.findings)
        self.assertIn("nobody has: Fans", texts)
        self.assertIn("same name: fans", texts)

    def test_bots_counted_in_role(self):
        everyone = role("@everyone", 0, default=True)
        r = role("Bot", 2, [member("Dyno", bot=True), member("Arcane", bot=True)], manage_channels=True)
        texts = " ".join(t for _, t in checks.roles_section(guild([everyone, r])).findings)
        self.assertIn("0 members, 2 bots", texts)

    def test_activity_waits_for_two_weeks_of_tracking(self):
        everyone = role("@everyone", 0, default=True)
        g = guild([everyone], members=[member("a", id=1)])
        s = checks.activity_section(g, {}, NOW - dt.timedelta(days=3), NOW)
        self.assertEqual(levels(s), [checks.INFO])

    def test_activity_lists_quiet_members(self):
        everyone = role("@everyone", 0, default=True)
        since = NOW - dt.timedelta(days=30)
        talker, lurker, newbie = (member("talker", id=1), member("lurker", id=2),
                                  member("newbie", id=3, joined=NOW - dt.timedelta(days=2)))
        g = guild([everyone], members=[talker, lurker, newbie, member("Dyno", bot=True, id=4)])
        s = checks.activity_section(g, {1: NOW - dt.timedelta(days=1)}, since, NOW)
        text = s.findings[0][1]
        self.assertIn("lurker (30d+)", text)
        self.assertNotIn("talker", text)
        self.assertNotIn("newbie", text)
        self.assertNotIn("Dyno", text)

    def test_accepted_decisions(self):
        everyone = role("@everyone", 0, default=True)
        owner = role("Founder", 5, members=[member("a"), member("b")], administrator=True)
        s = checks.roles_section(guild([everyone, owner]), accepted_admin=("Founder",))
        self.assertEqual(levels(s), [checks.INFO])
        kept = role("Miami", 2)
        s = checks.cleanup_section(guild([everyone, kept, role("Old", 1)]), members_loaded=True, keep_roles=("Miami",))
        self.assertIn("Old", s.findings[0][1])
        self.assertNotIn("Miami", s.findings[0][1])

    def test_nickname_fits_discord_limit(self):
        import nicknames
        self.assertEqual(nicknames.nickname("Viper", "ybd_nebula"), "Viper (@ybd_nebula)")
        self.assertLessEqual(len(nicknames.nickname("DrivaDaveOfficial", "Jauntethebigboss")), 32)
        self.assertTrue(nicknames.SUFFIX.search("jdot (@Jscott12230)"))

    def test_safety_settings_off(self):
        everyone = role("@everyone", 0, default=True)
        g = guild([everyone], verification=discord.VerificationLevel.none, mfa=discord.MFALevel.disabled,
                  filter=discord.ContentFilter.disabled)
        s = checks.safety_section(g, automod=[], webhooks=None)
        self.assertEqual(levels(s).count(checks.RED), 2)
        self.assertIn(checks.INFO, levels(s))  # webhooks not visible


if __name__ == "__main__":
    unittest.main()
