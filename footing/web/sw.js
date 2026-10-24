// Offline support: the app shell is cached on install; API answers are network-first with the
// last good answer kept as a fallback, so a receipt or plan opened once still shows with no signal.
const SHELL = "footing-shell-v6";
const DATA = "footing-data-v6";
const SHELL_FILES = ["./", "index.html", "styles.css", "app.js", "manifest.webmanifest", "icon.svg",
  "globe.css", "globe.js", "fit.js", "i18n.js", "vendor/maplibre-gl.js", "vendor/maplibre-gl.css",
  "vendor/topojson-client.min.js", "data/states-10m.json", "data/countries-110m.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((k) => ![SHELL, DATA].includes(k)).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/api/")) {
    e.respondWith(fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(DATA).then((c) => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request).then((hit) => hit || new Response(
      JSON.stringify({ offline: true, detail: "No signal and nothing saved for this page yet." }),
      { status: 503, headers: { "Content-Type": "application/json" } }))));
    return;
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
