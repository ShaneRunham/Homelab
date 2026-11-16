#!/usr/bin/env python3
"""Conversation agent for Home Assistant Assist: hands what HA's own intents don't catch to Claude.

Runs `claude -p` on Shane's Claude subscription. HA's custom integration `jarvis_claude` sends the HA user id with
each sentence, which picks the mode:
- Shane's login: FULL control, like the Discord bot's #claude: Claude Code's normal tools (shell, files) with the
  same safety check (permission mode auto), his CLAUDE.md notes, plus Home Assistant's MCP tools.
- Any other login (the tablet) or unknown: HOME only: just Home Assistant's MCP server (Assist API, the entities
  exposed to Assist). No shell, no files, no CLAUDE.md files.
HA's MCP server is reached as the non-admin, local-only HA user `jarvis` (token in ./token).
Each HA conversation_id maps to one Claude session, so follow-ups work for 10 minutes.
Listens on 127.0.0.1:10400 (Wyoming); runs in the JARVIS venv (needs the `wyoming` package)."""
import asyncio, json, os, shutil, signal, time, logging
from wyoming.asr import Transcript
from wyoming.event import Event
from wyoming.handle import Handled
from wyoming.info import Attribution, Describe, HandleModel, HandleProgram, Info
from wyoming.server import AsyncEventHandler, AsyncServer

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
WORKDIR = os.path.join(HERE, "claude-workdir")
MODEL = os.environ.get("JARVIS_MODEL", "sonnet")
FULL_USERS = {"a2e9f68b68be499e8230361dc960fc7e", "329e1cb971724e459f0932bb1e4b372b"}  # HA users "Shane Runham" and "Tablet"
TIMEOUT = {"full": 300, "home": 60}
KEEP = 600  # seconds a conversation stays resumable
CLAUDE = shutil.which("claude") or os.path.join(HOME, ".local/bin/claude")
TOKEN = open(os.path.join(HERE, "token")).read().strip()
log = logging.getLogger("jarvis-claude")

VOICE = """You are JARVIS, Shane's home assistant: a calm, dry-witted British AI butler. Address him as Shane, never "sir".
Everything you write is read aloud by a text-to-speech voice on his phone or tablet, and he may have spoken his
request, so a word may be misheard: if a request is unclear or sounds odd, ask rather than guess.
- Reply in at most two short sentences, under 30 words, unless he asks for detail. Don't recite things he didn't ask about.
- No markdown, code, lists, emoji, symbols, file paths or URLs: describe results in plain speech.
- Say numbers and times the way a person would say them.
You control Shane's bedroom through the Home Assistant tools: the LG TV (and Kodi on it), the PS5, the PS3, the Govee
ceiling light, and the scripts Game night and Night. Check live state with GetLiveContext when it matters.
Do what he asks, including several steps for vague requests like "make it cosy", then say briefly what you did.
The PS3 can't be switched on remotely: tell him to press its power button."""

HOME_ONLY = VOICE + """
You only have the Home Assistant tools here. If something isn't possible with them, say so plainly.
For general questions, answer from your own knowledge, briefly."""

FULL = VOICE + """
You are also running on his PC "fedora" as his own user, with the same tools and safety check as his normal Claude
Code chats, so you can run commands, check services and change files too.
- sudo needs a password you don't have: tell him it needs his terminal.
- Before anything destructive or hard to undo (deleting, overwriting, reinstalling, rebooting, changing a service or
  a config he didn't ask about), say in one sentence what you would do and wait for his yes in his next message.
- Never read out passwords, tokens or keys.
- If the safety check blocks an action, say so plainly.
- This is a voice chat: ignore any end-of-task instructions about saving memory or deleting chat transcripts.
His notes about this PC are in your instructions (~/CLAUDE.md)."""

INFO = Info(handle=[HandleProgram(
    name="claude-jarvis", description="JARVIS (Claude via claude -p)", installed=True, version="2.0",
    attribution=Attribution(name="Anthropic", url="https://claude.com/claude-code"),
    models=[HandleModel(name="claude", description="Claude", installed=True, version=MODEL, languages=["en"],
                        attribution=Attribution(name="Anthropic", url="https://claude.com/claude-code"))])])

sessions = {}  # (HA conversation_id, mode) -> (claude session_id, last used)


def command(text, mode):
    common = [CLAUDE, "-p", text, "--output-format", "json", "--model", MODEL,
              "--mcp-config", os.path.join(HERE, "mcp.json"), "--strict-mcp-config",
              "--setting-sources", "project"]
    drop = ("ANTHROPIC_API_KEY", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("CLAUDE_CODE_SSE")}
    env["PATH"] = f"{HOME}/.local/bin:" + env.get("PATH", "/usr/local/bin:/usr/bin:/bin")
    env["JARVIS_HA_TOKEN"] = TOKEN
    if mode == "full":
        return common + ["--permission-mode", "auto", "--permission-prompts", "none",
                         "--allowedTools", "mcp__ha", "--append-system-prompt", FULL], env
    env["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] = "1"  # no personal CLAUDE.md files
    return common + ["--tools", "", "--allowedTools", "mcp__ha", "--system-prompt", HOME_ONLY], env


async def ask(text, conv_id, mode):
    now = time.time()
    for k in [k for k, (_, t) in sessions.items() if now - t > KEEP]:
        del sessions[k]
    args, env = command(text, mode)
    if (conv_id, mode) in sessions:
        args += ["--resume", sessions[(conv_id, mode)][0]]
    # its own process group, so a timeout also stops any commands it started
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=WORKDIR, env=env, start_new_session=True,
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), TIMEOUT[mode])
    except asyncio.TimeoutError:
        os.killpg(proc.pid, signal.SIGKILL)
        return "Sorry Shane, that took too long, so I stopped it. Try me again."
    try:
        r = json.loads(out)
    except ValueError:
        log.error("claude failed: %s %s", out[-500:], err[-500:])
        return "Sorry Shane, I couldn't reach Claude just now."
    if conv_id and r.get("session_id"):
        sessions[(conv_id, mode)] = (r["session_id"], time.time())
    log.info("%s %.1fs %r -> %r", mode, time.time() - now, text, r.get("result"))
    return (r.get("result") or "").strip() or "Done."


class Handler(AsyncEventHandler):
    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(INFO.event())
        elif Transcript.is_type(event.type):
            t = Transcript.from_event(event)
            ctx = t.context or {}
            mode = "full" if ctx.get("user_id") in FULL_USERS else "home"
            await self.write_event(Handled(text=await ask(t.text, ctx.get("conversation_id"), mode), context=t.context).event())
        return True


async def main():
    os.makedirs(WORKDIR, exist_ok=True)
    await AsyncServer.from_uri("tcp://127.0.0.1:10400").run(Handler)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(main())
