# 🏠 Homelab

<img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/panel-tablet.jpg" alt="The Home Assistant panel on a tablet" width="72%"> <img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/panel-phone.jpg" alt="The Home Assistant panel on a phone" width="25%">

My home server: one Fedora PC running everything through Docker Compose and a handful of systemd services.
It watches itself, backs itself up every night and tells me on my phone, TV or Discord when something's wrong.

### What runs on it

| | |
|---|---|
| **Home Assistant** | The hub: TV, PS5, light, alerts and scenes, with my own dashboard panel (`home-assistant/config/www/vice-panel`) |
| **JARVIS voice** | Offline speech-to-text (Whisper) and voice (Kokoro), with Claude answering what Home Assistant can't (`jarvis-assist`) |
| **Jellyfin** | Films and TV, hardware transcoding on the GPU |
| **Forgejo + runner** | My own Git server; every push runs the checks in `.forgejo/workflows` |
| **Uptime Kuma, Dozzle, Speedtest Tracker** | Uptime, container logs and internet speed |
| **Vice Radio** | A 24/7 music station, in its own repo: [VICE-Radio](https://github.com/ShaneRunham/VICE-Radio) |
| **VICE Bot** | The Discord bot that reports on all of this: [VICE-Bot](https://github.com/ShaneRunham/VICE-Bot) |

Everything binds to `127.0.0.1` and is reached over Tailscale; only what the TV and consoles need is open on the LAN.

### Looking after itself

- **Backups:** nightly btrfs snapshots to a mirrored pair of drives (`backup`), monthly scrubs (`scrub`), SMART checks (`hardening`)
- **Updates:** images daily, OS updates offline at the next reboot with a snapshot to boot back into (`update`, `update-snapshot`)
- **Health:** `doctor` checks everything in one go; `blackbox` records the last seconds before a freeze; `heartbeat` pings a dead-man's switch
- **Git:** every change is committed automatically, scanned for secrets first (`git-autocommit`)

### Also here

`govee-bridge` (a Bluetooth bulb for Home Assistant), `pc-actions` (PC buttons on the dashboard), `ps3-backup`,
`streaming` (Sunshine for Moonlight), `jellyfin` (custom theme), `kernel` (keeps a known-good kernel as default).

> A cleaned copy of my private repo, updated automatically: personal details are swapped for placeholders and
> third-party artwork, fonts and videos are left out. It's built for my PC, so expect to adapt paths and names.
