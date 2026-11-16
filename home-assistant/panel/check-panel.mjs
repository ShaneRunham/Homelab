// Check the Vice panel in headless Brave: logs in with the long-lived token (~/.config/ha-token via the bot's
// gaming.HA_TOKEN), opens /vice, counts redraws for a while and takes screenshots.
// Usage: node check-panel.mjs <out dir> [seconds=60] [width=1920] [height=1200]
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const [out, secs = "60", W = "1920", H = "1200"] = process.argv.slice(2);
const HA = "http://127.0.0.1:8123";
const tokFile = execFileSync("python3", ["-c", "import sys,os;sys.path.insert(0,os.path.expanduser('~/homelab/discord-bot'));import gaming;print(os.path.expanduser(gaming.HA_TOKEN))"]).toString().trim();
const token = execFileSync("cat", [tokFile]).toString().trim();
const prof = mkdtempSync(path.join(tmpdir(), "vice-panel-check-"));
const PORT = 9400 + Math.floor(Math.random() * 400);
const br = spawn("brave-browser", ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, `--window-size=${W},${H}`,
  "--autoplay-policy=no-user-gesture-required", "--no-first-run", "--hide-scrollbars", "about:blank"], { detached: true, stdio: "ignore" });
const kill = () => { try { process.kill(-br.pid, "SIGKILL"); } catch (e) {} try { rmSync(prof, { recursive: true, force: true }); } catch (e) {} };
process.on("exit", kill);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let tgt;
for (let i = 0; i < 50 && !tgt; i++) { await sleep(200); try { tgt = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find((t) => t.type === "page"); } catch (e) {} }
const ws = new WebSocket(tgt.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const wait = {}; const logs = [];
ws.addEventListener("message", (m) => {
  const d = JSON.parse(m.data);
  if (d.id && wait[d.id]) { wait[d.id](d.result); delete wait[d.id]; }
  if (d.method === "Runtime.exceptionThrown") logs.push("EXCEPTION " + JSON.stringify(d.params.exceptionDetails).slice(0, 400));
  if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error") logs.push("console.error " + JSON.stringify(d.params.args).slice(0, 300));
});
const cmd = (method, params = {}) => new Promise((r) => { const i = ++id; wait[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await cmd("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result.value;
const shot = async (name) => { const r = await cmd("Page.captureScreenshot", { format: "png" }); writeFileSync(path.join(out, name + ".png"), Buffer.from(r.data, "base64")); console.log(path.join(out, name + ".png")); };

await cmd("Page.enable"); await cmd("Runtime.enable");
await cmd("Emulation.setDeviceMetricsOverride", { width: +W, height: +H, deviceScaleFactor: 1, mobile: false });
await cmd("Page.navigate", { url: HA + "/manifest.json" }); await sleep(800);
await ev(`localStorage.setItem("hassTokens", ${JSON.stringify(JSON.stringify({ access_token: token, token_type: "Bearer", expires_in: 1e9, hassUrl: HA, clientId: HA + "/", expires: Date.now() + 1e12, refresh_token: "" }))})`);
await cmd("Page.navigate", { url: HA + "/vice" });
await sleep(9000);
// find the panel through HA's shadow roots, count its redraws and DOM writes
const find = `(function f(r){ for (const e of r.querySelectorAll("*")) { if (e.localName === "vice-panel") return e; if (e.shadowRoot) { const x = f(e.shadowRoot); if (x) return x; } } return null; })(document)`;
const found = await ev(`(() => { const p = ${find}; if (!p) return false; window.__p = p; p.__renders = 0; p.__hass = 0;
  const r = p.render.bind(p); p.render = () => { p.__renders++; r(); };
  const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(p), "hass"); Object.defineProperty(p, "hass", { set(h) { p.__hass++; d.set.call(p, h); }, configurable: true });
  p.__muts = 0; new MutationObserver((m) => { p.__muts += m.length; }).observe(p.shadowRoot || p.root, { subtree: true, childList: true, characterData: true });
  return true; })()`);
if (!found) { console.log("vice-panel not found", logs); process.exit(1); }
await shot("panel");
await sleep(+secs * 1000);
console.log(JSON.stringify(await ev(`({ seconds: ${secs}, hassUpdates: __p.__hass, redraws: __p.__renders, domMutations: __p.__muts,
  newsPictures: [...__p.root.querySelectorAll("#nrow img")].map((i) => i.currentSrc.replace(location.origin, "") + " " + i.naturalWidth + "px"),
  watched: __p.used ? __p.used.size : null })`)));
await ev(`__p.root.querySelector("#nrow .ncard").click()`); await sleep(2500);
console.log("post picture:", await ev(`(() => { const i = __p.root.getElementById("nHero"); return i.currentSrc.replace(location.origin, "") + " " + i.naturalWidth + "px"; })()`));
await shot("news-post");
if (logs.length) console.log(logs.join("\n"));
ws.close(); kill(); process.exit(0);
