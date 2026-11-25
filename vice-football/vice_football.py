#!/usr/bin/env python3
"""Vice Football (2026-11-17, ~/homelab/vice-football-plan.md): London AFC and England men, live.

Follows both teams on ESPN's public site API (no key), serves a summary for the Vice panel and fires HA event
`vice_football` for each match moment (an HA automation turns those into Vice OSD cards and phone notifications).

  vice_football.py serve                       the user service (127.0.0.1:5405)
  vice_football.py replay <league> <event_id>  replay a finished match through the event engine, print the cards
                       [--var] [--emit]         --var: add a goal that VAR rules out; --emit: also fire them at HA

HTTP: GET /api/football (teams: next, last, live), GET /crest/<id>.png (cached crests, for the TV's cards).
Standard library only.
"""
import json, os, sys, threading, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
CREST = "https://a.espncdn.com/i/teamlogos/soccer/500/{}.png"
HA = "http://127.0.0.1:8123"
HA_TOKEN = os.path.expanduser("~/homelab/home-assistant/token")
STATE = os.path.expanduser("~/.local/state/vice-football/state.json")
CRESTS = os.path.expanduser("~/homelab/home-assistant/config/www/vice-panel/football")  # gitignored
PORT = 5405
UK = ZoneInfo("Europe/London")

# ESPN's cross-competition team schedule (`all/`) returned last season for England (checked 2026-11-17),
# so each competition is asked separately. Add a code here when a new tournament or qualifying round starts.
TEAMS = {
    "london": {"id": "366", "name": "London", "short": "SUN",
                   "leagues": ["eng.1", "eng.fa", "eng.league_cup", "uefa.europa"]},
    "england": {"id": "448", "name": "England", "short": "ENG",
                "leagues": ["uefa.nations", "fifa.friendly", "fifa.worldq.uefa", "uefa.euroq", "uefa.euro", "fifa.world"]},
}
OURS = {t["id"]: key for key, t in TEAMS.items()}
FIXTURES_EVERY = 3 * 3600
LIVE_EVERY = 30
WINDOW_BEFORE = timedelta(minutes=35)   # start polling (the 30-minute card comes from the fixture list)
WINDOW_AFTER = timedelta(hours=3, minutes=30)  # extra time, delays; polling stops earlier once ESPN says full time


def get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "vice-football"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def when(iso):
    return datetime.strptime(iso.replace("Z", "+0000"), "%Y-%m-%dT%H:%M%z") if len(iso) <= 18 else \
        datetime.fromisoformat(iso.replace("Z", "+00:00"))


def surname(name):
    return name.split()[-1] if name else ""


# ---------------------------------------------------------------- fixtures (next / last per team)

def parse_event(e, league):
    c = e["competitions"][0]
    sides = {}
    for x in c["competitors"]:
        s = x.get("score")
        s = s.get("displayValue") if isinstance(s, dict) else s
        sides[x["homeAway"]] = {"id": x["team"]["id"], "name": x["team"].get("shortDisplayName") or x["team"]["displayName"],
                                "short": x["team"].get("abbreviation", ""), "score": s}
    st = c["status"]["type"]
    return {"id": e["id"], "league": league, "comp": e.get("league", {}).get("name") or c.get("type", {}).get("text") or "",
            "date": e["date"], "home": sides.get("home"), "away": sides.get("away"),
            "state": st.get("state"), "completed": bool(st.get("completed")),
            "venue": (c.get("venue") or {}).get("fullName", "")}


def load_fixtures():
    out = {}
    for key, t in TEAMS.items():
        games, leagues = {}, list(t["leagues"])
        # Upcoming games in every competition (found London's Europa League games this way); `all/` is only
        # wrong for past results, so results still come per competition, including any new one seen here.
        try:
            for e in get(f"{ESPN}/all/teams/{t['id']}/schedule?fixture=true").get("events", []):
                lg = (e.get("league") or {}).get("slug") or (e.get("league") or {}).get("midsizeName", "").lower()
                if lg:
                    games[e["id"]] = parse_event(e, lg)
                    if lg not in leagues:
                        leagues.append(lg)
        except Exception as e:
            log("fixtures", key, "all failed:", e)
        for lg in leagues:
            for q in ("",):
                try:
                    d = get(f"{ESPN}/{lg}/teams/{t['id']}/schedule{q}")
                except Exception as e:  # one competition failing (none this season) mustn't hide the others
                    log("fixtures", key, lg, q, "failed:", e)
                    continue
                comp = (d.get("season") or {}).get("displayName", "")
                for e in d.get("events", []):
                    g = parse_event(e, lg)
                    g["comp"] = g["comp"] or comp
                    games[g["id"]] = g
        out[key] = sorted(games.values(), key=lambda g: g["date"])
    return out


def summary_for(key, games, now):
    done = [g for g in games if g["completed"]]
    ahead = [g for g in games if not g["completed"] and when(g["date"]) > now - WINDOW_AFTER]
    return {"name": TEAMS[key]["name"], "id": TEAMS[key]["id"], "short": TEAMS[key]["short"],
            "last": done[-1] if done else None, "next": ahead[0] if ahead else None,
            "coming": ahead[:5]}  # the panel's tap sheet


# ---------------------------------------------------------------- the event engine (one match)

class Match:
    """Turns successive ESPN `summary` snapshots of one match into card events. Pure: no network."""

    def __init__(self, mid, league, saved=None):
        s = saved or {}
        self.id, self.league = mid, league
        self.seen = set(s.get("seen", []))
        self.score = s.get("score")          # [home, away] as last seen
        self.done = set(s.get("done", []))   # one-off moments already sent: kickoff, ft
        self.seeded = s.get("seeded", False)

    def save(self):
        return {"league": self.league, "seen": sorted(self.seen), "score": self.score, "done": sorted(self.done), "seeded": self.seeded}

    def update(self, d, silent=False):
        """Returns a list of events for what's new in snapshot `d`. silent=True only records (service restarted mid-match)."""
        comp = d["header"]["competitions"][0]
        side = {c["homeAway"]: c for c in comp["competitors"]}
        home, away = side["home"], side["away"]
        tid = {"home": home["team"]["id"], "away": away["team"]["id"]}
        ours_side = "home" if tid["home"] in OURS else "away"
        ours_id = tid[ours_side]
        names = {s: side[s]["team"].get("shortDisplayName") or side[s]["team"]["displayName"] for s in side}
        short = {s: side[s]["team"].get("abbreviation", "") for s in side}
        score = [int(home.get("score") or 0), int(away.get("score") or 0)]
        status = comp["status"]["type"]
        league_name = d["header"].get("league", {}).get("name", "")
        base = {"match": self.id, "team": OURS[ours_id], "home": names["home"], "away": names["away"],
                "home_id": tid["home"], "away_id": tid["away"], "comp": league_name, "tag": f"football_{self.id}"}

        def scoreline(h, a):
            return f"{names['home']} {h}–{a} {names['away']}"

        out = []

        def emit(kind, title, line="", em="", sub="", crests=None, ours=False, minute=""):
            out.append(dict(base, kind=kind, title=title, line=line, em=em, sub=sub, minute=minute, ours=ours,
                            crests=crests or [tid["home"], tid["away"]], score=f"{run[0]}–{run[1]}"))

        run = [0, 0]  # score as it stood at each key event, counted from the goals in order
        for k in d.get("keyEvents", []):
            kt = (k.get("type") or {}).get("type", "")
            team = (k.get("team") or {}).get("id")
            who = [(p.get("athlete") or {}).get("displayName", "") for p in k.get("participants", [])]
            minute = (k.get("clock") or {}).get("displayValue", "")
            if k.get("scoringPlay"):
                run[0 if team == tid["home"] else 1] += 1
            if k["id"] in self.seen:
                continue
            self.seen.add(k["id"])
            if silent:
                continue
            tside = "home" if team == tid["home"] else "away"
            if kt == "kickoff" and "kickoff" not in self.done:
                self.done.add("kickoff")
                emit("kickoff", "Kicked off", f"{names['home']} v {names['away']}", "0–0")
            elif k.get("scoringPlay"):
                us = team == ours_id
                scorer = surname(who[0]) if who else ""
                if kt == "own-goal":
                    scorer += " (og)"
                title = f"GOAL! {names[tside]}" if us else f"{names[tside]} score"
                emit("goal", title, scorer, scoreline(*run), crests=[team], ours=us, minute=minute)
            elif kt == "red-card":
                emit("red", "Red card", f"{surname(who[0]) if who else ''} ({names[tside]})", f"{run[0]}–{run[1]}",
                     crests=[team], minute=minute)
            elif kt in ("penalty---missed", "penalty---saved"):
                emit("penalty", "Penalty missed" if kt.endswith("missed") else "Penalty saved",
                     f"{surname(who[0]) if who else ''} ({names[tside]})", scoreline(*run), crests=[team], minute=minute)
            elif kt == "halftime":
                emit("halftime", "Half time", scoreline(*run))

        # VAR: ESPN has no "disallowed" event; the score just goes back down (or a goal event disappears)
        if self.score is not None and sum(score) < sum(self.score) and not silent:
            lost = "home" if score[0] < self.score[0] else "away"
            run = score
            emit("ruled_out", "Goal ruled out", names[lost], f"back to {score[0]}–{score[1]}", crests=[tid[lost]])
        self.score = score

        if status.get("completed") and "ft" not in self.done:
            self.done.add("ft")
            if not silent:
                run = score
                us, them = (score[0], score[1]) if ours_side == "home" else (score[1], score[0])
                res = "Won" if us > them else "Lost" if us < them else "Drew"
                ours_goals = [f"{surname(((k.get('participants') or [{}])[0].get('athlete') or {}).get('displayName', ''))} "
                              f"{(k.get('clock') or {}).get('displayValue', '')}" + (" (og)" if (k.get("type") or {}).get("type") == "own-goal" else "")
                              for k in d.get("keyEvents", []) if k.get("scoringPlay") and (k.get("team") or {}).get("id") == ours_id]
                emit("fulltime", f"Full time · {res}", scoreline(*score), sub=" · ".join(ours_goals) or league_name)
                out[-1]["result"] = res
        self.seeded = True
        return out


# ---------------------------------------------------------------- talking to HA, crests

def fire(ev):
    try:
        token = open(HA_TOKEN).read().strip()
        req = urllib.request.Request(f"{HA}/api/events/vice_football", data=json.dumps(ev).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception as e:
        log("HA event failed:", e)
        return False


def crest(tid):
    os.makedirs(CRESTS, exist_ok=True)
    p = os.path.join(CRESTS, f"{tid}.png")
    if not os.path.exists(p) or time.time() - os.path.getmtime(p) > 30 * 86400:
        try:
            req = urllib.request.Request(CREST.format(tid), headers={"User-Agent": "vice-football"})
            data = urllib.request.urlopen(req, timeout=15).read()
            with open(p + ".tmp", "wb") as f:
                f.write(data)
            os.replace(p + ".tmp", p)
        except Exception as e:
            log("crest", tid, "failed:", e)
    return p if os.path.exists(p) else None


# ---------------------------------------------------------------- the service

class Service:
    def __init__(self):
        self.lock = threading.Lock()
        self.fixtures, self.fixtures_at, self.live = {}, 0, {}
        self.matches, self.sent_pre = {}, set()
        self.details = {}  # last game id -> live_view() of it: the timeline in the panel's tap sheet
        self.last_ok = None
        try:
            s = json.load(open(STATE))
            self.matches = {m: Match(m, v["league"], v) for m, v in s.get("matches", {}).items()}
            self.sent_pre = set(s.get("pre", []))
        except (OSError, ValueError):
            pass

    def save(self):
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        keep = sorted(self.matches)[-20:]  # ESPN ids grow; old matches drop off
        data = {"matches": {m: self.matches[m].save() for m in keep}, "pre": sorted(self.sent_pre)[-20:]}
        with open(STATE + ".tmp", "w") as f:
            json.dump(data, f)
        os.replace(STATE + ".tmp", STATE)

    def games(self):
        return [g for gs in self.fixtures.values() for g in gs]

    def tick(self):
        now = datetime.now(timezone.utc)
        if time.time() - self.fixtures_at > FIXTURES_EVERY:
            f = load_fixtures()
            if any(f.values()):
                with self.lock:
                    self.fixtures, self.fixtures_at = f, time.time()
                self.last_ok = time.time()
                for t in self.view()["teams"].values():  # only the crests the panel shows: next, last, coming
                    l = t["last"]
                    if l and l["id"] not in self.details:
                        try:
                            self.details[l["id"]] = live_view(get(f"{ESPN}/{l['league']}/summary?event={l['id']}"))
                        except Exception as e:
                            log("last match", l["id"], "failed:", e)
                    for g in [t["next"], l] + t["coming"]:
                        for s in ("home", "away"):
                            if g and g[s]:
                                crest(g[s]["id"])
        busy = False
        for g in self.games():
            ko = when(g["date"])
            if g["id"] not in self.sent_pre and timedelta(0) < ko - now <= timedelta(minutes=30) and not g["completed"]:
                self.sent_pre.add(g["id"])
                ours = g["home"] if g["home"]["id"] in OURS else g["away"]
                fire({"kind": "pre", "match": g["id"], "team": OURS[ours["id"]], "tag": f"football_{g['id']}",
                      "title": f"{g['home']['name']} v {g['away']['name']}", "line": g["comp"],
                      "em": f"{ko.astimezone(UK):%H:%M} kickoff", "sub": g["venue"], "minute": "", "ours": False,
                      "crests": [g["home"]["id"], g["away"]["id"]], "home_id": g["home"]["id"], "away_id": g["away"]["id"],
                      "comp": g["comp"], "score": ""})
                self.save()
            m = self.matches.get(g["id"])
            if ko - WINDOW_BEFORE <= now <= ko + WINDOW_AFTER and not (m and "ft" in m.done):
                busy = True
                self.poll(g)
        if not busy:
            with self.lock:
                self.live = {}
        return busy

    def poll(self, g):
        try:
            d = get(f"{ESPN}/{g['league']}/summary?event={g['id']}")
        except Exception as e:
            log("live", g["id"], "failed:", e)
            return
        self.last_ok = time.time()
        m = self.matches.get(g["id"])
        state = d["header"]["competitions"][0]["status"]["type"].get("state")
        fresh = m is None
        if fresh:
            m = self.matches[g["id"]] = Match(g["id"], g["league"])
        # first sight of a match already under way or over (service restarted): record it, don't replay old goals
        evs = m.update(d, silent=fresh and state != "pre")
        for ev in evs:
            log("event", ev["kind"], ev["title"], ev["line"], ev["em"])
            fire(ev)
        if evs or fresh:
            self.save()
        with self.lock:
            self.live[g["id"]] = live_view(d)
        if state == "post":
            self.fixtures_at = 0  # refresh next/last now

    def view(self):
        now = datetime.now(timezone.utc)
        with self.lock:
            teams = {k: summary_for(k, gs, now) for k, gs in self.fixtures.items()}
            for k, t in teams.items():
                n = t["next"]
                t["live"] = self.live.get(n["id"]) if n else None
                t["last_detail"] = self.details.get(t["last"]["id"]) if t["last"] else None
            return {"updated": self.last_ok, "teams": teams}

    def run(self):
        while True:
            try:
                busy = self.tick()
            except Exception as e:
                log("tick failed:", repr(e))
                busy = False
            time.sleep(LIVE_EVERY if busy else 60)


def live_view(d):
    comp = d["header"]["competitions"][0]
    st = comp["status"]
    side = {c["homeAway"]: c for c in comp["competitors"]}
    goals = [{"team": (k.get("team") or {}).get("id"), "minute": (k.get("clock") or {}).get("displayValue", ""),
              "who": surname(((k.get("participants") or [{}])[0].get("athlete") or {}).get("displayName", "")),
              "og": (k.get("type") or {}).get("type") == "own-goal"}
             for k in d.get("keyEvents", []) if k.get("scoringPlay")]
    kinds = {"red-card": "red", "own-goal": "og", "penalty---scored": "pen", "penalty---missed": "pen_missed",
             "penalty---saved": "pen_saved"}
    timeline = [{"kind": "goal" if k.get("scoringPlay") and kinds.get(k["type"].get("type")) not in ("og", "pen")
                 else kinds.get((k.get("type") or {}).get("type"), "goal"),
                 "team": (k.get("team") or {}).get("id"), "minute": (k.get("clock") or {}).get("displayValue", ""),
                 "who": ((k.get("participants") or [{}])[0].get("athlete") or {}).get("displayName", "")}
                for k in d.get("keyEvents", [])
                if k.get("scoringPlay") or (k.get("type") or {}).get("type") in kinds]
    return {"timeline": timeline, "state": st["type"].get("state"), "detail": st["type"].get("shortDetail", ""),
            "clock": st.get("displayClock", ""), "score": [side["home"].get("score"), side["away"].get("score")],
            "goals": goals,
            "reds": [{"team": (k.get("team") or {}).get("id"), "minute": (k.get("clock") or {}).get("displayValue", "")}
                     for k in d.get("keyEvents", []) if (k.get("type") or {}).get("type") == "red-card"]}


def serve():
    svc = Service()
    threading.Thread(target=svc.run, daemon=True).start()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/api/football"):
                body, ctype = json.dumps(svc.view()).encode(), "application/json"
            elif self.path.startswith("/crest/") and self.path.endswith(".png"):
                tid = self.path[7:-4]
                p = crest(tid) if tid.isdigit() else None
                if not p:
                    self.send_error(404)
                    return
                body, ctype = open(p, "rb").read(), "image/png"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "max-age=86400" if ctype == "image/png" else "no-store")
            self.end_headers()
            self.wfile.write(body)

    log(f"vice-football on 127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


# ---------------------------------------------------------------- replay (testing)

def replay(league, eid, var=False, emit=False):
    """Feeds a finished match to the engine one key event at a time, as if it were live."""
    full = get(f"{ESPN}/{league}/summary?event={eid}")
    keys = full.get("keyEvents", [])
    comp = full["header"]["competitions"][0]
    side = {c["homeAway"]: c for c in comp["competitors"]}
    if not (side["home"]["team"]["id"] in OURS or side["away"]["team"]["id"] in OURS):
        sys.exit("neither team is London or England")
    m = Match(eid, league)
    out = []

    def snap(n, done=False, extra=None):
        d = json.loads(json.dumps(full))
        ks = keys[:n] + (extra or [])
        d["keyEvents"] = ks
        c = d["header"]["competitions"][0]
        h_id = side["home"]["team"]["id"]
        hs = sum(1 for k in ks if k.get("scoringPlay") and (k.get("team") or {}).get("id") == h_id)
        a_s = sum(1 for k in ks if k.get("scoringPlay")) - hs
        for x in c["competitors"]:
            x["score"] = str(hs if x["homeAway"] == "home" else a_s)
        c["status"]["type"].update({"completed": done, "state": "post" if done else "in"})
        return d

    for i in range(1, len(keys) + 1):
        out += m.update(snap(i))
        if var and i == len(keys) // 2:  # a goal for the home side that VAR then takes away
            fake = {"id": "var-test", "type": {"type": "goal", "text": "Goal"}, "scoringPlay": True,
                    "clock": {"displayValue": "VAR'"}, "team": {"id": side["home"]["team"]["id"]},
                    "participants": [{"athlete": {"displayName": "Test Player"}}]}
            out += m.update(snap(i, extra=[fake]))
            out += m.update(snap(i))
    out += m.update(snap(len(keys), done=True))
    for ev in out:
        print(f"{ev['kind']:10} {ev['minute']:>7}  {ev['title']}  |  {ev['line']}  ·  {ev['em']}"
              + (f"  |  {ev['sub']}" if ev['sub'] else "") + ("  [pink]" if ev["ours"] else ""))
        if emit:
            fire(dict(ev, tag="football_replay"))
            time.sleep(10)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["serve"]:
        serve()
    elif a[:1] == ["replay"] and len(a) >= 3:
        replay(a[1], a[2], var="--var" in a, emit="--emit" in a)
    else:
        sys.exit(__doc__)
