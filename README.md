# 🏠 Homelab

<img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/panel-tablet.jpg" alt="The Hideout panel in Home Assistant on a tablet" width="100%">

My home server: one Fedora PC under the TV running everything through Docker Compose and a set of small systemd
services. It runs the smart home, a media server, a radio station, my own Git server and an offline voice assistant,
watches itself, backs itself up every night and tells me on my phone, TV or Discord when something's wrong.

**Contents:** [What runs on it](#what-runs-on-it) · [The Hideout panel](#the-hideout-panel) · [Hideout Map](#hideout-map) ·
[Wanted Level](#wanted-level) · [JARVIS voice](#jarvis-voice) · [Looking after itself](#looking-after-itself) ·
[Alerts](#alerts) · [Folders](#folders)

## What runs on it

| | |
|---|---|
| **Home Assistant** | The hub: TV, PS5, Switch, the ceiling light, alerts, scenes and my own dashboards (below) |
| **JARVIS voice** | Offline speech-to-text (Whisper) and voice (Kokoro); Claude answers what Home Assistant can't (`jarvis-assist`) |
| **Jellyfin** | Films and TV with hardware transcoding on the GPU, plus tinyMediaManager for tidying new media |
| **Forgejo + runner** | My own Git server; every push runs the checks in `.forgejo/workflows` (tests, compose, shellcheck, HA config) |
| **Uptime Kuma, Dozzle, Speedtest Tracker** | Uptime monitors, container logs, an internet speed test every 6 hours |
| **Mosquitto + ps5-mqtt** | MQTT, and PS5 power and game status over the local network |
| **Hideout Radio** | A 24/7 80s station: [Hideout-Radio](https://github.com/ShaneRunham/Hideout-Radio) |
| **Hideout Bot** | The Discord bot that reports on all of this: [Hideout-Bot](https://github.com/ShaneRunham/Hideout-Bot) |
| **Hideout Home + Hideout Phone** | The TV's home screen and my phone remote: [Hideout-Home](https://github.com/ShaneRunham/Hideout-Home) |
| **Sunshine** | Streams PC games to the TV, tablet and phone with Moonlight (`streaming`) |
| **Small services** | `govee-bridge` (a Bluetooth bulb for Home Assistant), `pc-actions` (lock, VS Code, restart a container from a dashboard button), `syncthing` (PSP saves with the tablet) |

Everything binds to `127.0.0.1` and is reached over Tailscale with HTTPS; only what the TV and consoles need is
open on the LAN.

## The Hideout panel

A custom Home Assistant panel (`home-assistant/config/www/vice-panel/vice-panel.js`) in the same look as the TV's
home screen: graphite, with the same slow fjord video behind it. It's the only dashboard: the tablet opens it when it's plugged in, and it's in the phone app's menu.

<img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/panel-phone.jpg" alt="The Hideout panel on a phone" width="32%"> <img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/panel-phone-2.jpg" alt="Lower down on the phone: football, the light and the PC" width="32%">

- **Top line:** weather (tap for the next hours), match days, and the homelab's health with the Wanted stars
- **Devices:** TV (tap for power, hold to pick an input), PS5 (wake or rest, the game being played), Switch (puts it on the TV), Hideout Radio (play it on the panel, skip)
- **Ceiling light:** on/off, brightness, warm/neutral/cool white and colours
- **PC:** CPU, temperature, memory, free space on the SSD and backup drives; Lock, Open VS Code, Turn off (double tap)
- **Football:** my team and England, last result and next match (tap for the timeline and fixtures), with a Spoilers switch that hides scores everywhere
- **Map** and **JARVIS** buttons in the top bar; on-screen cards from the rest of the system show here as banners

<img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/panel-weather.jpg" alt="The weather card" width="72%">

## Hideout Map

A second panel (`www/vice-panel/vice-map.js`): the homelab drawn as an invented coastal city, made from scratch in
SVG. Each device is a place on it: the PC is Fedora Tower, the TV the Starlight Drive-In, the PS5 the Neon Arcade,
the Switch the Pier Arcade, the radio is Radio Hill, the backups The Vault and the ceiling light the Lighthouse (its
beam sweeps the sea while the light is on).

<img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/map-tablet.jpg" alt="Hideout Map on a tablet" width="100%">

<img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/map-phone.jpg" alt="Hideout Map on a phone" width="32%"> <img src="https://raw.githubusercontent.com/ShaneRunham/ShaneRunham/main/screens/hideout-panel/map-card.jpg" alt="Tapping a place on the phone opens its card" width="32%">

Places that are on glow; tap one for its card with live details and controls. A problem flashes red on the place it
belongs to, and at three stars or more the map gets a red and blue border. Tablet: map and list side by side;
phone: map on top, cards slide up from the bottom.

## Wanted Level

The homelab's health as 0 to 5 stars, shown everywhere: the Hideout panel, Hideout Map, the TV, the phone remote and Discord.

- Each problem the bot finds is worth 1 to 3 stars (disk, SATA link, backup, watchdog or Docker trouble 3; a stopped container or service 2; the rest 1)
- A problem left unfixed gains a star per hour (at most two more), and three problems at once add one
- When everything's fixed the stars flash for about two minutes ("evading"), then it's "Lost them"
- Phone alerts are titled with the stars; TV pop-ups show them; Home Assistant has `sensor.wanted_level`
- Quiet 23:00 to 08:00: only Discord and the sensor

The rules live in the bot ([`wanted.py`](https://github.com/ShaneRunham/Hideout-Bot/blob/main/wanted.py)).

## JARVIS voice

Push-to-talk from the panel's mic button or the Home Assistant app. Whisper turns speech into text, Home Assistant
handles what it knows (lights, TV, PS5), and anything else goes to Claude; Kokoro speaks the answer. All local
except Claude.

## Looking after itself

- **Backups:** nightly btrfs snapshots to a mirrored pair of drives, 14 kept (`backup`); monthly scrubs (`scrub`); SMART checks (`hardening`)
- **Updates:** container images daily; Fedora updates offline at the next reboot, each with a snapshot to boot back into (`update`, `update-snapshot`)
- **Health:** `doctor` checks everything in one go; `blackbox` records the last seconds before a freeze; `heartbeat` pings an outside dead-man's switch every 5 minutes
- **Kernel:** keeps a known-good kernel as the default (`kernel`)
- **Git:** every change is committed automatically and scanned for secrets first (`git-autocommit`); each commit also refreshes these public copies

## Alerts

One detector, one ping. The bot decides what's a problem (containers, services, disks, heat, backups, SATA errors,
logins about to expire, failed CI runs, the watchdog). Home Assistant turns each into a phone notification with a
Restart button where that makes sense, a card on the TV, and the status line on every dashboard. Discord's #alerts
is the quiet log.

## Folders

| | |
|---|---|
| `compose.yaml` | Every container |
| `home-assistant/config` | Automations, scripts, the Hideout panel and Hideout Map (still in `www/vice-panel`: the old name) |
| `jarvis-assist` | The voice assistant (Whisper and Kokoro run beside it in `compose.yaml`) |
| `backup`, `scrub`, `hardening`, `update`, `update-snapshot`, `kernel` | Keeping the PC healthy |
| `doctor`, `blackbox`, `heartbeat` | Health checks |
| `git-autocommit`, `tools` | Automatic commits and the public mirrors |
| `govee-bridge`, `pc-actions`, `streaming`, `ps3-backup`, `jellyfin` | Small services and setups |
| `mosquitto`, `media` | The MQTT broker's config; the firewall rule for Jellyfin on the LAN |
| `.forgejo/workflows` | The checks every push runs on my Git server |

> A cleaned copy of my private repo, updated automatically: personal details are swapped for placeholders and
> third-party artwork, fonts and videos are left out. It's built for my PC, so expect to adapt paths and names.
