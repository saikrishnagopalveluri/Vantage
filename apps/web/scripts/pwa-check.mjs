// PWA smoke check driven over the Chrome DevTools Protocol (no extra dependencies).
//   node scripts/pwa-check.mjs online    -> with the app running: manifest, icons, SW, cache warm-up
//   (stop the web server)
//   node scripts/pwa-check.mjs offline   -> reuses the same profile: cached feed + offline fallback
// Set CHROME to override the browser path, APP for the origin, API_USER for the identity used.
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const mode = process.argv[2] ?? "online";
const APP = process.env.APP ?? "http://localhost:3000";
const CHROME = process.env.CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PROFILE = join(tmpdir(), "vantage-pwa-check");
const PORT = 9333;
mkdirSync(PROFILE, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const check = (name, ok, detail = "") => {
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  (${detail})` : ""}`);
};

const chrome = spawn(
  CHROME,
  [`--headless=new`, `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, "--no-first-run", "--disable-gpu", "about:blank"],
  { stdio: "ignore" },
);

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = targets.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await connect());
await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));
let nextId = 0;
const pending = new Map();
ws.addEventListener("message", ({ data }) => {
  const message = JSON.parse(data);
  if (message.id && pending.has(message.id)) pending.get(message.id)(message);
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const id = ++nextId;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
const evaluate = async (expression) => {
  const { result } = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  return result?.result?.value;
};
const waitFor = async (expression, ms = 15000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await evaluate(expression).catch(() => false)) return true;
    await sleep(250);
  }
  return false;
};
const go = async (path) => {
  await send("Page.navigate", { url: `${APP}${path}` });
  await sleep(600);
};

await send("Page.enable");
await send("Runtime.enable");

try {
  if (mode === "online") {
    await go("/onboarding");
    await waitFor("document.readyState === 'complete'");

    const manifestUrl = await evaluate("document.querySelector('link[rel=manifest]')?.href");
    check("manifest is linked", !!manifestUrl, manifestUrl);
    const manifest = await (await fetch(manifestUrl)).json();
    check("manifest is installable (standalone + start_url + name)", manifest.display === "standalone" && !!manifest.start_url && !!manifest.name);
    const sizes = new Set(manifest.icons.map((i) => i.sizes));
    check("manifest has 192 and 512 icons", sizes.has("192x192") && sizes.has("512x512"));
    check("manifest has a maskable icon", manifest.icons.some((i) => i.purpose === "maskable"));
    for (const icon of manifest.icons) {
      const res = await fetch(new URL(icon.src, APP));
      check(`icon ${icon.src} loads as image/png`, res.ok && res.headers.get("content-type") === "image/png");
    }
    const ios = await evaluate(`({
      touch: !!document.querySelector('link[rel=apple-touch-icon]'),
      capable: !!document.querySelector('meta[name=mobile-web-app-capable], meta[name=apple-mobile-web-app-capable]'),
      viewportFit: document.querySelector('meta[name=viewport]')?.content.includes('viewport-fit=cover'),
      theme: !!document.querySelector('meta[name=theme-color]')
    })`);
    check("iOS: apple-touch-icon, standalone meta, viewport-fit, theme-color", ios.touch && ios.capable && ios.viewportFit && ios.theme, JSON.stringify(ios));

    await evaluate("navigator.serviceWorker.ready.then(() => true)");
    check(
      "service worker activates",
      await waitFor("navigator.serviceWorker.getRegistration().then(r => r?.active?.state === 'activated')"),
    );

    // Onboard a real user so /feed has personal data to cache.
    const userId = `pwa-check-${Date.now()}`;
    const roles = await (await fetch(`${APP}/api/taxonomy/roles?limit=1`)).json();
    const legal = await (await fetch(`${APP}/api/public/legal`)).json();
    const created = await evaluate(`fetch('/api/onboarding', {method:'POST', headers:{'Content-Type':'application/json','X-User-Id':'${userId}'},
      body: JSON.stringify({target_role_ids:['${roles[0].id}'], consent:{terms_version:'${legal.terms_version}', privacy_version:'${legal.privacy_version}', over_18:true}})}).then(r => r.status)`);
    check("test user onboarded through the proxy", created === 201, String(created));
    await evaluate(`localStorage.setItem('vantage.userId', '${userId}')`);

    await go("/feed");
    await waitFor("document.querySelector('h1')?.textContent && !document.body.innerText.includes('Loading')");
    await go("/feed"); // second load is controlled by the worker
    check("page is controlled by the service worker", await waitFor("!!navigator.serviceWorker.controller"));
    check("feed renders online", await waitFor("document.querySelector('h1')?.textContent.length > 0"));
    for (const p of ["/career", "/saved", "/profile"]) {
      await go(p);
      await waitFor("document.querySelector('h1')?.textContent.length > 0");
    }
    const cached = await evaluate(`(async () => {
      const out = [];
      for (const name of await caches.keys()) for (const req of await (await caches.open(name)).keys()) out.push(new URL(req.url).pathname);
      return out;
    })()`);
    check("app shell and personal reads are cached", cached.includes("/offline") && cached.some((p) => p.startsWith("/api/feed/")) && cached.some((p) => p.startsWith("/api/profile/")), `${cached.length} entries`);
    check("static assets are cached", cached.some((p) => p.startsWith("/_next/static/")));
  } else {
    await go("/feed");
    // Behaviour, not wording: the shell and greeting render, and neither the profile nor the feed
    // fell back to the "can't be reached" error, so both came from the cache.
    const ok = await waitFor(
      "/Good (morning|afternoon|evening)/.test(document.querySelector('h1')?.textContent ?? '') && !document.body.innerText.includes(\"can't be reached\")",
      20000,
    );
    check("feed renders with the server stopped (cached shell + cached data)", ok);
    // The banner follows the browser's connectivity flag, which stays true while only our server is down.
    await send("Network.enable");
    await send("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    check("offline banner is shown when the browser goes offline", await waitFor("document.body.innerText.includes(\"You're offline\")", 5000));
    await go("/never-visited-page");
    check("unknown page falls back to the offline screen", await waitFor("document.body.innerText.includes(\"You're offline\")", 10000));
  }
} finally {
  await send("Browser.close").catch(() => {}); // closes child processes too, so the debugging port is free next run
  ws.close();
  chrome.kill();
}
console.log(failures === 0 ? "\nAll checks passed." : `\n${failures} check(s) failed.`);
process.exit(failures === 0 ? 0 : 1);
