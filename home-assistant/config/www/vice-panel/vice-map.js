// Vice Map (2026-11-16): the homelab as an invented Vice-style city. Each device is a place on the map; tap it for its
// controls. Places that are on glow; a Wanted Level problem (~/homelab/discord-bot/wanted.py) flashes red on the place
// it belongs to. A custom panel (panel_custom url_path vice-map) like the Vice panel, same look; the Vice panel's map
// button opens it. The map is drawn here (inline SVG), not taken from any game.

const BASE = "/local/vice-panel/";
const RADIO = `${location.protocol}//${location.hostname}:8447`;  // Vice Radio's now-playing and skip (same as the Vice panel)
const E = {
  tv: "media_player.lg_tv", ps5: "switch.ps5", ps5Media: "media_player.playstation_5", ps5Last: "sensor.ps5_last_game",
  nsw: "binary_sensor.nintendo_switch", nswTime: "sensor.bedroom_sam_s_switch_used_screen_time",
  light: "light.ceiling_light", wanted: "sensor.wanted_level",
  cpu: "sensor.system_monitor_processor_use", temp: "sensor.system_monitor_processor_temperature",
  ram: "sensor.system_monitor_memory_usage", up: "sensor.system_monitor_uptime",
  storeFree: "sensor.system_monitor_disk_free_mnt_storage", storeUse: "sensor.system_monitor_disk_usage_mnt_storage",
  haBackup: "sensor.backup_last_successful_automatic_backup",
};
const INPUTS = [["Home", "Vice Home"], ["PS5", "PS5 Game Console"], ["Switch", "Nintendo Switch"], ["Sky", "Sky Box"]];
const WHITES = [["Warm", 2700], ["Neutral", 4000], ["Cool", 6500]];

const ic = (p) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
const ICON = {
  hq: ic('<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M10 22v-4h4v4M9 6h.01M12 6h.01M15 6h.01M9 10h.01M12 10h.01M15 10h.01M9 14h.01M12 14h.01M15 14h.01"/>'),
  tv: ic('<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M17 2l-5 5-5-5"/>'),
  ps5: ic('<path d="M6 11h4M8 9v4M15 12h.01M18 10h.01"/><path d="M17.3 5H6.7a4 4 0 0 0-4 3.6C2.6 9.4 2 14.5 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.4-1.4A2 2 0 0 1 9.8 16h4.4a2 2 0 0 1 1.4.6L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.5-.6-6.6-.7-7.3A4 4 0 0 0 17.3 5z"/>'),
  nsw: ic('<rect x="3" y="4" width="8" height="16" rx="4"/><rect x="13" y="4" width="8" height="16" rx="4"/><circle cx="7" cy="9" r=".6"/><circle cx="17" cy="15" r=".6"/>'),
  radio: ic('<path d="M4.9 16.1C1 12.2 1 5.8 4.9 1.9M7.8 4.7a6.1 6.1 0 0 0-.8 7.5M16.2 4.8c2 2 2.3 5.1.8 7.5M19.1 1.9a10 10 0 0 1 0 14.1"/><circle cx="12" cy="9" r="2"/><path d="M8 22l4-11 4 11M9.5 18h5"/>'),
  light: ic('<path d="M9 18h6M10 22h4M15 14c.2-1 .7-1.7 1.5-2.5A5 5 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'),
  vault: ic('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0"/>'),
  back: ic('<path d="M15 18l-6-6 6-6"/>'),
};

// The places: id, name, what it is, where (map units, 0-1000 both ways), and which Wanted problems belong there
const PLACES = [
  { id: "hq", name: "Fedora Tower", what: "The PC", x: 352, y: 372 },
  { id: "tv", name: "Starlight Drive-In", what: "LG TV", x: 168, y: 612 },
  { id: "ps5", name: "Neon Arcade", what: "PS5", x: 478, y: 566 },
  { id: "nsw", name: "Pier Arcade", what: "Nintendo Switch", x: 896, y: 604 },
  { id: "radio", name: "Radio Hill", what: "Vice Radio", x: 196, y: 178 },
  { id: "light", name: "Lighthouse", what: "Ceiling light", x: 716, y: 902 },
  { id: "vault", name: "The Vault", what: "Backups", x: 404, y: 846 },
];
function placeOf(key) {
  if (key === "tv_ssh") return "tv";
  if (key === "radio" || key === "container:radio") return "radio";
  if (key === "backup" || key === "disk:/mnt/storage" || key === "update_snapshot") return "vault";
  if (key === "psn") return "ps5";
  return "hq";
}

// ---------- the map: an invented coastal city (mainland, a bay with islets, a barrier island with its beach, ocean) ----------
const MAINLAND = "M0 0H602C588 92 612 152 592 232C577 302 603 362 588 432C572 522 612 592 592 672C577 742 542 802 562 872C577 932 542 972 522 1000H0Z";
const ISLAND = "M690 38C722 28 746 62 752 122L766 402C776 522 792 642 782 762C774 862 746 932 706 962C690 968 682 950 688 930C705 860 712 780 708 680C702 560 690 440 688 320C686 200 676 80 690 38Z";
// city blocks: a few lit buildings in the street grid (the same every time: a fixed pseudo-random sequence)
const BLOCKS = (() => {
  let seed = 7, out = "";
  const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;
  for (let y = 4; y < 1000; y += 34) for (let x = 4; x < 1000; x += 34) {
    const r = rnd();
    if (r < .45) continue;
    out += `<rect x="${x + 3}" y="${y + 3}" width="${20 + Math.round(rnd() * 6)}" height="${20 + Math.round(rnd() * 6)}" rx="2" fill="rgba(255,255,255,${(.03 + rnd() * .07).toFixed(3)})"/>`;
  }
  return out;
})();
const MAP_SVG = `
<svg class="map" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs>
    <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse"><path d="M34 0H0V34" fill="none" stroke="rgba(255,255,255,.055)" stroke-width="1.2"/></pattern>
    <radialGradient id="sea" cx="85%" cy="40%" r="85%"><stop offset="0" stop-color="#173a6b"/><stop offset=".55" stop-color="#11284f"/><stop offset="1" stop-color="#0b1733"/></radialGradient>
    <clipPath id="land"><path d="${MAINLAND}"/><path d="${ISLAND}"/></clipPath>
  </defs>
  <rect width="1000" height="1000" fill="url(#sea)"/>
  <g class="waves" stroke="rgba(255,255,255,.05)" stroke-width="1.5" fill="none">
    <path d="M820 140q20-8 40 0t40 0"/><path d="M860 300q20-8 40 0t40 0"/><path d="M830 460q20-8 40 0t40 0"/>
    <path d="M870 760q20-8 40 0t40 0"/><path d="M810 900q20-8 40 0t40 0"/><path d="M620 140q14-6 28 0"/><path d="M630 700q14-6 28 0"/>
  </g>
  <g fill="none" stroke="rgba(110,200,255,.16)" stroke-width="26" stroke-linejoin="round"><path d="${MAINLAND}"/><path d="${ISLAND}"/></g>
  <path d="${MAINLAND}" fill="#2a2140"/>
  <path d="${ISLAND}" fill="#2a2140"/>
  <g fill="none" stroke="rgba(255,255,255,.22)" stroke-width="2"><path d="${MAINLAND}"/><path d="${ISLAND}"/></g>
  <g clip-path="url(#land)">${BLOCKS}</g>
  <path d="M752 122L766 402C776 522 792 642 782 762C774 862 746 932 706 962" fill="none" stroke="rgba(255,196,150,.22)" stroke-width="12"/>
  <rect width="1000" height="1000" fill="url(#grid)" clip-path="url(#land)"/>
  <g fill="rgba(126,226,168,.09)" clip-path="url(#land)">
    <rect x="112" y="104" width="170" height="146" rx="40"/><rect x="92" y="544" width="160" height="118" rx="18"/>
    <rect x="424" y="640" width="108" height="86" rx="14"/><rect x="704" y="190" width="40" height="110" rx="14"/>
    <circle cx="300" cy="900" r="46"/>
  </g>
  <g fill="#2a2140" stroke="rgba(255,255,255,.22)" stroke-width="2"><ellipse cx="640" cy="330" rx="16" ry="30"/>
  <ellipse cx="636" cy="610" rx="22" ry="13"/><ellipse cx="646" cy="822" rx="13" ry="22"/></g>
  <g stroke="rgba(255,255,255,.16)" stroke-width="5" fill="none" stroke-linecap="round">
    <path d="M0 232H700M0 522H700M0 800H712M182 0V1000M404 0V872M0 940L240 700" clip-path="url(#land)"/>
    <path d="M588 232H702M596 522H700M556 800H712" stroke="rgba(255,255,255,.3)" stroke-width="7"/>
    <path d="M720 60C734 300 744 560 748 760C750 860 730 920 700 950" clip-path="url(#land)"/>
  </g>
  <g stroke="rgba(255,255,255,.11)" stroke-width="3" fill="none"><path d="M780 604H900"/><rect x="888" y="590" width="26" height="28" rx="3" fill="rgba(255,255,255,.08)"/></g>
  <g class="lbl" fill="rgba(255,255,255,.34)" font-size="17" letter-spacing="5" font-weight="600">
    <text x="236" y="84">NORTH SHORE</text><text x="40" y="496">DOWNTOWN</text><text x="40" y="742">LITTLE PALMS</text>
    <text x="250" y="972">HARBOR</text><text x="548" y="470" fill="rgba(255,255,255,.22)" transform="rotate(-90 548 470)">THE BAY</text>
    <text x="732" y="560" transform="rotate(-86 732 560)">VICE BEACH</text><text x="842" y="380" fill="rgba(255,255,255,.18)" letter-spacing="10">OCEAN</text>
  </g>
</svg>`;

const CSS = `
:host{display:block;position:relative;height:100%;min-height:100vh;overflow:hidden;background:#0d0a14;color:#fff;
  font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased;-webkit-tap-highlight-color:transparent;user-select:none}
*{box-sizing:border-box;margin:0;padding:0}
svg{display:block}
.wrap{position:relative;height:100%;overflow-y:auto;padding:32px 48px 32px;display:flex;flex-direction:column;gap:22px}
.top{display:flex;align-items:center;gap:14px}
.round{width:42px;height:42px;border-radius:21px;background:rgba(38,38,44,.6);display:grid;place-items:center;cursor:pointer;flex:none}
.round svg{width:22px;height:22px}
.title small{display:block;font-size:12px;letter-spacing:3px;opacity:.55;font-weight:500;text-transform:uppercase}
.title b{font-size:26px;font-weight:600;letter-spacing:-.3px}
.chip{margin-left:auto;display:flex;align-items:center;gap:10px;font-size:15px;color:rgba(255,255,255,.8);background:rgba(38,38,44,.6);padding:10px 16px;border-radius:22px;white-space:nowrap}
.chip .stars{display:flex;gap:2px}
.stars i{display:block;width:17px;height:17px}
.stars svg{width:17px;height:17px;fill:rgba(0,0,0,.25);stroke:rgba(255,255,255,.55);stroke-width:1.5}
.stars i.on svg{fill:#fff;stroke:#fff}
.stars.evading i.on svg{animation:evade .8s steps(1) infinite}
@keyframes evade{50%{fill:rgba(0,0,0,.25);stroke:rgba(255,255,255,.55)}}
.dot{width:8px;height:8px;border-radius:4px;background:#7ee2a8;box-shadow:0 0 0 3px rgba(126,226,168,.18);flex:none}
.dot.bad{background:#ff8a7a;box-shadow:0 0 0 3px rgba(255,138,122,.2)}
.dot.off{background:#9a96a3;box-shadow:none}
.body{display:flex;gap:28px;align-items:flex-start}
/* explicit size: HA's panel host has no fixed height for a percentage to work from (2026-11-16, map was 0 px) */
.mapbox{position:relative;flex:none;width:min(calc(100vh - 150px),58vw);aspect-ratio:1;border-radius:18px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.4)}
.mapbox .map{position:absolute;inset:0;width:100%;height:100%}
.mapbox.hot{animation:siren 2.4s ease-in-out infinite}
@keyframes siren{0%,100%{box-shadow:0 12px 40px rgba(0,0,0,.4),inset 0 0 0 2px rgba(255,90,90,.0)}25%{box-shadow:0 12px 40px rgba(0,0,0,.4),0 0 0 3px rgba(255,90,90,.55)}75%{box-shadow:0 12px 40px rgba(0,0,0,.4),0 0 0 3px rgba(90,140,255,.55)}}
.blip{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;cursor:pointer;z-index:1}
.blip .b{position:relative;width:46px;height:46px;border-radius:23px;display:grid;place-items:center;background:rgba(30,28,36,.94);
  box-shadow:0 0 0 2px rgba(255,255,255,.28),0 6px 16px rgba(0,0,0,.45);color:rgba(255,255,255,.55);transition:.2s}
.blip .b svg{width:22px;height:22px}
.blip.on .b{color:#fff;box-shadow:0 0 0 2px #fff,0 0 22px rgba(255,255,255,.35),0 6px 16px rgba(0,0,0,.45)}
.blip.bad .b::after{content:"";position:absolute;inset:-8px;border-radius:50%;border:2px solid #ff6b6b;animation:ping 1.4s ease-out infinite}
.blip.bad .b{box-shadow:0 0 0 2px #ff8a7a,0 6px 16px rgba(0,0,0,.45);color:#fff}
@keyframes ping{0%{transform:scale(.85);opacity:1}100%{transform:scale(1.5);opacity:0}}
.blip.sel .b{background:#f2f2f2;color:#141414;box-shadow:0 0 0 3px #fff,0 6px 16px rgba(0,0,0,.45)}
.blip .n{margin-top:7px;font-size:14px;font-weight:500;white-space:nowrap;text-shadow:0 1px 3px rgba(0,0,0,.8),0 0 12px rgba(0,0,0,.6)}
.blip .s{font-size:12px;opacity:.65;white-space:nowrap;max-width:170px;overflow:hidden;text-overflow:ellipsis;text-shadow:0 1px 3px rgba(0,0,0,.8)}
.side{flex:1;min-width:0;display:flex;flex-direction:column;gap:10px}
.label{font-size:17px;font-weight:500;opacity:.92;margin:2px 0 4px}
.place{display:flex;align-items:center;gap:14px;padding:12px 16px;border-radius:14px;background:rgba(32,32,38,.82);cursor:pointer}
.place .i{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:rgba(255,255,255,.08);color:rgba(255,255,255,.6);flex:none}
.place .i svg{width:20px;height:20px}
.place.on .i{color:#fff;background:rgba(255,255,255,.16)}
.place h4{font-size:16px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.place p{font-size:13.5px;color:rgba(255,255,255,.62);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
.place p em{font-style:normal;color:#fff}
.place .t{min-width:0;flex:1}
.place.sel{box-shadow:0 0 0 2px #fff}
.place.bad p{color:#ffb2a8}
.sheet{position:fixed;inset:0;z-index:5;background:rgba(8,5,14,.55);display:none;align-items:center;justify-content:center}
.sheet.show{display:flex}
.pick{width:min(520px,92%);max-height:90%;overflow-y:auto;background:rgba(30,28,36,.97);border-radius:18px;padding:22px 24px 24px;box-shadow:0 24px 60px rgba(0,0,0,.5)}
.ph{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.ph .i{width:48px;height:48px;border-radius:14px;display:grid;place-items:center;background:rgba(255,255,255,.12);flex:none}
.ph .i svg{width:24px;height:24px}
.ph small{display:block;font-size:12px;letter-spacing:2.5px;opacity:.55;text-transform:uppercase;font-weight:500}
.ph h4{font-size:21px;font-weight:600}
.line{font-size:16px;color:rgba(255,255,255,.75);margin:4px 0 14px;line-height:1.45}
.line em{font-style:normal;color:#fff}
.stats{display:flex;gap:26px;margin:4px 0 16px;flex-wrap:wrap}
.stat span{display:block;font-size:13px;color:rgba(255,255,255,.62);margin-bottom:4px}
.stat b{font-size:22px;font-weight:500;font-variant-numeric:tabular-nums}
.stat b small{font-size:14px;font-weight:400;opacity:.7;margin-left:2px}
.crimes{margin:0 0 16px;padding:12px 14px;border-radius:12px;background:rgba(255,138,122,.1)}
.crimes p{font-size:14.5px;line-height:1.5;color:rgba(255,255,255,.85)}
.crimes p b{color:#ffb2a8;font-weight:500;margin-right:6px;letter-spacing:1px}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.btn{font-size:15px;font-weight:500;padding:10px 17px;border-radius:19px;background:rgba(255,255,255,.1);color:rgba(255,255,255,.9);cursor:pointer;white-space:nowrap}
.btn.on{background:#f2f2f2;color:#141414}
.btn.warn{background:#ff8a7a;color:#141414}
.done{display:flex;justify-content:flex-end;margin-top:6px}
input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:6px;border-radius:3px;margin:6px 0 18px;
  background:linear-gradient(90deg,#fff var(--p,50%),rgba(255,255,255,.18) var(--p,50%));outline:none}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:24px;height:24px;border-radius:12px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.4)}
.toast{position:absolute;left:50%;bottom:28px;transform:translate(-50%,20px);opacity:0;transition:.25s;background:rgba(30,28,36,.96);
  padding:12px 20px;border-radius:14px;font-size:15px;pointer-events:none;z-index:6;white-space:nowrap}
.toast.show{opacity:1;transform:translate(-50%,0)}
/* phone: the map full width on top, the places under it; names on the map only for the selected place */
:host(.phone) .wrap{padding:20px 16px 24px;gap:16px}
:host(.phone) .title b{font-size:22px}
:host(.phone) .chip{padding:8px 12px;font-size:14px}
:host(.phone) .chip .w{display:none}
:host(.phone) .body{flex-direction:column;align-items:stretch;gap:18px}
:host(.phone) .mapbox{width:100%}
:host(.phone) .blip .b{width:38px;height:38px}
:host(.phone) .blip .b svg{width:19px;height:19px}
:host(.phone) .blip .n,:host(.phone) .blip .s{display:none}
:host(.phone) .lbl{display:none}
`;

const HTML = `
<div class="wrap">
  <div class="top">
    <div class="round" id="back" title="Back to Vice">${ICON.back}</div>
    <div class="title"><small>Vice City HQ</small><b>Vice Map</b></div>
    <div class="chip" id="chip"></div>
  </div>
  <div class="body">
    <div class="mapbox" id="mapbox">${MAP_SVG}<div id="blips"></div></div>
    <div class="side"><div class="label">Places</div><div id="list"></div></div>
  </div>
</div>
<div class="sheet" id="sheet"><div class="pick" id="pick"></div></div>
<div class="toast" id="toast"></div>
`;

if (!document.getElementById("vice-panel-font")) {
  const f = document.createElement("style");
  f.id = "vice-panel-font";
  f.textContent = `@font-face{font-family:Inter;src:url(${BASE}inter-latin.woff2) format("woff2");font-weight:100 900;font-display:swap}`;
  document.head.appendChild(f);
}

const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const STAR = '<svg viewBox="0 0 24 24"><path d="M12 2.6l2.9 6 6.6.8-4.9 4.5 1.3 6.5L12 17.2l-5.9 3.2 1.3-6.5L2.5 9.4l6.6-.8z"/></svg>';
const stars = (n, evading) => `<span class="stars${n ? "" : " evading"}">` + [0, 1, 2, 3, 4].map((i) => `<i class="${i < (n || evading) ? "on" : ""}">${STAR}</i>`).join("") + "</span>";
const ago = (t) => {
  const m = Math.max(0, Math.round((Date.now() / 1000 - t) / 60));
  return m < 1 ? "just now" : m < 60 ? `${m} min` : m < 1440 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${Math.floor(m / 1440)} days`;
};
const playtime = (mins) => { const h = Math.floor(mins / 60), m = Math.round(mins % 60); return h ? `${h} h ${m} m` : `${m} min`; };

class ViceMap extends HTMLElement {
  constructor() {
    super();
    this.root = this.attachShadow({ mode: "open" });
    this.root.innerHTML = `<style>${CSS}</style>${HTML}`;
    this.$ = (id) => this.root.getElementById(id);
    this.sel = null;
    this.offArmed = 0;
    this.$("blips").innerHTML = PLACES.map((p) =>
      `<div class="blip" data-id="${p.id}" style="left:${p.x / 10}%;top:${p.y / 10}%"><div class="b">${ICON[p.id]}</div><div class="n">${p.name}</div><div class="s"></div></div>`).join("");
    this.$("list").innerHTML = PLACES.map((p) =>
      `<div class="place" data-id="${p.id}"><div class="i">${ICON[p.id]}</div><div class="t"><h4>${p.name} <span style="opacity:.5;font-weight:400">· ${p.what}</span></h4><p></p></div></div>`).join("");
    this.root.addEventListener("click", (e) => {
      const t = e.target.closest && e.target.closest("[data-id]");
      if (t) return this.open(t.dataset.id);
      const a = e.target.closest && e.target.closest("[data-act]");
      if (a) return this.act(a.dataset.act, a.dataset.arg, a);
    });
    this.$("sheet").addEventListener("click", (e) => { if (e.target === this.$("sheet")) this.close(); });
    this.$("back").onclick = () => this.navigate("/vice");
    new ResizeObserver(() => {
      const was = this.className;
      this.classList.toggle("phone", this.offsetWidth < 760);
      if (this.className !== was) this.render();
    }).observe(this);
  }

  connectedCallback() {
    clearInterval(this.radioT);
    this.readRadio(); this.radioT = setInterval(() => { if (!document.hidden) this.readRadio(); }, 10000);
  }
  disconnectedCallback() { clearInterval(this.radioT); }

  set hass(h) { this._hass = h; this.render(); }
  set panel(p) {}  // HA hands this over; nothing to do

  st(e) { const s = this._hass && this._hass.states[e]; return s ? s.state : "unavailable"; }
  at(e, a) { const s = this._hass && this._hass.states[e]; return s ? s.attributes[a] : undefined; }
  num(e) { const v = parseFloat(this.st(e)); return isNaN(v) ? null : v; }
  navigate(path) { history.pushState(null, "", path); window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } })); }
  toast(msg) {
    const t = this.$("toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(this.toastT); this.toastT = setTimeout(() => t.classList.remove("show"), 2600);
  }
  call(domain, service, data, ok) {
    return this._hass.callService(domain, service, data).then(() => ok && this.toast(ok))
      .catch((e) => this.toast(`Didn't work: ${e.message || e.code || e}`));
  }
  async readRadio() {
    let n = null;
    try { n = await (await fetch(`${RADIO}/now`, { cache: "no-store" })).json(); } catch (e) { /* off: shown as off */ }
    const k = n ? [n.artist, n.title].join("|") : "off";
    if (k !== this.radioKey) { this.radioKey = k; this.radio = n; this.render(); }
  }

  // ---------- what each place shows: on (glows), a short line, and its Wanted problems ----------
  tvOn() { return !["off", "standby", "unavailable", "unknown"].includes(this.st(E.tv)); }
  info(id) {
    switch (id) {
      case "hq": {
        const c = this.num(E.cpu), r = this.num(E.ram);
        return { on: true, line: c == null ? "No readings" : `CPU <em>${Math.round(c)}%</em> · memory <em>${Math.round(r)}%</em>` };
      }
      case "tv": {
        if (!this.tvOn()) return { on: false, line: "Off" };
        const src = this.at(E.tv, "source"), vol = this.at(E.tv, "volume_level");
        return { on: true, line: `<em>On</em>${src ? " · " + esc(src) : ""}${vol != null ? " · vol " + Math.round(vol * 100) : ""}` };
      }
      case "ps5": {
        const on = this.st(E.ps5) === "on", game = this.st(E.ps5Media) === "playing" && this.at(E.ps5Media, "media_title");
        const last = this.st(E.ps5Last);
        return { on, line: on ? `<em>${game ? "Playing " + esc(game) : "On"}</em>` : `Rest mode${last && last !== "unknown" ? " · last " + esc(last) : ""}` };
      }
      case "nsw": {
        const on = this.st(E.nsw) === "on", mins = parseFloat(this.st(E.nswTime));
        return { on, line: (on ? "<em>Awake</em>" : "Asleep") + (mins > 0 ? ` · today ${playtime(mins)}` : "") };
      }
      case "radio": {
        const n = this.radio;
        if (!n) return { on: false, line: "Off air" };
        return { on: true, line: `<em>${esc(n.title || "On air")}</em>${n.artist ? " · " + esc(n.artist) : ""}` };
      }
      case "light": {
        const on = this.st(E.light) === "on", b = this.at(E.light, "brightness");
        return { on, line: on ? `<em>On</em> · ${Math.round((b || 0) / 2.55)}%` : "Off" };
      }
      case "vault": {
        const free = this.num(E.storeFree), use = this.num(E.storeUse);
        return { on: true, line: free == null ? "No readings" : `<em>${Math.round(free)} GB</em> free · ${Math.round(use)}% used` };
      }
    }
    return { on: false, line: "" };
  }
  crimes(id) { return (this.at(E.wanted, "crimes") || []).filter((c) => placeOf(c.key) === id); }

  render() {
    if (!this._hass) return;
    const n = parseInt(this.st(E.wanted)) || 0, ev = this.at(E.wanted, "evading") || 0;
    this.$("chip").innerHTML = n || ev ? `${stars(n, ev)}<span class="w">${n ? "Wanted" : "Evading"}</span>` : '<span class="dot"></span>All quiet';
    this.$("mapbox").classList.toggle("hot", n >= 3);
    for (const p of PLACES) {
      const i = this.info(p.id), bad = this.crimes(p.id).length > 0;
      const line = bad ? esc(this.crimes(p.id)[0].what) : i.line;
      for (const el of this.root.querySelectorAll(`[data-id="${p.id}"]`)) {
        el.classList.toggle("on", !!i.on);
        el.classList.toggle("bad", bad);
        el.classList.toggle("sel", this.sel === p.id);
        const s = el.querySelector(".s, p");
        // on the map just the first part ("Asleep", "440 GB free", the song): the full line is in the list
        const plain = line.replace(/<[^>]+>/g, "").split(" · ")[0];
        if (el.classList.contains("blip")) { if (s.textContent !== plain) s.textContent = plain; }
        else if (s._h !== line) { s._h = line; s.innerHTML = line; }
      }
    }
    if (this.sel) this.fill();
  }

  // ---------- the place card ----------
  open(id) { this.sel = id; this.$("sheet").classList.add("show"); this.render(); }
  close() { this.sel = null; this.$("sheet").classList.remove("show"); this.render(); }
  fill() {
    const p = PLACES.find((x) => x.id === this.sel), i = this.info(p.id), cr = this.crimes(p.id);
    let body = p.id === "hq" ? "" : `<p class="line">${i.line}</p>`;  // the PC's stats below say it already
    if (cr.length) body += `<div class="crimes">${cr.map((c) => `<p><b>${"★".repeat(c.stars)}</b>${esc(c.what)} · ${ago(c.since)}</p>`).join("")}</div>`;
    body += this.controls(p.id);
    const h = `<div class="ph"><div class="i">${ICON[p.id]}</div><div><small>${esc(p.what)}</small><h4>${esc(p.name)}</h4></div></div>${body}
      <div class="done"><span class="btn" data-act="close">Done</span></div>`;
    if (this.$("pick")._h === h) return;
    const slider = this.$("pick").querySelector("input[type=range]");
    if (slider && this.dragging) return;  // don't redraw under a finger on the brightness slider
    this.$("pick")._h = h;
    this.$("pick").innerHTML = h;
    const r = this.$("pick").querySelector("input[type=range]");
    if (r) {
      r.style.setProperty("--p", `${r.value}%`);
      r.oninput = () => { this.dragging = true; r.style.setProperty("--p", `${r.value}%`); };
      r.onchange = () => { this.dragging = false; this.call("light", "turn_on", { entity_id: E.light, brightness_pct: +r.value }); };
    }
  }
  controls(id) {
    const b = (act, label, arg = "", cls = "") => `<span class="btn ${cls}" data-act="${act}" data-arg="${esc(arg)}">${label}</span>`;
    switch (id) {
      case "hq": {
        const t = this.num(E.temp), up = Date.parse(this.st(E.up));
        const stat = (k, v, u) => `<div class="stat"><span>${k}</span><b>${v}<small>${u}</small></b></div>`;
        return `<div class="stats">${stat("CPU", Math.round(this.num(E.cpu) || 0), "%")}${stat("Memory", Math.round(this.num(E.ram) || 0), "%")}` +
          `${t != null ? stat("Temp", Math.round(t), "°C") : ""}${up ? stat("Up", Math.floor((Date.now() - up) / 3600000), "h") : ""}</div>` +
          `<div class="btns">${b("pc", "Lock PC", "pc_lock")}${b("pc", "Open VS Code", "pc_vscode")}${b("pcoff", Date.now() - this.offArmed < 4000 ? "Tap again to turn off" : "Turn off PC", "", Date.now() - this.offArmed < 4000 ? "warn" : "")}</div>`;
      }
      case "tv": {
        const on = this.tvOn(), src = this.at(E.tv, "source") || "";
        return `<div class="btns">${b("tv", on ? "Turn off" : "Turn on")}</div>` + (on ? `<div class="btns">${INPUTS.map(([n, s]) =>
          b("input", n, s, src === s || src === n ? "on" : "")).join("")}</div>` : "");
      }
      case "ps5": return `<div class="btns">${b("ps5", this.st(E.ps5) === "on" ? "Rest mode" : "Turn on")}</div>`;
      case "nsw": return this.st(E.nsw) === "on" ? `<div class="btns">${b("nswtv", "Put it on the TV")}</div>`
        : `<p class="line" style="font-size:14px;opacity:.7">It can't be woken over the network: press HOME on a Joy-Con.</p>`;
      case "radio": return this.radio ? `<div class="btns">${b("skip", this.radio.src === "live" ? "Back to my music" : "Skip song")}${b("nav", "Listen on the Vice panel", "/vice")}</div>` : "";
      case "light": {
        const on = this.st(E.light) === "on", k = this.at(E.light, "color_temp_kelvin"), mode = this.at(E.light, "color_mode");
        const pct = Math.round((this.at(E.light, "brightness") || 0) / 2.55);
        return `<div class="btns">${b("light", on ? "Turn off" : "Turn on")}</div>` + (on ? `<input type="range" min="1" max="100" value="${pct}">` +
          `<div class="btns">${WHITES.map(([n, kk]) => b("white", n, kk, mode === "color_temp" && Math.abs((k || 0) - kk) < 400 ? "on" : "")).join("")}</div>` : "");
      }
      case "vault": {
        const t = Date.parse(this.st(E.haBackup));
        const bad = this.crimes("vault").length;
        return `<p class="line" style="font-size:14.5px">${bad ? "" : "Nightly backup at 03:30 · fine<br>"}` +
          `${t ? `Home Assistant's own backup: ${ago(t / 1000)} ago` : ""}</p>`;
      }
    }
    return "";
  }
  act(a, arg, el) {
    switch (a) {
      case "close": return this.close();
      case "nav": return this.navigate(arg);
      case "pc": return this.call("rest_command", arg, {}, arg === "pc_lock" ? "Locking the PC" : "Opening VS Code on the PC");
      case "pcoff":
        if (Date.now() - this.offArmed < 4000) {
          this.offArmed = 0;
          this.call("rest_command", "pc_poweroff", {}, "Turning off the PC. This map goes offline with it.");
        } else {
          this.offArmed = Date.now();
          setTimeout(() => this.render(), 4100);
        }
        return this.render();
      case "tv": return this.call("media_player", this.tvOn() ? "turn_off" : "turn_on", { entity_id: E.tv }, this.tvOn() ? "TV off" : "TV on");
      case "input": return this.call("media_player", "select_source", { entity_id: E.tv, source: arg }, `TV: ${el.textContent}`);
      case "ps5": return this.call("switch", this.st(E.ps5) === "on" ? "turn_off" : "turn_on", { entity_id: E.ps5 }, this.st(E.ps5) === "on" ? "PS5: rest mode" : "Waking the PS5");
      case "nswtv": return this.call("script", "turn_on", { entity_id: "script.switch_on_tv" }, "TV: Switch");
      case "skip":
        return fetch(`${RADIO}/skip`, { method: "POST" }).then(() => { this.toast("Skipping"); setTimeout(() => this.readRadio(), 1500); })
          .catch(() => this.toast("Vice Radio isn't answering"));
      case "light": return this.call("light", this.st(E.light) === "on" ? "turn_off" : "turn_on", { entity_id: E.light });
      case "white": return this.call("light", "turn_on", { entity_id: E.light, color_temp_kelvin: +arg });
    }
  }
}

if (!customElements.get("vice-map")) customElements.define("vice-map", ViceMap);
