// Vice panel for Home Assistant: the same look as Vice Home on the TV (~/tv-launcher/vice).
// A custom panel (panel_custom in configuration.yaml); HA hands it `hass`, so it uses the viewer's own login.
// Tablet (wide) and phone (narrow) layouts. Mock-ups: ~/homelab/home-assistant/panel/mockup.

const BASE = "/local/vice-panel/";
// Vice Radio (~/homelab/radio): stream and now-playing JSON on the tailnet, same host as HA (tailscale serve :8447)
const RADIO = `${location.protocol}//${location.hostname}:8447`;
const E = {
  tv: "media_player.lg_tv",
  ps5: "switch.ps5", ps5Media: "media_player.playstation_5", ps5Activity: "sensor.ps5_activity",
  ps5Last: "sensor.ps5_last_game",
  nsw: "binary_sensor.nintendo_switch", nswTime: "sensor.bedroom_sam_s_switch_used_screen_time",
  ps3: "switch.ps3", ps3Status: "sensor.ps3_status", ps3Game: "sensor.ps3_last_game", ps3Last: "sensor.ps3_last_played",
  light: "light.ceiling_light", lightLast: "sensor.ceiling_light_last", busy: "binary_sensor.pc_busy",
  cpu: "sensor.system_monitor_processor_use", temp: "sensor.system_monitor_processor_temperature",
  ram: "sensor.system_monitor_memory_usage", ssd: "sensor.system_monitor_disk_free",
  backups: "sensor.system_monitor_disk_free_mnt_storage",
  weather: "weather.home", services: "sensor.homelab_services", problems: "sensor.homelab_state", wanted: "sensor.wanted_level", person: "person.shane_runham",
};
const INPUTS = [["Home", "Vice Home"], ["PS5", "PS5 Game Console"], ["Switch", "Nintendo Switch"], ["PS3", "PS3 Game Console"], ["Sky", "Sky Box"]];
const WHITES = [["Warm", 2700], ["Neutral", 4000], ["Cool", 6500]];
const COLOURS = [["Pink", [255, 77, 109]], ["Purple", [155, 92, 255]], ["Blue", [63, 169, 255]], ["Orange", [255, 154, 60]]];
const CONDITIONS = {
  "clear-night": "Clear", cloudy: "Cloudy", exceptional: "Unusual weather", fog: "Fog", hail: "Hail",
  lightning: "Thunder", "lightning-rainy": "Thunderstorms", partlycloudy: "Partly cloudy", pouring: "Heavy rain",
  rainy: "Rain", snowy: "Snow", "snowy-rainy": "Sleet", sunny: "Sunny", windy: "Windy", "windy-variant": "Windy",
};

// weather icons (lucide, ISC), the same ones Vice Home uses on the TV
const wx = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const CLOUD = '<path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>';
const WX = {
  sun: wx('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'),
  moon: wx('<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'),
  part: wx('<path d="M12 2v2M4.93 4.93l1.41 1.41M20 12h2M19.07 4.93l-1.41 1.41M15.947 12.65a4 4 0 0 0-5.925-4.128"/><path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6Z"/>'),
  cloud: wx('<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>'),
  rain: wx(CLOUD + '<path d="M16 14v6M8 14v6M12 16v6"/>'),
  snow: wx(CLOUD + '<path d="M8 15h.01M8 19h.01M12 17h.01M12 21h.01M16 15h.01M16 19h.01"/>'),
  fog: wx(CLOUD + '<path d="M16 17H7M17 21H9"/>'),
  storm: wx('<path d="M6 16.326A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 .5 8.973"/><path d="m13 12-3 5h4l-3 5"/>'),
};
const WX_ICON = { sunny: "sun", "clear-night": "moon", partlycloudy: "part", cloudy: "cloud", fog: "fog", rainy: "rain", pouring: "rain",
  snowy: "snow", "snowy-rainy": "snow", hail: "rain", lightning: "storm", "lightning-rainy": "storm" };

// Vice OSD icons (lucide, ISC): the same ones the TV's cards use
const OSD_ICON = {
  server: wx('<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><path d="M6 6h.01M6 18h.01"/>'),
  phone: wx('<rect width="14" height="20" x="5" y="2" rx="2"/><path d="M12 18h.01"/>'),
  bell: wx('<path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/>'),
  radio: wx('<path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/>'),
};

// device logos (simple-icons, CC0): one fixed logo per card
const logo = (d, box, name) => `<svg class="logo ${name}" viewBox="${box}" fill="#fff" role="img" aria-label="${name.toUpperCase()}"><path d="${d}"/></svg>`;
const LOGO = {
  lg: logo("M14.522 14.078h3.27v1.33h-4.847v-6.83h1.577v5.5zm6.74-1.274h1.284v1.195c-.236.09-.698.18-1.137.18-1.42 0-1.893-.721-1.893-2.186 0-1.398.45-2.221 1.869-2.221.791 0 1.24.248 1.612.722l.982-.903c-.6-.855-1.646-1.114-2.629-1.114-2.208 0-3.368 1.205-3.368 3.504 0 2.288 1.047 3.528 3.358 3.528 1.06 0 2.096-.27 2.66-.665V11.53h-2.739v1.274zM5.291 6.709a5.29 5.29 0 1 1 0 10.582 5.291 5.291 0 1 1 0-10.582m3.16 8.457a4.445 4.445 0 0 0 1.31-3.161v-.242l-.22.001H6.596v.494h2.662l-.001.015a3.985 3.985 0 0 1-3.965 3.708 3.95 3.95 0 0 1-2.811-1.165 3.952 3.952 0 0 1-1.164-2.811c0-1.061.414-2.059 1.164-2.81a3.951 3.951 0 0 1 2.81-1.164l.252.003v-.495l-.251-.003a4.475 4.475 0 0 0-4.47 4.469c0 1.194.465 2.316 1.309 3.161a4.444 4.444 0 0 0 3.16 1.31 4.444 4.444 0 0 0 3.162-1.31m-2.91-1.297V9.644H5.04v4.72h1.556v-.495H5.543zm-1.265-3.552a.676.676 0 1 0-.675.674.676.676 0 0 0 .675-.674", "0 6.709 24 10.582", "lg"),
  ps5: logo("M10.4499 14.56905a1.38287 1.38287 0 001.38287-1.38287v-2.37841a.83315.83315 0 01.83416-.83315h2.68403a.03732.03732 0 00.03631-.03732V9.4612a.03631.03631 0 00-.0363-.0363H12.1172a1.38287 1.38287 0 00-0.12768 1.38286v2.38043a.83416.83416 0 01-.83315.83415H7.25347a.03631.03631 0 00-.03631.03632v.47608a.03631.03631 0 00.03631.03631zm6.04488-3.21156V9.4612a.03631.03631 0 01.0363-.0363h7.30772a.03732.03732 0 01.03732.0363v.47609a.03833.03833 0 01-.03732.03732h-6.20929a.03631.03631 0 00-.0363.03631v1.2356a.3954.3954 0 00.3964.39741h4.62267a1.46457 1.46457 0 010 2.9251h-6.0812a.03631.03631 0 01-.0363-.0363v-.47407a.03631.03631 0 01.0363-.03632h5.53047a.91586.91586 0 10-.00706-1.8307h-4.72656a.83315.83315 0 01-.83315-.83416m-10.84608.28645a.83466.83466 0 000-1.66932H.03654a.03732.03732 0 01-.03632-.03732V9.4612a.03631.03631 0 01.03632-.0363h6.1528a1.38388 1.38388 0 010 2.76673H1.9328a.83315.83315 0 00-.83315.83416v1.51299a.03631.03631 0 01-.03631.0363H.03654a.03631.03631 0 01-.03632-.04034v-1.51298a1.38287 1.38287 0 011.38388-1.37783Z", "0 9.425 24 5.15", "ps5"),
  nswitch: logo("M14.176 24h3.674c3.376 0 6.15-2.774 6.15-6.15V6.15C24 2.775 21.226 0 17.85 0H14.1c-.074 0-.15.074-.15.15v23.7c-.001.076.075.15.226.15zm4.574-13.199c1.351 0 2.399 1.125 2.399 2.398 0 1.352-1.125 2.4-2.399 2.4-1.35 0-2.4-1.049-2.4-2.4-.075-1.349 1.05-2.398 2.4-2.398zM11.4 0H6.15C2.775 0 0 2.775 0 6.15v11.7C0 21.226 2.775 24 6.15 24h5.25c.074 0 .15-.074.15-.149V.15c.001-.076-.075-.15-.15-.15zM9.676 22.051H6.15c-2.326 0-4.201-1.875-4.201-4.201V6.15c0-2.326 1.875-4.201 4.201-4.201H9.6l.076 20.102zM3.75 7.199c0 1.275.975 2.25 2.25 2.25s2.25-.975 2.25-2.25c0-1.273-.975-2.25-2.25-2.25s-2.25.977-2.25 2.25z", "0 0 24 24", "nswitch"),
  ps3: logo("M15.362 9.433h-3.148c-.97 0-1.446.6-1.446 1.38v2.365c0 .483-.228.83-.71.83H7.304a.035.035 0 00-.035.035v.47c0 .02.01.032.03.032h3.11c.97 0 1.45-.597 1.45-1.377v-2.363c0-.484.224-.832.71-.832h2.781c.02 0 .04-.014.04-.033v-.475c0-.02-.02-.035-.04-.035zm-9.266 0H.038c-.022 0-.038.017-.038.035v.477c0 .02.016.036.038.036h5.694c.48 0 .71.347.71.83s-.228.83-.71.83H1.228c-.7 0-1.227.586-1.227 1.365v1.513c0 .02.02.037.04.037h1.03c.02 0 .04-.016.04-.037v-1.513c0-.48.28-.82.68-.82H6.1c.97 0 1.444-.594 1.444-1.374 0-.778-.473-1.38-1.442-1.38zm17.453 2.498a.04.04 0 010-.056c.3-.25.45-.627.45-1.062 0-.778-.474-1.38-1.446-1.38h-6.057c-.02 0-.036.018-.036.038v.475c0 .02.02.04.04.04h5.7c.48 0 .715.35.715.83s-.23.83-.712.83h-5.7c-.02 0-.036.02-.036.04v.48c0 .02.016.033.037.033h5.7c.63.007.71.62.71.93v.06c0 .485-.23.833-.71.833h-5.7c-.02 0-.036.015-.036.034v.477c0 .02.015.037.036.037h6.05c.973 0 1.446-.645 1.446-1.38v-.057c0-.47-.15-.916-.45-1.19z", "0 9.43 24 5.14", "ps3"),
};

const ICON = {
  radio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9"/><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5"/><circle cx="12" cy="12" r="2"/><path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"/><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19"/></svg>',
  skip: '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M5 5.5v13l9.5-6.5z"/><path d="M18.5 5v14" fill="none" stroke-linecap="round" stroke-width="2.2"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
  // lucide "mic" (ISC)
  mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3"/></svg>',
};

const CSS = `
:host{display:block;position:relative;height:100%;min-height:100vh;overflow:hidden;background:#0d0a14;color:#fff;
  font-family:Inter,sans-serif;-webkit-font-smoothing:antialiased;-webkit-tap-highlight-color:transparent;user-select:none}
*{box-sizing:border-box;margin:0;padding:0}
svg{display:block}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:62% center;background:#0d0a14 url(${BASE}poster.jpg?v=2) 62% center/cover}
.scrim{position:absolute;inset:0;background:
  linear-gradient(90deg,rgba(10,6,20,.62) 0%,rgba(10,6,20,.30) 48%,rgba(10,6,20,.10) 75%),
  linear-gradient(180deg,rgba(10,6,20,.15) 0%,rgba(10,6,20,0) 22%,rgba(10,6,20,.25) 48%,rgba(10,6,20,.72) 100%)}
.wrap{position:relative;height:100%;overflow-y:auto;padding:40px 56px 40px}
.top{display:flex;justify-content:space-between;align-items:center}
.clock{font-size:20px;font-weight:450;opacity:.92;font-variant-numeric:tabular-nums}
.right{display:flex;gap:12px;align-items:center}
.home{display:flex;align-items:center;gap:10px;font-size:16px;color:rgba(255,255,255,.72);background:rgba(38,38,44,.6);padding:10px 16px;border-radius:22px}
.round{width:42px;height:42px;border-radius:21px;background:rgba(38,38,44,.6);display:grid;place-items:center;cursor:pointer}
.round svg{width:20px;height:20px}
.dot{width:8px;height:8px;border-radius:4px;background:#7ee2a8;box-shadow:0 0 0 3px rgba(126,226,168,.18);flex:none}
.dot.bad{background:#ff8a7a;box-shadow:0 0 0 3px rgba(255,138,122,.2)}
.dot.off{background:#9a96a3;box-shadow:none}
.hero{margin-top:36px}
.date{font-size:14px;letter-spacing:2.6px;font-weight:500;opacity:.72}
.greet{font-size:64px;font-weight:600;letter-spacing:-3.4px;margin-top:6px;text-shadow:0 2px 24px rgba(0,0,0,.18);white-space:nowrap}
.info{display:inline-flex;align-items:center;gap:10px;font-size:17px;color:rgba(255,255,255,.78);margin-top:10px;flex-wrap:wrap;padding:6px 14px;margin-left:-14px;border-radius:12px;background:rgba(14,10,24,.42)}  /* backing: it crossed the figures (2026-11-16), as on the TV */
.info b{color:#fff;font-weight:500}.info .sep{opacity:.5}
.info span{display:flex;align-items:center;gap:10px}
.wanted:empty{display:none}
.info #wanted > span{gap:2px}  /* id: beats :host(.phone) .info span{gap:7px} */
.info .wanted i{display:block;width:18px;height:18px}
.info .wanted svg{width:18px;height:18px;opacity:1;fill:rgba(0,0,0,.25);stroke:rgba(255,255,255,.55);stroke-width:1.5}
.info .wanted i.on svg{fill:#fff;stroke:#fff}
.info .wanted .evading i.on svg{animation:evade .8s steps(1) infinite}
@keyframes evade{50%{fill:rgba(0,0,0,.25);stroke:rgba(255,255,255,.55)}}
.dot.gone{display:none}
.info span.gta{display:block}  /* plain text flow: no flex gap inside "GTA VI in 7 days" */
.info svg{width:20px;height:20px;opacity:.75;flex:none}
.label{font-size:17px;font-weight:500;opacity:.92;margin-bottom:14px}
.label i{font-style:normal;opacity:.55;font-weight:400;margin-left:10px;font-size:15px}
.living{margin-top:44px}
.row{display:flex;gap:18px}
.row.two{margin-top:26px}
.row.two>div{flex:1;min-width:0}
.card{border-radius:14px;background:rgba(32,32,38,.82);box-shadow:0 8px 24px rgba(0,0,0,.25);display:flex;align-items:center;gap:12px;padding:0 16px;height:96px}
.card.dev{flex:1;min-width:0;cursor:pointer}
/* one frame for every device (TV, PS5, PS3) so the titles line up; game art fits whole, on a blurred copy of itself */
/* device cards: the logo is the title (top left), the switch top right, status and game below at full width */
.card.dev{flex-direction:column;align-items:stretch;justify-content:flex-start;gap:0;height:auto;padding:16px 20px}
.dtop{display:flex;align-items:center;justify-content:space-between;height:34px;margin-bottom:8px}
svg.logo{display:block;width:auto}
svg.logo.lg{height:21px}  /* its letters then match the PS5/PS3 wordmarks */
svg.logo.ps5,svg.logo.ps3{height:15px}
svg.logo.nswitch{height:24px}
.card.dev p{font-size:15px}
.card p.game{margin-top:4px;font-size:13px;color:rgba(255,255,255,.5)}
.card p.game:empty::before{content:"\\00a0"}  /* every card keeps two lines, so all three have the same shape */
.card p.game em{opacity:.8}
.big.off .lrow:not(:first-child){opacity:.4;transition:opacity .2s}
.card h4{font-size:20px;font-weight:500;margin-bottom:5px}
.card p{font-size:14px;color:rgba(255,255,255,.62);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card p em{font-style:normal;color:#fff;opacity:.9}
.sw{width:58px;height:34px;border-radius:17px;background:rgba(255,255,255,.16);position:relative;flex:none;cursor:pointer;transition:background .2s}
.sw::after{content:"";position:absolute;left:4px;top:4px;width:26px;height:26px;border-radius:13px;background:#cfcbd6;transition:left .2s,background .2s}
.sw.on{background:#f2f2f2}.sw.on::after{left:28px;background:#141414}
.sw.busy{opacity:.55}
.big{flex-direction:column;align-items:stretch;justify-content:center;gap:16px;padding:0 22px;height:150px}
.lrow{display:flex;align-items:center;gap:14px}
.lrow h4{margin:0;flex:1}
input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:10px;border-radius:5px;outline:none;
  background:linear-gradient(90deg,#f2f2f2 var(--p,100%),rgba(255,255,255,.14) var(--p,100%))}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:26px;height:26px;border-radius:13px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.4);cursor:pointer}
input[type=range]::-moz-range-thumb{width:26px;height:26px;border:0;border-radius:13px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.4)}
input[type=range]:disabled{opacity:.4}
.chips{display:flex;gap:10px;flex:1}
.chip,.btn{font-size:14px;font-weight:500;padding:9px 15px;border-radius:18px;background:rgba(255,255,255,.1);color:rgba(255,255,255,.88);cursor:pointer;white-space:nowrap}
.chip.on{background:#f2f2f2;color:#141414}
.btn.warn{background:#ff8a7a;color:#141414}
.cdot{width:30px;height:30px;border-radius:15px;flex:none;box-shadow:inset 0 0 0 2px rgba(255,255,255,.25);cursor:pointer}
.cdot.on{box-shadow:0 0 0 3px #fff}
.stats{display:flex;gap:28px}
.stat span{display:block;font-size:13px;color:rgba(255,255,255,.62);margin-bottom:4px;white-space:nowrap}
.stat b{font-size:22px;font-weight:500;font-variant-numeric:tabular-nums}
.stat b small{font-size:14px;font-weight:400;opacity:.7;margin-left:2px}
.btns{display:flex;gap:10px;flex-wrap:wrap}
/* sheets and the photo viewer are pinned to the screen: with the news row the panel is taller than a phone screen */
.sheet{position:fixed;inset:0;z-index:5;background:rgba(8,5,14,.55);display:none;align-items:center;justify-content:center}
.sheet.show{display:flex}
.pick{background:rgba(30,28,36,.96);border-radius:18px;padding:22px 24px 24px;box-shadow:0 24px 60px rgba(0,0,0,.5)}
.pick h4{font-size:18px;font-weight:500;margin-bottom:16px}
.pick .chip{font-size:16px;padding:12px 22px}
.done{display:flex;justify-content:flex-end;margin-top:18px}
.card.dev{-webkit-touch-callout:none}
.rlogo{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:600;letter-spacing:-.2px;min-width:0;white-space:nowrap}
.rname{min-width:0;overflow:hidden;text-overflow:ellipsis}
/* skip sits beside the song lines (the top row has no room on the tablet's four narrow cards) */
.card.radio{position:relative}
.card.radio p{padding-right:44px}
.round.rskip{position:absolute;right:16px;bottom:18px;width:34px;height:34px;border-radius:17px;background:rgba(255,255,255,.12)}
.round.rskip svg{width:15px;height:15px}
:host(.phone) .round.rskip{width:32px;height:32px}
.rart svg{width:20px;height:20px;margin:7px;opacity:.75}
.rart{width:34px;height:34px;border-radius:7px;flex:none;background:rgba(255,255,255,.12) center/cover;box-shadow:0 2px 8px rgba(0,0,0,.35)}
.tap{cursor:pointer}
.pick.wx{width:min(560px,92%)}
.wxnow{display:flex;align-items:center;gap:18px}
.wxnow svg{width:52px;height:52px;opacity:.9}
.wxnow b{font-size:34px;font-weight:600;letter-spacing:-1px}
.wxnow b small{font-size:20px;font-weight:400;opacity:.6;margin-left:6px}
.wxnow p{font-size:15px;color:rgba(255,255,255,.62);margin-top:2px}
.hours{display:flex;justify-content:space-between;margin-top:22px;padding-top:18px;border-top:1px solid rgba(255,255,255,.08)}
.hour{display:flex;flex-direction:column;align-items:center;gap:8px;font-size:14px;color:rgba(255,255,255,.62)}
.hour svg{width:26px;height:26px}
.hour b{font-size:16px;font-weight:500;color:#fff}
.wxnext{margin-top:18px;font-size:15px;color:rgba(255,255,255,.62)}
.wxnext b{color:#fff;font-weight:500}
.toast{position:absolute;left:50%;bottom:28px;transform:translate(-50%,20px);opacity:0;transition:.25s;background:rgba(30,28,36,.96);
  padding:12px 20px;border-radius:14px;font-size:15px;box-shadow:0 12px 40px rgba(0,0,0,.5);pointer-events:none;max-width:90%;text-align:center}
.toast.show{opacity:1;transform:translate(-50%,0)}
/* Vice OSD banner (2026-11-14, ~/tv-launcher/vice-layer-plan.md step 7): the TV's card at the panel's scale (0.8:
   this .card, the 100x56 icon frame at 80x45, the toast's colour). Tablet: drops in over the top bar (8px from the top,
   right edge = the cards' edge), covering only the home pill and round buttons for a few seconds; under them it covered
   the greeting (Shane picked this from mock-ups, 2026-11-14). Phone: full width under the top bar. Cards come from
   script.vice_osd through sensor.vice_osd. Tap to dismiss. */
.osd{position:absolute;right:56px;top:8px;z-index:30;width:min(453px,calc(100% - 112px));background:rgba(30,28,36,.96);
  box-shadow:0 18px 48px rgba(0,0,0,.5);opacity:0;transform:translateY(-10px);transition:opacity .25s,transform .25s;pointer-events:none}
.osd.show{opacity:1;transform:none;pointer-events:auto}
.osd .ic{width:80px;height:45px;border-radius:10px;background:rgba(255,255,255,.1);display:grid;place-items:center;flex:none}
.osd .ic svg{width:22px;height:22px}
.osd > div:last-child{min-width:0}
.osd h4{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.osd p{line-height:18px}
.osd p .dot{display:inline-block;margin:0 8px 1px 2px;vertical-align:middle}
.osd p .last{opacity:.75}
:host(.phone) .osd{left:20px;right:20px;top:74px;width:auto}
/* JARVIS: talk to Home Assistant Assist (pipeline JARVIS: Whisper, Claude, Kokoro), see ~/homelab/README.md */
.round{color:#fff}
.round,.chip,.btn,.cdot{position:relative}
.round::before,.chip::before,.btn::before,.sw::before{content:"";position:absolute;inset:-7px}
.cdot::before{content:"";position:absolute;inset:-10px}
.pick.jv{width:min(560px,92%)}
.jlog{display:flex;flex-direction:column;gap:12px;max-height:40vh;overflow-y:auto;margin-bottom:18px}
.jlog:empty{display:none}
.jlog p{font-size:16px;line-height:1.45;color:#fff;user-select:text}
.jlog p.you{color:rgba(255,255,255,.55);font-size:15px}
.jbar{display:flex;align-items:center;gap:12px}
.jmic{width:52px;height:52px;border-radius:26px;flex:none;display:grid;place-items:center;cursor:pointer;color:#fff;
  background:rgba(255,255,255,.1);transition:background .2s,color .2s,box-shadow .08s}
.jmic svg{width:22px;height:22px}
.jmic.on{background:#f2f2f2;color:#141414}
.jbar input{flex:1;min-width:0;height:44px;border:0;border-radius:22px;padding:0 18px;font:inherit;font-size:15px;color:#fff;
  background:rgba(255,255,255,.08);outline:none;user-select:text}
.jbar input::placeholder{color:rgba(255,255,255,.45)}
/* GTA VI news (Rockstar Newswire, file written by the bot's rockstar_news.py): picture cards, post sheet, photo viewer */
.gnews{margin-top:26px}
.nrow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}
.ncard{position:relative;aspect-ratio:16/9;border-radius:14px;overflow:hidden;background:rgba(32,32,38,.82);box-shadow:0 8px 24px rgba(0,0,0,.25);cursor:pointer}
.ncard img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.ncard .shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,6,20,0) 25%,rgba(10,6,20,.62) 58%,rgba(10,6,20,.95) 100%)}
.ncard .txt{text-shadow:0 1px 3px rgba(0,0,0,.6)}
.ncard .new,.nnew{position:absolute;top:10px;left:10px;font-size:11px;font-weight:600;letter-spacing:1px;padding:4px 8px;border-radius:8px;background:#f2f2f2;color:#141414}
.nhero{cursor:zoom-in}
.nphotos .vid{position:relative;display:block}
.nphotos .vid::after{content:"";position:absolute;left:50%;top:50%;width:0;height:0;margin:-9px 0 0 -6px;border-left:16px solid #fff;border-top:9px solid transparent;border-bottom:9px solid transparent;filter:drop-shadow(0 1px 4px rgba(0,0,0,.7))}
.ncard .txt{position:absolute;left:14px;right:14px;bottom:11px}
.ncard .src{font-size:12.5px;color:rgba(255,255,255,.72);white-space:nowrap}
.ncard .hl{font-size:15px;font-weight:600;line-height:1.25;margin-top:2px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.pick.npost{width:min(980px,94%);max-height:92%;overflow-y:auto;display:flex;gap:24px;padding:20px}
.nhero{width:46%;aspect-ratio:16/9;object-fit:cover;border-radius:12px;flex:none;align-self:flex-start;background:rgba(255,255,255,.06)}
.nbody{flex:1;min-width:0;display:flex;flex-direction:column}
.nmeta{font-size:12px;letter-spacing:2px;color:rgba(255,255,255,.6);font-weight:500;margin-top:2px}
.npost h4{font-size:22px;line-height:1.2;margin:8px 0 4px}
.nsub{font-size:15px;color:rgba(255,255,255,.62);margin-bottom:14px;user-select:text}
.nsub:empty{display:none}
.npost .btn{text-decoration:none}
.nphotos{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin-top:14px}
.nphotos:empty{display:none}
.nphotos img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;cursor:pointer;display:block}
.npost .done{margin-top:auto;padding-top:16px}
.viewer{position:fixed;inset:0;z-index:8;background:#050308;display:flex;align-items:center;justify-content:center}
.viewer[hidden]{display:none}
:host(.short) .viewer,:host(.phone) .viewer{padding-top:36px}  /* clear Android's status bar in the HA app */
:host(.short) .vcap,:host(.phone) .vcap{padding-bottom:52px}  /* and its navigation bar */
.viewer img{max-width:100%;max-height:100%;object-fit:contain}
.vcap{position:absolute;left:0;right:0;bottom:0;padding:60px 24px 22px;display:flex;justify-content:space-between;align-items:flex-end;gap:20px;font-size:14px;line-height:1.45;color:rgba(255,255,255,.9);background:linear-gradient(180deg,rgba(5,3,8,0),rgba(5,3,8,.88) 55%);pointer-events:none}
.vcap span{overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}
.vcap b{font-weight:500;white-space:nowrap}
.vnav{position:absolute;top:0;bottom:0;width:30%}
.vnav.prev{left:0}.vnav.next{right:0}
:host(.phone) .nrow{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:12px;scrollbar-width:none}
:host(.phone) .nrow::-webkit-scrollbar{display:none}
/* on the phone each post is as wide as the cards above (Shane, 2026-11-12); swipe for the next, the dots show where you are */
:host(.phone) .ncard{flex:0 0 100%;scroll-snap-align:start}
.ndots{display:none}
:host(.phone) .ndots{display:flex;justify-content:center;gap:7px;margin-top:10px}
.ndots i{width:6px;height:6px;border-radius:3px;background:rgba(255,255,255,.3);transition:background .2s}
.ndots i.on{background:#fff}
:host(.phone) .gnews{margin-top:28px}
:host(.phone) .pick.npost{flex-direction:column;gap:14px;padding:16px}
:host(.phone) .nhero{width:100%}
:host(.mid) .nrow{grid-template-columns:repeat(2,minmax(0,1fr))}
.jstate{font-size:14px;color:rgba(255,255,255,.55);margin-top:12px;min-height:20px}

/* phone */
:host(.phone) .scrim{position:fixed;background:linear-gradient(180deg,rgba(10,6,20,.30) 0%,rgba(10,6,20,.15) 20%,rgba(10,6,20,.55) 42%,rgba(10,6,20,.80) 100%)}
:host(.phone) .bg{position:fixed;object-position:50% center;background:#0d0a14 url(${BASE}poster-phone.jpg?v=2) center/cover}
/* phone: its own wallpaper (1080x2160 crop of the 4K GTA VI key-art loop, wall-phone.mp4, 2026-11-12), centred and pinned
   to the screen so it stays put while the panel scrolls */
:host(.phone) .wrap{padding:20px 20px 32px}
:host(.phone) .clock{font-size:17px}
:host(.phone) .home{font-size:13px;padding:7px 12px}
:host(.phone) .round{width:34px;height:34px}
:host(.phone) .round svg{width:17px;height:17px}
:host(.phone) .hero{margin-top:22px}
:host(.phone) .date{font-size:11px;letter-spacing:2px}
:host(.phone) .greet{font-size:34px;letter-spacing:-1.5px}  /* "Good afternoon, Shane" fits a 412 px phone */
:host(.phone) .info{font-size:13px;gap:7px;display:flex;margin-right:-14px}
:host(.phone) .info span{gap:7px}
:host(.phone) .info > .sep{display:none}
:host(.phone) .info > .sep.gta{display:block}  /* keep the dot between the weather and the countdown */
:host(.phone) .info > span:last-child{flex-basis:100%;margin-top:4px}
/* middle widths (760-960 px, the tablet in portrait): the light and PC cards stack; the status gets its own line */
:host(.mid) .row.two{flex-direction:column;gap:26px}
:host(.mid) .info > .sep{display:none}
:host(.mid) .info > .sep.gta{display:block}
:host(.mid) .info > span:last-child{flex-basis:100%;margin-top:4px}
/* short screens (under 1000 px tall: the tablet in landscape, the phone with Android's bars): tighter vertical
   spacing so the whole panel fits without scrolling (2026-11-12, second pass on the real devices) */
:host(.short) .wrap{padding-top:24px;padding-bottom:24px}
:host(.short) .hero{margin-top:18px}
:host(.short) .living{margin-top:26px}
:host(.short) .row.two{margin-top:16px}
:host(.phone.short) .wrap{padding-top:12px;padding-bottom:20px}
:host(.phone.short) .hero{margin-top:14px}
:host(.phone.short) .living{margin-top:24px}
:host(.phone.short) .row.two{margin-top:20px;gap:20px}
:host(.phone) .info svg{width:16px;height:16px}
:host(.phone) .living{margin-top:36px}
:host(.phone) .row{flex-direction:column;gap:10px}
:host(.phone) .row.two{margin-top:28px;gap:28px}
:host(.phone) .label{font-size:15px;margin-bottom:9px}
:host(.phone) .card{height:72px;padding:0 14px;gap:12px;border-radius:12px}
:host(.phone) .card.dev{flex:none}
:host(.phone) .card.dev{height:auto;gap:0;padding:14px 16px}
:host(.phone) .dtop{height:30px;margin-bottom:8px}
:host(.phone) svg.logo.lg{height:18px}
:host(.phone) svg.logo.ps5,:host(.phone) svg.logo.ps3{height:13px}
:host(.phone) .card.dev p{font-size:13.5px}
:host(.phone) .card h4{font-size:16px;margin-bottom:3px}
:host(.phone) .card p{font-size:12.5px}
:host(.phone) .card p.game{margin-top:2px;font-size:12.5px}
:host(.phone) .sw{width:50px;height:30px}
:host(.phone) .sw::after{width:22px;height:22px}
:host(.phone) .sw.on::after{left:24px}
:host(.phone) .big{height:auto;padding:16px;gap:14px}
:host(.phone) .chip,:host(.phone) .btn{font-size:12.5px;padding:8px 11px}
:host(.phone) .chips{gap:7px}
:host(.phone) .cdot{width:24px;height:24px}
:host(.phone) .lrow{gap:9px}
:host(.phone) .stats{gap:0;justify-content:space-between}
:host(.phone) .stat span{font-size:11px}
:host(.phone) .stat b{font-size:17px}
:host(.phone) .stat b small{font-size:11px}
:host(.phone) .btns{gap:7px}
`;

const HTML = `
<video class="bg" id="bg" muted loop playsinline autoplay preload="auto"></video>
<div class="scrim"></div>
<div class="wrap">
  <div class="top">
    <div class="clock" id="clock"></div>
    <div class="right">
      <div class="home"><span class="dot" id="homeDot"></span><span id="home"></span></div>
      <div class="round" id="jarvis" title="Talk to JARVIS">${ICON.mic}</div>
      <div class="round" id="menu" title="Menu">${ICON.menu}</div>
    </div>
  </div>
  <div class="hero">
    <div class="date" id="date"></div>
    <div class="greet" id="greet"></div>
    <div class="info"><span id="weather" class="tap" title="Weather details"></span><span class="sep gta">·</span><span id="gta" class="gta"></span><span class="sep">·</span><span><span class="wanted" id="wanted"></span><span class="dot" id="svcDot"></span><span id="svc"></span></span></div>
  </div>
  <div class="living">
    <div class="label">Bedroom</div>
    <div class="row">
      <div class="card dev" data-dev="tv"><div class="dtop">${LOGO.lg}<div class="sw" id="tvSw"></div></div><p id="tvSub"></p><p class="game" id="tvGame"></p></div>
      <div class="card dev" data-dev="ps5"><div class="dtop">${LOGO.ps5}<div class="sw" id="ps5Sw"></div></div><p id="ps5Sub"></p><p class="game" id="ps5Game"></p></div>
      <div class="card dev" data-dev="nsw"><div class="dtop">${LOGO.nswitch}<div class="sw" id="nswSw"></div></div><p id="nswSub"></p><p class="game" id="nswGame"></p></div>
      <div class="card dev" data-dev="ps3"><div class="dtop">${LOGO.ps3}<div class="sw" id="ps3Sw"></div></div><p id="ps3Sub"></p><p class="game" id="ps3Game"></p></div>
      <div class="card dev radio" id="radioCard"><div class="dtop"><span class="rlogo"><span class="rart" id="rArt"></span><span class="rname">Vice Radio</span></span><div class="sw" id="rSw"></div></div><p id="rSub"></p><p class="game" id="rSrc"></p><span class="round rskip" id="rSkip" title="Skip song">${ICON.skip}</span></div>
    </div>
  </div>
  <div class="row two">
    <div>
      <div class="label">Ceiling light</div>
      <div class="card big" id="lightCard">
        <div class="lrow"><h4 id="lightTxt"></h4><div class="sw" id="lightSw"></div></div>
        <div class="lrow"><input type="range" id="bright" min="1" max="100" step="1"></div>
        <div class="lrow"><div class="chips" id="whites"></div><div class="lrow" id="colours"></div></div>
      </div>
    </div>
    <div>
      <div class="label">PC <i id="pcNote"></i></div>
      <div class="card big">
        <div class="stats" id="stats"></div>
        <div class="btns">
          <span class="btn" id="pcOff">Turn off PC</span><span class="btn" id="pcLock">Lock PC</span><span class="btn" id="pcCode">Open VS Code</span>
        </div>
      </div>
    </div>
  </div>
  <div class="gnews" id="gnews" hidden>
    <div class="label">GTA VI news <i>From Rockstar Newswire</i></div>
    <div class="nrow" id="nrow"></div>
    <div class="ndots" id="ndots"></div>
  </div>
</div>
<div class="sheet" id="nSheet"><div class="pick npost">
  <img class="nhero" id="nHero" alt="">
  <div class="nbody">
    <div class="nmeta" id="nMeta"></div>
    <h4 id="nTitle"></h4>
    <p class="nsub" id="nSub"></p>
    <div class="btns" id="nBtns"></div>
    <div class="nphotos" id="nPhotos"></div>
    <div class="done"><span class="btn" data-close="nSheet">Done</span></div>
  </div>
</div></div>
<div class="viewer" id="viewer" hidden><img id="vImg" alt=""><div class="vcap"><span id="vAlt"></span><b id="vN"></b></div>
  <span class="vnav prev" id="vPrev" aria-label="Previous photo"></span><span class="vnav next" id="vNext" aria-label="Next photo"></span></div>
<div class="sheet" id="wxSheet"><div class="pick wx" id="wxBody"></div></div>
<div class="sheet" id="inputs"><div class="pick"><h4>Switch the TV to</h4><div class="btns" id="inputBtns"></div><div class="done"><span class="btn" data-close="inputs">Done</span></div></div></div>
<div class="sheet" id="jSheet"><div class="pick jv">
  <h4>JARVIS</h4>
  <div class="jlog" id="jLog"></div>
  <div class="jbar"><div class="jmic" id="jMic" title="Tap to talk">${ICON.mic}</div><input id="jText" placeholder="Or type here" enterkeyhint="send" autocomplete="off"></div>
  <p class="jstate" id="jState"></p>
  <div class="done"><span class="btn" id="jDone">Done</span></div>
</div></div>
<div class="toast" id="toast"></div>
<div class="card osd" id="osd"></div>
`;

if (!document.getElementById("vice-panel-font")) {
  const f = document.createElement("style");
  f.id = "vice-panel-font";
  f.textContent = `@font-face{font-family:Inter;src:url(${BASE}inter-latin.woff2) format("woff2");font-weight:100 900;font-display:swap}`;
  document.head.appendChild(f);
}

class VicePanel extends HTMLElement {
  constructor() {
    super();
    this.root = this.attachShadow({ mode: "open" });
    this.root.innerHTML = `<style>${CSS}</style>${HTML}`;
    this.$ = (id) => this.root.getElementById(id);
    this.pending = {};       // entity -> time of our last command, to show the switch as busy
    this.offArmed = 0;
    this.build();
    new ResizeObserver(() => {
      const w = this.offsetWidth, was = this.className;
      this.classList.toggle("phone", w < 760);
      this.wallpaper(w < 760);
      this.classList.toggle("mid", w >= 760 && w < 960);
      this.classList.toggle("short", this.offsetHeight < 1000);
      if (this.className !== was) this.render();
    }).observe(this);
  }

  // the clock changes exactly on the minute (HA keeps this element when you switch away, so restart it on return)
  connectedCallback() {
    clearTimeout(this.tick);
    const next = () => { this.renderClock(); this.tick = setTimeout(next, 60000 - (Date.now() % 60000) + 50); };
    next();
    this.hideSidebarForTablet();
    clearInterval(this.newsT);
    this.readNews(); this.newsT = setInterval(() => this.readNews(), 600000);
    clearInterval(this.radioT);
    this.readRadio(); this.radioT = setInterval(() => { if (!document.hidden) this.readRadio(); }, 10000);
    // the wallpaper stops while the app or tab is in the background (screen off, another app), and carries on after
    this.onVis = this.onVis || (() => { const v = this.$("bg"); if (document.hidden) v.pause(); else if (this.isConnected) v.play().catch(() => {}); });
    document.addEventListener("visibilitychange", this.onVis);
  }

  // The wallpaper: the phone gets its own portrait loop; tablet and desktop keep the wide one. Set here, not in the
  // markup, so a phone never downloads the big video first.
  wallpaper(phone) {
    // ?v= changes whenever the phone video is replaced, so the HA app doesn't keep showing a cached old one
    const v = this.$("bg"), want = `${BASE}${phone ? "wall-phone.mp4?v=2" : "wall.mp4?v=2"}`;
    if (v.getAttribute("src") === want) return;
    v.poster = `${BASE}${phone ? "poster-phone.jpg?v=2" : "poster.jpg?v=2"}`;
    v.src = want;
    v.play().catch(() => {});  // muted autoplay; the poster shows if it's refused
  }

  // The tablet's HA login never needs HA's own sidebar (it takes a fifth of the screen); the menu button still opens
  // it. Same as Profile > "Always hide the sidebar". Only once the panel is on the page, so HA hears the event.
  hideSidebarForTablet() {
    const h = this._hass;
    if (!this.isConnected || this.sidebarHidden || !h || !h.user || h.user.name !== "Tablet" || h.dockedSidebar === "always_hidden") return;
    this.sidebarHidden = true;
    this.dispatchEvent(new CustomEvent("hass-dock-sidebar", { detail: { dock: "always_hidden" }, bubbles: true, composed: true }));
  }

  disconnectedCallback() { clearTimeout(this.tick); clearInterval(this.newsT); clearInterval(this.radioT); this.radioWanted = false; this.stopRadio(); this.stopListening(true); document.removeEventListener("visibilitychange", this.onVis); }

  // ---------- Vice Radio: what the PC's 80s station plays; the switch plays it on this device ----------
  async readRadio() {
    let n = null;
    try { n = await (await fetch(`${RADIO}/now`, { cache: "no-store" })).json(); } catch (e) { /* station off: shown below */ }
    const key = n ? [n.src, n.artist, n.title, n.dir].join("|") : "off";
    if (key === this.radioKey) return;
    this.radioKey = key; this.radioNow = n;
    this.showRadio();
  }
  showRadio() {
    const n = this.radioNow, on = !!this.audio || !!this.radioStarting;
    this.$("rSw").classList.toggle("on", on);
    if (!n) { this.putText("rSub", "Off"); this.putText("rSrc", ""); this.put("rArt", ""); return; }
    // the song alone on the first line, the artist and where it's from on the second: the tablet's narrow card cut
    // "song · artist" off mid-name (2026-11-16)
    this.put("rSub", `<em>${esc(cleanTitle(n.title))}</em>`);
    const from = this.radioStarting ? "Starting…" : n.src === "local" ? `Your music${n.album ? " · " + cleanTitle(n.album) : ""}` : n.station || "Internet radio";
    this.putText("rSrc", n.artist && !this.radioStarting ? `${n.artist} · ${from}` : from);
    const art = this.$("rArt");
    if (art._dir === n.dir) return;
    art._dir = n.dir;
    art.innerHTML = n.dir ? "" : ICON.radio;  // a station visit has no cover: the radio icon instead of an empty square
    if (!n.dir || !(window.crypto && crypto.subtle)) { art.style.backgroundImage = ""; return; }
    crypto.subtle.digest("SHA-1", new TextEncoder().encode(n.dir)).then((d) => {
      if (art._dir !== n.dir) return;
      art.style.backgroundImage = `url("${BASE}radio/${[...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16)}.jpg")`;
    });
  }
  toggleRadio() {
    if (this.audio || this.radioStarting) { this.radioWanted = false; this.stopRadio(); return this.showRadio(); }
    this.radioWanted = true; this.radioTries = 0;
    this.startRadio();
  }
  // The stream takes ~6 s to start ("Starting…"); if it drops (Wi-Fi blip, the station restarting) it reconnects,
  // up to 3 times in a row
  startRadio() {
    let a;
    const lost = () => {
      if (this.audio !== a) return;
      this.stopRadio();
      if (++this.radioTries <= 3) { this.radioStarting = true; this.showRadio(); setTimeout(() => { if (this.radioWanted) this.startRadio(); }, 2000); }
      else { this.radioStarting = false; this.showRadio(); this.toast("Vice Radio isn't answering"); }
    };
    // Fed through Media Source Extensions (fetch the stream, append the pieces) it plays in about a second; a plain
    // <audio src=stream> waited ~4.5 s for its own buffer. Plain audio stays as the fallback.
    if (window.MediaSource && MediaSource.isTypeSupported("audio/mpeg")) a = msePlayer(`${RADIO}/vice-radio`, lost);
    else { a = new Audio(`${RADIO}/vice-radio`); a.onerror = lost; a.onended = lost; }
    a.onplaying = () => { if (this.audio === a) { this.radioTries = 0; this.radioStarting = false; this.showRadio(); } };
    this.audio = a; this.radioStarting = true;
    a.play().catch(() => { if (this.audio === a) { this.stopRadio(); this.radioStarting = false; this.showRadio(); this.toast("Vice Radio couldn't start"); } });
    this.showRadio(); this.readRadio();
  }
  // skips for the whole station (it's Shane's own): the next song fades in; on a station visit, back to his music
  async skipRadio() {
    const live = this.radioNow && this.radioNow.src === "live";
    try { await fetch(`${RADIO}/skip`, { method: "POST" }); } catch (e) { return this.toast("Vice Radio isn't answering"); }
    this.toast(live ? "Back to your music" : "Skipping");
    setTimeout(() => this.readRadio(), 1500);
  }
  stopRadio() {
    const a = this.audio; this.audio = null; this.radioStarting = false;
    if (a) {  // drops the stream, not just the sound
      const u = a.src;
      a.onerror = a.onended = a.onplaying = null;
      if (a.stopStream) a.stopStream();
      a.pause(); a.removeAttribute("src"); a.load();
      if (u && u.startsWith("blob:")) URL.revokeObjectURL(u);
    }
  }

  // ---------- GTA VI news: Rockstar Newswire posts with photos and videos (same feed as Vice Home on the TV) ----------
  async readNews() {
    let items;
    try { items = (await (await fetch(`${BASE}gta6.json?t=${Date.now()}`)).json()).items || []; }
    catch (e) { return; }  // keep what's shown
    const key = JSON.stringify(items.slice(0, 4));
    if (key === this.newsKey) return;  // same posts: leave the row (and its pictures) alone
    this.newsKey = key;
    const row = this.$("nrow"); row.innerHTML = "";
    this.$("gnews").hidden = !items.length;
    const seen = newsSeen(items);
    items.slice(0, 4).forEach((x) => {
      const c = document.createElement("div"), m = media(x);
      c.className = "ncard";
      c.innerHTML = `${x.image ? '<img alt="" loading="lazy">' : ""}<div class="shade"></div>`
        + (isNew(seen, x.id) ? '<span class="new">NEW</span>' : "")
        + `<div class="txt"><div class="src">${esc(day(x.date))}${m ? " · " + m : ""}</div><div class="hl">${esc(x.title)}</div></div>`;
      if (x.image) pic(c.querySelector("img"), x.image, 640);
      c.onclick = () => { markOpened(x.id); const b = c.querySelector(".new"); if (b) b.remove(); this.openNews(x); };
      row.appendChild(c);
    });
    // phone: one dot per post, the one in view lit
    const dots = this.$("ndots");
    dots.innerHTML = row.children.length > 1 ? "<i></i>".repeat(row.children.length) : "";
    const lit = () => {
      const w = row.firstElementChild ? row.firstElementChild.offsetWidth + 12 : 1, n = Math.round(row.scrollLeft / w);
      [...dots.children].forEach((d, i) => d.classList.toggle("on", i === n));
    };
    row.onscroll = lit; lit();
  }

  openNews(x) {
    const hero = x.image || (x.photos[0] && x.photos[0].url) || "";
    pic(this.$("nHero"), hero, 1920);
    this.$("nMeta").textContent = `${day(x.date)} · Rockstar Newswire`.toUpperCase();
    this.$("nTitle").textContent = x.title;
    this.$("nSub").textContent = x.subtitle || "";
    const link = (href, label) => `<a class="btn" href="${esc(href)}" target="_blank" rel="noopener">${esc(label)}</a>`;
    this.$("nBtns").innerHTML = x.videos.map((v, i) => link(`https://www.youtube.com/watch?v=${v}`, x.videos.length > 1 ? `Play video ${i + 1}` : "Play video")).join("")
      + link(x.url, "Read on Rockstar");
    // the strip: each video's thumbnail (opens YouTube), then the photos when there's more than one (a single photo is
    // the big picture already); the big picture opens full screen
    const ph = this.$("nPhotos"); ph.innerHTML = "";
    const view = (list, i) => { this.view = { list, i }; this.showPhoto(); this.$("viewer").hidden = false; };
    if (x.videos.length > 1) x.videos.forEach((v) => {  // one video: the Play video button is enough
      const a = document.createElement("a");
      a.className = "vid"; a.href = `https://www.youtube.com/watch?v=${v}`; a.target = "_blank"; a.rel = "noopener";
      a.innerHTML = `<img src="https://i.ytimg.com/vi/${esc(v)}/hqdefault.jpg" alt="Video" loading="lazy">`;
      ph.appendChild(a);
    });
    if (x.photos.length > 1) x.photos.slice(0, 16).forEach((p, i) => {
      const im = document.createElement("img");
      pic(im, p.url, 640); im.alt = p.alt || ""; im.loading = "lazy";
      im.onclick = () => view(x.photos, i);
      ph.appendChild(im);
    });
    const big = x.photos.length ? x.photos : [{ url: hero, alt: x.title }];
    this.$("nHero").onclick = () => view(big, 0);
    this.$("nSheet").classList.add("show");
  }

  showPhoto() {
    const { list, i } = this.view, p = list[i];
    pic(this.$("vImg"), p.url, 1920); this.$("vAlt").textContent = p.alt || ""; this.$("vN").textContent = `${i + 1} / ${list.length}`;
  }

  set narrow(v) { this._narrow = v; }

  // HA hands over a new hass on every state change anywhere (about 40 a minute, mostly the PC's system monitor):
  // redraw only when one of the entities the last redraw read has changed (HA keeps unchanged state objects as-is).
  set hass(h) {
    const old = this._hass;
    this._hass = h;
    this.hideSidebarForTablet();
    this.checkOsd(h);
    if (old && this.used && ![...this.used].some((id) => old.states[id] !== h.states[id])) return;
    this.render();
  }

  // HA hands the panel its config, including module_url (configuration.yaml, bumped ?v= after each change). If that
  // differs from the copy running here (a tablet that kept the page open), load the new one: once per version.
  set panel(p) {
    const want = p && p.config && p.config._panel_custom && p.config._panel_custom.module_url;
    if (!want || import.meta.url.endsWith(want)) return;
    try {
      if (sessionStorage.getItem("vice-panel-reloaded") === want) return;
      sessionStorage.setItem("vice-panel-reloaded", want);
    } catch (e) { return; }
    location.reload();
  }

  // ---------- actions ----------
  call(domain, service, data, okMsg) {
    return this._hass.callService(domain, service, data)
      .then(() => okMsg && this.toast(okMsg))
      .catch((e) => this.toast(`Didn't work: ${e.message || e.code || e}`));
  }

  toggle(entity, domain, on) {
    this.pending[entity] = Date.now();
    this.render();
    this.call(domain, on ? "turn_on" : "turn_off", { entity_id: entity })
      .finally(() => setTimeout(() => { delete this.pending[entity]; this.render(); }, 1500));
  }

  build() {
    this.$("inputs").onclick = (e) => this.closeInputs(e);
    this.$("weather").onclick = () => this.openWeather();
    this.root.addEventListener("click", (e) => { const c = e.target.closest && e.target.closest("[data-close]"); if (c) this.$(c.dataset.close).classList.remove("show"); });
    this.$("wxSheet").onclick = (e) => { if (e.target === this.$("wxSheet")) this.$("wxSheet").classList.remove("show"); };
    this.$("menu").onclick = () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
    this.$("jarvis").onclick = () => this.openJarvis();
    this.$("nSheet").onclick = (e) => { if (e.target === this.$("nSheet")) this.$("nSheet").classList.remove("show"); };
    this.$("viewer").onclick = (e) => {
      const v = this.view;
      if (e.target === this.$("vPrev") && v.i > 0) { v.i--; return this.showPhoto(); }
      if (e.target === this.$("vNext") && v.i < v.list.length - 1) { v.i++; return this.showPhoto(); }
      this.$("viewer").hidden = true;
    };
    this.$("jDone").onclick = () => this.closeJarvis();
    this.$("jSheet").onclick = (e) => { if (e.target === this.$("jSheet")) this.closeJarvis(); };
    this.$("jMic").onclick = () => (this.rec ? this.stopListening() : this.listen());
    this.$("jText").onkeydown = (e) => {
      const t = e.target.value.trim();
      if (e.key !== "Enter" || !t) return;
      e.target.value = ""; e.target.blur();
      this.converse({ start_stage: "intent", input: { text: t } }, t);
    };
    const dev = (key, entity, domain) => {
      const card = this.root.querySelector(`[data-dev="${key}"]`);
      let held = false, t;
      if (key === "tv") {  // press and hold the TV card: pick an input
        card.addEventListener("pointerdown", () => { held = false; t = setTimeout(() => { held = true; this.openInputs(); }, 500); });
        ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => card.addEventListener(ev, () => clearTimeout(t)));
        card.addEventListener("contextmenu", (e) => e.preventDefault());
      }
      card.onclick = () => {
        if (held) { held = false; return; }
        const on = this.state(entity) === "on" || (key === "tv" && this.isTvOn());
        if (key === "ps3" && !on) return this.toast("The PS3 can't be turned on remotely. Use its power button, then enable HEN.");
        this.toggle(entity, domain, !on);
      };
    };
    dev("tv", E.tv, "media_player");
    dev("ps5", E.ps5, "switch");
    dev("ps3", E.ps3, "switch");
    // Switch: no network power control, so a tap puts it on the TV (HDMI 2) when it's awake
    this.root.querySelector('[data-dev="nsw"]').onclick = () => this.state(E.nsw) === "on"
      ? this.call("script", "turn_on", { entity_id: "script.switch_on_tv" }, "TV: Switch")
      : this.toast("The Switch can't be woken remotely. Press HOME on a Joy-Con.");

    this.$("lightSw").onclick = () => this.toggle(E.light, "light", this.state(E.light) !== "on");
    const b = this.$("bright");
    b.oninput = () => { b.style.setProperty("--p", `${b.value}%`); this.putText("lightTxt", `On · ${b.value}%`); this.dragging = true; };
    b.onchange = () => { this.dragging = false; this.call("light", "turn_on", { entity_id: E.light, brightness_pct: +b.value }); };

    const whites = this.$("whites");
    WHITES.forEach(([name, k]) => {
      const c = document.createElement("span");
      c.className = "chip"; c.textContent = name; c.dataset.k = k;
      c.onclick = () => this.call("light", "turn_on", { entity_id: E.light, color_temp_kelvin: k });
      whites.appendChild(c);
    });
    const colours = this.$("colours");
    COLOURS.forEach(([, rgb]) => {
      const c = document.createElement("span");
      c.className = "cdot"; c.style.background = `rgb(${rgb})`; c.dataset.rgb = rgb.join(",");
      c.onclick = () => this.call("light", "turn_on", { entity_id: E.light, rgb_color: rgb });
      colours.appendChild(c);
    });

    this.$("radioCard").onclick = () => this.toggleRadio();
    this.$("rSkip").onclick = (e) => { e.stopPropagation(); this.skipRadio(); };
    this.$("pcLock").onclick = () => this.call("rest_command", "pc_lock", {}, "Locking the PC");
    this.$("pcCode").onclick = () => this.call("rest_command", "pc_vscode", {}, "Opening VS Code on the PC");
    this.$("pcOff").onclick = () => {
      const btn = this.$("pcOff");
      if (Date.now() - this.offArmed < 4000) {
        this.offArmed = 0; btn.textContent = "Turn off PC"; btn.classList.remove("warn");
        return this.call("rest_command", "pc_poweroff", {}, "Turning off the PC. This panel goes offline with it.");
      }
      this.offArmed = Date.now(); btn.textContent = "Tap again to turn off"; btn.classList.add("warn");
      setTimeout(() => { if (Date.now() - this.offArmed >= 4000) { btn.textContent = "Turn off PC"; btn.classList.remove("warn"); } }, 4100);
    };
  }

  closeInputs(e) { if (e.target === this.$("inputs")) this.$("inputs").classList.remove("show"); }

  // tap the weather: today, the next hours and tomorrow (Met.no via weather.get_forecasts)
  async openWeather() {
    const sheet = this.$("wxSheet"), body = this.$("wxBody");
    body.innerHTML = '<p class="wxnext">Getting the forecast…</p>';
    sheet.classList.add("show");
    const get = (type) => this._hass.connection.sendMessagePromise({ type: "call_service", domain: "weather", service: "get_forecasts",
      service_data: { type }, target: { entity_id: E.weather }, return_response: true })
      .then((r) => r.response[E.weather].forecast);
    let daily, hourly;
    try { [daily, hourly] = await Promise.all([get("daily"), get("hourly")]); }
    catch (e) { body.innerHTML = `<p class="wxnext">Couldn't get the forecast: ${esc(e.message || e.code || e)}</p>`; return; }
    const icon = (c) => WX[WX_ICON[c] || "cloud"];
    const name = (c) => CONDITIONS[c] || c;
    const rain = (mm) => !mm ? "no rain" : mm < 1 ? "a little rain" : `${Math.round(mm)} mm rain`;
    const t = daily[0], tm = daily[1], now = this.attr(E.weather, "temperature");
    const wind = this.attr(E.weather, "wind_speed"), wunit = this.attr(E.weather, "wind_speed_unit") || "km/h";
    const hours = hourly.slice(1, 13).filter((_, i) => i % 2 === 0);   // the next 12 hours, every 2 hours
    body.innerHTML = `
      <div class="wxnow">${icon(this.state(E.weather))}<div>
        <b>${Math.round(now)}°<small>${Math.round(t.temperature)}° / ${Math.round(t.templow)}°</small></b>
        <p>${esc(name(this.state(E.weather)))} · ${rain(t.precipitation)} today${wind != null ? ` · wind\u00a0${Math.round(wind)}\u00a0${esc(wunit)}` : ""}</p>
      </div></div>
      <div class="hours">${hours.map((h) => `<div class="hour">${esc(time12(new Date(h.datetime)).replace(":00", ""))}${icon(h.condition)}<b>${Math.round(h.temperature)}°</b></div>`).join("")}</div>
      ${tm ? `<p class="wxnext"><b>Tomorrow</b> · ${esc(name(tm.condition))}, ${Math.round(tm.temperature)}° / ${Math.round(tm.templow)}°, ${rain(tm.precipitation)}</p>` : ""}
      <div class="done"><span class="btn" data-close="wxSheet">Done</span></div>`;
  }

  openInputs() {
    if (!this.isTvOn()) return this.toast("Turn the TV on first.");
    const list = this.attr(E.tv, "source_list") || [], cur = this.attr(E.tv, "source");
    const box = this.$("inputBtns"); box.innerHTML = "";
    INPUTS.filter(([, src]) => list.includes(src)).forEach(([name, src]) => {
      const b = document.createElement("span");
      b.className = "chip" + (src === cur ? " on" : ""); b.textContent = name;
      b.onclick = (e) => {
        e.stopPropagation(); this.$("inputs").classList.remove("show");
        this.call("media_player", "select_source", { entity_id: E.tv, source: src }, `TV: ${name}`);
      };
      box.appendChild(b);
    });
    this.$("inputs").classList.add("show");
  }

  // ---------- JARVIS (Assist pipeline over HA's websocket, the same way HA's own Assist dialog does it) ----------
  // Speech: the mic streams 16-bit PCM to the pipeline (Whisper on the PC); HA stops listening by itself after a pause.
  // Known commands are answered by HA locally, everything else by Claude; the reply plays in the George voice.
  openJarvis() {
    this.$("jSheet").classList.add("show");
    if (Date.now() - (this.convAt || 0) > 300000) { this.conv = null; this.$("jLog").innerHTML = ""; }  // new chat after 5 quiet minutes
    this.listen();
  }

  closeJarvis() {
    this.$("jSheet").classList.remove("show");
    this.stopListening(true);
    if (this.unsub) { this.unsub(); this.unsub = null; }
    if (this.audio) this.audio.pause();
  }

  jState(t) { this.$("jState").textContent = t; }

  jSay(text, you) {
    const p = document.createElement("p");
    if (you) p.className = "you";
    p.textContent = text;
    this.$("jLog").appendChild(p);
    this.$("jLog").scrollTop = 1e6;
  }

  async listen() {
    if (this.audio) this.audio.pause();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return this.jState("No microphone here: type instead.");
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } }); }
    catch (e) { return this.jState("I can't use the microphone (allow it for the Home Assistant app). You can type instead."); }
    const ctx = new AudioContext();
    const src = ctx.createMediaStreamSource(stream), proc = ctx.createScriptProcessor(4096, 1, 1);
    const rec = this.rec = { stream, ctx, proc, queue: [], handler: null };
    proc.onaudioprocess = (e) => {
      if (this.rec !== rec) return;
      const f = e.inputBuffer.getChannelData(0), pcm = new Int16Array(f.length);
      let sum = 0;
      for (let i = 0; i < f.length; i++) { const s = Math.max(-1, Math.min(1, f[i])); pcm[i] = s * 32767; sum += s * s; }
      const level = Math.min(1, Math.sqrt(sum / f.length) * 6);
      this.$("jMic").style.boxShadow = `0 0 0 ${Math.round(level * 10)}px rgba(255,255,255,.18)`;
      if (rec.handler == null) rec.queue.push(pcm); else this.sendAudio(rec.handler, pcm);
    };
    src.connect(proc); proc.connect(ctx.destination);
    this.$("jMic").classList.add("on");
    this.jState("Listening…");
    this.converse({ start_stage: "stt", input: { sample_rate: ctx.sampleRate } });
  }

  sendAudio(handler, pcm) {
    const msg = new Uint8Array(1 + (pcm ? pcm.byteLength : 0));
    msg[0] = handler;
    if (pcm) msg.set(new Uint8Array(pcm.buffer), 1);
    this._hass.connection.socket.send(msg);
  }

  // quiet: closing the sheet, so don't touch the status line
  stopListening(quiet) {
    const rec = this.rec;
    if (!rec) return;
    this.rec = null;
    rec.proc.disconnect(); rec.stream.getTracks().forEach((t) => t.stop()); rec.ctx.close();
    if (rec.handler != null) this.sendAudio(rec.handler);  // an empty message ends the audio
    this.$("jMic").classList.remove("on");
    this.$("jMic").style.boxShadow = "";
    if (!quiet) this.jState("Thinking…");
  }

  async converse(run, typed) {
    if (this.unsub) { this.unsub(); this.unsub = null; }
    if (typed) { this.stopListening(true); this.jSay(typed, true); this.jState("Thinking…"); }
    const rec = this.rec;
    const done = () => { if (this.unsub) { this.unsub(); this.unsub = null; } };
    try {
      this.unsub = await this._hass.connection.subscribeMessage((ev) => {
        const d = ev.data || {};
        if (ev.type === "run-start" && rec) {
          rec.handler = d.runner_data.stt_binary_handler_id;
          rec.queue.splice(0).forEach((pcm) => this.sendAudio(rec.handler, pcm));
          if (this.rec !== rec) this.sendAudio(rec.handler);  // already stopped before HA was ready: end the audio now
        } else if (ev.type === "stt-vad-end") {
          if (this.rec === rec) this.stopListening();
        } else if (ev.type === "stt-end") {
          if (this.rec === rec) this.stopListening();
          const t = d.stt_output && d.stt_output.text.trim();
          if (t) this.jSay(t.charAt(0).toUpperCase() + t.slice(1).replace(/\.$/, ""), true);
          this.jState("Thinking…");
        } else if (ev.type === "intent-end") {
          const o = d.intent_output || {};
          this.conv = o.conversation_id; this.convAt = Date.now();
          const speech = o.response && o.response.speech && o.response.speech.plain && o.response.speech.plain.speech;
          if (speech) this.jSay(speech);
          this.jState("");
        } else if (ev.type === "tts-end") {
          const url = d.tts_output && d.tts_output.url;
          if (url) { this.audio = new Audio(url); this.audio.play().catch(() => {}); }
        } else if (ev.type === "error") {
          if (this.rec === rec) this.stopListening(true);
          this.jState(d.code === "stt-no-text-recognized" ? "I didn't catch that. Tap the mic and try again." : `Something went wrong: ${d.message || d.code}`);
          done();
        } else if (ev.type === "run-end") {
          done();
        }
      }, { type: "assist_pipeline/run", end_stage: "tts", conversation_id: this.conv || null, ...run });
    } catch (e) {
      if (this.rec === rec) this.stopListening(true);
      this.jState(`Couldn't start: ${e.message || e.code || e}`);
    }
  }

  // ---------- Vice OSD banner: a new sensor.vice_osd (script.vice_osd) shows once, then the next ----------
  checkOsd(h) {
    // a tag taken off (script.vice_osd_clear, e.g. the call was answered): drop those banners, close the one showing
    const c = h.states["sensor.vice_osd_clear"];
    if (c && this.osdClearSeen !== undefined && c.state !== this.osdClearSeen && Date.now() - Date.parse(c.state) < 30000) {
      const tag = c.attributes.tag;
      this.osdQ = (this.osdQ || []).filter((o) => !o.tag || o.tag !== tag);
      if (this.osdCur && this.osdCur.tag === tag && this.osdDone) this.osdDone();
    }
    if (c) this.osdClearSeen = c.state;
    const s = h.states["sensor.vice_osd"];
    if (!s || !this.root) return;
    if (this.osdSeen === undefined) { this.osdSeen = s.state; return; }  // the card that was there when the page opened
    if (s.state === this.osdSeen) return;
    this.osdSeen = s.state;
    if (Date.now() - Date.parse(s.state) > 30000) return;
    (this.osdQ = this.osdQ || []).push(s.attributes);
    this.osdNext();
  }
  osdNext() {
    if (this.osdOn || !(this.osdQ && this.osdQ.length)) return;
    const o = this.osdQ.shift(), el = this.$("osd"), esc = (t) => String(t || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
    el.innerHTML = `<div class="ic">${OSD_ICON[o.kind] || OSD_ICON.bell}</div><div><h4>${esc(o.title)}</h4><p>` +
      (o.dot === "bad" ? '<span class="dot bad"></span>' : "") + esc(o.line) + (o.em ? (o.line ? " · " : "") + `<em>${esc(o.em)}</em>` : "") +
      (o.sub ? `<br><span class="last">${esc(o.sub)}</span>` : "") + "</p></div>";
    this.osdOn = true; this.osdCur = o; el.classList.add("show");
    const done = this.osdDone = () => {
      clearTimeout(this.osdT); el.onclick = null; this.osdDone = this.osdCur = null; el.classList.remove("show");
      setTimeout(() => { this.osdOn = false; this.osdNext(); }, 300);
    };
    el.onclick = done;
    this.osdT = setTimeout(done, (+o.ttl || 8) * 1000);
  }

  toast(msg) {
    const t = this.$("toast");
    t.textContent = msg; t.classList.add("show");
    clearTimeout(this.toastT);
    this.toastT = setTimeout(() => t.classList.remove("show"), 3500);
  }

  // ---------- state ----------
  st(id) { if (this.used) this.used.add(id); return this._hass && this._hass.states[id]; }
  // a line's text set only when it changed: rewriting the same text still costs a layout and repaint
  put(id, h) { const el = this.$(id); if (el._shown !== h) { el._shown = h; el.innerHTML = h; } }
  putText(id, t) { const el = this.$(id); if (el._shownText !== t) { el._shownText = t; el.textContent = t; } }
  state(id) { const s = this.st(id); return s ? s.state : "unavailable"; }
  attr(id, a) { const s = this.st(id); return s ? s.attributes[a] : undefined; }
  num(id) { const v = parseFloat(this.state(id)); return Number.isFinite(v) ? v : null; }
  isTvOn() { return !["off", "unavailable", "unknown", "standby"].includes(this.state(E.tv)); }

  setSwitch(id, on, entity) {
    const sw = this.$(id);
    sw.classList.toggle("on", on);
    sw.classList.toggle("busy", !!this.pending[entity]);
  }

  renderClock() {
    const now = new Date(), h = now.getHours();
    this.putText("clock", time12(now));
    const pad = (n) => String(n).padStart(2, "0");
    this.putText("date", `${pad(now.getDate())}.${pad(now.getMonth() + 1)}.${now.getFullYear()}`);
    // GTA VI countdown (release 19 Nov 2026, midnight local); gone after launch day
    const days = Math.round((new Date(2026, 10, 19) - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 864e5);
    // launch-day mode: from 19 Nov "out now" for a week, and your play time as soon as there is some
    const played = this.num("sensor.gta_vi_minutes_played") || 0;
    const text = days > 1 ? `GTA VI in <b>${days} days</b>` : days === 1 ? "GTA VI <b>tomorrow</b>"
      : played > 0 ? `GTA VI · <b>${playtime(played)}</b> played` : days >= -6 ? "GTA VI <b>out now</b>" : "";
    this.put("gta", text);
    this.root.querySelectorAll(".gta").forEach((el) => { el.style.display = text ? "" : "none"; });
    this.putText("greet", h < 5 ? "Still up, Shane?" : h < 12 ? "Good morning, Shane" : h < 18 ? "Good afternoon, Shane" : "Good evening, Shane");
  }

  // Second line of a console card: the game being played, else "Last: <game>" (HA remembers it).
  game(kind, playing) {
    const name = playing || known(this.state(kind === "ps5" ? E.ps5Last : E.ps3Last));
    this.put(kind + "Game", !name ? "" : playing ? `Playing <em>${esc(name)}</em>` : `Last: ${esc(name)}`);
  }

  render() {
    if (!this._hass) return;
    this.used = new Set();  // filled by st(): the entities this redraw depends on
    this.renderClock();

    const home = this.state(E.person);
    this.putText("home", home === "home" ? "Shane is home" : home === "not_home" ? "Shane is out" : `Shane: ${home}`);
    this.$("homeDot").className = "dot" + (home === "home" ? "" : " off");

    const t = this.attr(E.weather, "temperature");
    this.put("weather", t == null ? "Weather unavailable"
      : `${WX[WX_ICON[this.state(E.weather)] || "cloud"]}<b>${Math.round(t)}°C</b> ${CONDITIONS[this.state(E.weather)] || this.state(E.weather)}`);
    // a problem from the homelab (the bot's checks, same list as the phone alerts) beats "All 6 services up"
    const probs = Object.values(this.attr(E.problems, "problems") || {});
    // Wanted Level (2026-11-16, ~/homelab/discord-bot/wanted.py): stars instead of the red dot; worst problem first
    const stars = parseInt(this.state(E.wanted)) || 0, evading = this.attr(E.wanted, "evading") || 0;
    const crimes = this.attr(E.wanted, "crimes") || [];
    this.put("wanted", wantedStars(stars, evading));
    this.putText("svc", probs.length ? problemLine(crimes.length ? [crimes[0].what, ...probs.slice(1)] : probs) : this.state(E.services));
    this.$("svcDot").className = "dot" + (stars || evading ? " gone" : !probs.length && this.attr(E.services, "good") ? "" : " bad");

    // PS5: first line power, second line the game (playing now, else the last one HA remembers)
    const ps5On = this.state(E.ps5) === "on";
    this.setSwitch("ps5Sw", ps5On, E.ps5);
    const playing = this.state(E.ps5Media) === "playing" && this.attr(E.ps5Media, "media_title");
    this.put("ps5Sub", this.state(E.ps5) === "unavailable" ? "Not reachable" : ps5On ? "<em>On</em>" : "Rest mode");
    this.game("ps5", playing);

    // Switch: awake (ping) and whether the TV is showing it; second line today's screen time (Nintendo, cloud)
    const nswOn = this.state(E.nsw) === "on";
    this.setSwitch("nswSw", nswOn, E.nsw);
    const onTv = this.isTvOn() && /switch|nintendo|hdmi 2/i.test(this.attr(E.tv, "source") || "");
    this.put("nswSub", nswOn ? `<em>On</em>${onTv ? " · on the TV" : ""}` : "Asleep");
    const mins = parseFloat(this.state(E.nswTime));
    this.put("nswGame", mins > 0 ? `Today: ${playtime(mins)}` : "");

    // PS3: unplugged since 2026-11-16 (the Switch has its HDMI 2), so its card only shows while it's on
    const ps3On = this.state(E.ps3) === "on";
    this.root.querySelector('[data-dev="ps3"]').style.display = ps3On ? "" : "none";
    this.setSwitch("ps3Sw", ps3On, E.ps3);
    const now3 = known(this.state(E.ps3Game));
    this.put("ps3Sub", ps3On ? (this.attr(E.ps3Status, "webman") ? "<em>On</em>" : "<em>On</em> · enable HEN") : "Off");
    this.game("ps3", ps3On && now3);

    // TV
    const tvOn = this.isTvOn();
    this.setSwitch("tvSw", tvOn, E.tv);
    const src = this.attr(E.tv, "source"), vol = this.attr(E.tv, "volume_level");
    this.put("tvSub", tvOn ? `<em>On</em>${vol != null ? " · Vol " + Math.round(vol * 100) : ""}` : "Off");
    this.put("tvGame", tvOn && src ? `Input: ${esc(shortSource(src))}` : "");

    // Light (HA only knows what it last sent: the bulb can't report back)
    const lOn = this.state(E.light) === "on";
    this.setSwitch("lightSw", lOn, E.light);
    this.$("lightCard").classList.toggle("off", !lOn);
    // while it's off, the faded controls show what it comes back on at (HA remembers it in sensor.ceiling_light_last)
    const bri = this.attr(E.light, "brightness");
    const pct = lOn && bri ? Math.max(1, Math.round((bri / 255) * 100)) : Math.round(this.num(E.lightLast) || 100);
    const mode = lOn ? this.attr(E.light, "color_mode") : this.attr(E.lightLast, "color_mode");
    const k = lOn ? this.attr(E.light, "color_temp_kelvin") : this.attr(E.lightLast, "kelvin");
    const rgb = lOn ? this.attr(E.light, "rgb_color") : this.attr(E.lightLast, "rgb");
    const white = mode === "color_temp" && k && WHITES.find(([, wk]) => Math.abs(k - wk) < 400);
    const colour = mode === "rgb" && rgb && COLOURS.find(([, c]) => c.join(",") === rgb.join(","));
    const tone = white ? white[0] : colour ? colour[0] : mode === "rgb" ? "Colour" : "";
    const b = this.$("bright");
    if (!this.dragging) {
      b.value = pct; b.style.setProperty("--p", `${pct}%`);
      this.putText("lightTxt", lOn ? `On · ${pct}%${tone ? " · " + tone : ""}` : this.state(E.light) === "off" ? "Off" : "Unknown");
    }
    this.$("whites").querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", !!white && white[1] == c.dataset.k));
    this.root.querySelectorAll(".cdot").forEach((c) => c.classList.toggle("on", !!colour && colour[1].join(",") === c.dataset.rgb));

    // PC
    const temp = this.num(E.temp), ssd = this.num(E.ssd);
    this.putText("pcNote", temp != null && temp >= 80 ? "Running hot" : this.state(E.busy) === "on" ? "Busy"
      : ssd != null && ssd < 10 ? "SSD nearly full" : "All quiet");
    const stat = (name, v, unit) => `<div class="stat"><span>${name}</span><b>${v == null ? "–" : Math.round(v)}<small>${unit}</small></b></div>`;
    this.put("stats", stat("CPU", this.num(E.cpu), "%") + stat("Temp", temp, "°C") + stat("RAM", this.num(E.ram), "%")
      + stat("SSD free", ssd, "GB") + stat("Backups free", this.num(E.backups), "GB"));  // "free" on the phone too (2026-11-16)
  }
}

// A news picture at display size: vice-tv keeps 640 and 1920 px copies of Rockstar's 3840x2160 pictures in news/
// (file name = the first 16 hex of the address's SHA-1). The original if there's no copy (yet).
function pic(im, url, w) {
  im._want = url;
  const show = (src) => { if (im._want !== url) return; im.onerror = src !== url ? () => { im.onerror = null; im.src = url; } : null; im.src = src; };
  if (!url || !(window.crypto && crypto.subtle)) return show(url);
  crypto.subtle.digest("SHA-1", new TextEncoder().encode(url))
    .then((d) => show(`${BASE}news/${w}-${[...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16)}.jpg`), () => show(url));
}
// The radio through Media Source Extensions: fetch the MP3 stream, append it as it arrives; trims what played over a
// minute ago. lost() runs once if the stream ends or fails. Same as Vice Home's player.
function msePlayer(url, lost) {
  const a = new Audio(), ms = new MediaSource(), ctl = new AbortController(), q = [];
  let sb = null, dead = false;
  const fail = () => { if (!dead) { dead = true; ctl.abort(); lost(); } };
  const pump = () => {
    if (dead || !sb || sb.updating || !q.length) return;
    try {
      if (a.currentTime > 120 && sb.buffered.length && sb.buffered.start(0) < a.currentTime - 90) return sb.remove(0, a.currentTime - 60);
      const parts = q.splice(0), out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
      let o = 0; for (const p of parts) { out.set(p, o); o += p.length; }
      sb.appendBuffer(out);
    } catch (e) { fail(); }
  };
  a.src = URL.createObjectURL(ms);
  ms.addEventListener("sourceopen", async () => {
    try {
      sb = ms.addSourceBuffer("audio/mpeg");
      sb.addEventListener("updateend", pump);
      const res = await fetch(url, { signal: ctl.signal, cache: "no-store" });
      if (!res.ok || !res.body) return fail();
      const rd = res.body.getReader();
      for (;;) { const x = await rd.read(); if (dead) return; if (x.done) return fail(); q.push(x.value); pump(); }
    } catch (e) { fail(); }
  });
  a.onerror = fail;
  a.stopStream = () => { dead = true; ctl.abort(); };
  return a;
}
// "Still They Ride (2022 Remaster)" -> "Still They Ride" (same as Vice Home)
function cleanTitle(t) { return String(t || "").replace(/\s*[([][^)\]]*remaster[^)\]]*[)\]]/ig, "").replace(/\s+-\s+[^-]*remaster.*$/i, ""); }
// "2:05 pm"
function time12(d) { const h = d.getHours(); return `${h % 12 || 12}:${String(d.getMinutes()).padStart(2, "0")} ${h < 12 ? "am" : "pm"}`; }
// a problem message without its markdown or the command in brackets: "Container `x` is exited (Exited 2h)" -> "Container x is exited"
function cleanProblem(m) { m = String(m).replace(/[`*]/g, "").split(/\.\s/)[0].replace(/\s*\((?:[^()]|\([^()]*\))*\)\s*$/, ""); return m.length > 60 ? m.slice(0, 58).replace(/[\s,;:]+\S*$/, "") + "…" : m; }  // cut at a word
const STAR = '<svg viewBox="0 0 24 24"><path d="M12 2.6l2.9 6 6.6.8-4.9 4.5 1.3 6.5L12 17.2l-5.9 3.2 1.3-6.5L2.5 9.4l6.6-.8z"/></svg>';
function wantedStars(n, evading) {  // same as Vice Home (~/tv-launcher/vice/vice.js)
  const lit = n || evading;
  if (!lit) return "";
  return `<span class="${n ? "" : "evading"}">` + [0, 1, 2, 3, 4].map(i => `<i class="${i < lit ? "on" : ""}">${STAR}</i>`).join("") + "</span>";
}
function problemLine(list) { return cleanProblem(list[0]) + (list.length > 1 ? ` · +${list.length - 1} more` : ""); }
function known(v) { return v && !["None", "unavailable", "unknown", ""].includes(v) ? v : null; }
// "PS5 Game Console" -> "PS5", "ITVX - fresh, free streaming" -> "ITVX", "Tubi: Free Movies & TV" -> "Tubi"
function shortSource(s) { return s === "Vice Home" ? "Home" : s.replace(/ Game Console$/, "").split(/ - |: /)[0]; }
// "2026-11-10" -> "10 Nov"; what a post carries
function day(iso) { const d = iso ? iso.split("-") : null; return d ? `${+d[2]} ${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+d[1] - 1]}` : ""; }
// "3 h 20 m" / "45 min"
function playtime(m) { m = Math.round(m); return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} m` : ""}`; }
// "New" badges, remembered on this device: a post is new from when it first appears until it's opened (or 3 days)
const SEEN_KEY = "vice-gta6-seen";
function loadSeen() { try { return JSON.parse(localStorage.getItem(SEEN_KEY)); } catch (e) { return null; } }
function saveSeen(st) { try { localStorage.setItem(SEEN_KEY, JSON.stringify(st)); } catch (e) { /* private mode: no badges */ } }
function newsSeen(items) {
  let st = loadSeen();
  const now = Date.now();
  if (!st) { st = { first: {}, opened: {} }; items.forEach((x) => { st.first[x.id] = 0; }); }  // first visit: nothing is "new"
  items.forEach((x) => { if (!(x.id in st.first)) st.first[x.id] = now; });
  saveSeen(st);
  return st;
}
function isNew(st, id) { return !st.opened[id] && st.first[id] > 0 && Date.now() - st.first[id] < 3 * 864e5; }
function markOpened(id) { const st = loadSeen(); if (st) { st.opened[id] = 1; saveSeen(st); } }
function media(x) { return x.videos.length ? "Video" : x.photos.length > 1 ? `${x.photos.length} photos` : ""; }
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

if (!customElements.get("vice-panel")) customElements.define("vice-panel", VicePanel);
