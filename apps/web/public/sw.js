// Vantage service worker: app-shell + last-known-data offline support, plus push notifications.
// Bump VERSION to invalidate.
const VERSION = "v2";
const SHELL_CACHE = `vantage-shell-${VERSION}`;
const RUNTIME_CACHE = `vantage-runtime-${VERSION}`;
const PRECACHE = ["/offline", "/icons/icon-192.png", "/icons/icon-512.png"];
// Only these API reads are kept for offline use; everything else always hits the network.
const CACHEABLE_API = ["/api/feed/", "/api/profile/", "/api/taxonomy/"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) {
        if (key !== SHELL_CACHE && key !== RUNTIME_CACHE) await caches.delete(key);
      }
      await self.clients.claim();
    })(),
  );
});

// The app asks us to drop cached personal data when someone resets the device.
self.addEventListener("message", (event) => {
  if (event.data === "clear-runtime") event.waitUntil(caches.delete(RUNTIME_CACHE));
});

// The server's payload is { title, body, url }; url is where a tap should land.
self.addEventListener("push", (event) => {
  let data = { title: "Vantage", body: "", url: "/feed" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch {}
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: data.url },
    }),
  );
});

// Focus an already-open tab on that page if there is one, otherwise open a new one.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/feed";
  event.waitUntil(
    (async () => {
      const clientsList = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      const target = new URL(url, self.location.origin).href;
      for (const client of clientsList) {
        if (client.url === target && "focus" in client) return client.focus();
      }
      return self.clients.openWindow(url);
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(cacheFirst(request));
  } else if (url.pathname.startsWith("/api/")) {
    if (CACHEABLE_API.some((prefix) => url.pathname.startsWith(prefix))) {
      event.respondWith(networkFirst(request));
    }
  } else if (request.mode === "navigate") {
    event.respondWith(navigate(request));
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) (await caches.open(SHELL_CACHE)).put(request, response.clone());
  return response;
}

async function networkFirst(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function navigate(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    return (await cache.match(request)) || (await caches.match("/offline")) || Response.error();
  }
}
