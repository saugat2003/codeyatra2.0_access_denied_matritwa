/**
 * Matritwa — Service Worker (SOS offline-first)
 * ──────────────────────────────────────────────
 * Responsibilities:
 *   1. Cache critical app shell & SOS assets for offline access.
 *   2. Intercept failed SOS API requests and queue them in IndexedDB
 *      (via Background Sync API when available, fallback to
 *      client-side retry in sos-offline.js).
 *   3. Serve cached pages when the network is unavailable.
 */

const CACHE_NAME    = "matritwa-sos-v1";
const API_SOS_PATH  = "/api/sos/";

/**
 * Assets to pre-cache during installation.
 * We cache the app shell so the SOS trigger page works offline.
 */
const PRE_CACHE = [
  "/static/js/sos-offline.js",
  "/static/css/style.css",
  "/static/manifest.json",
];

// ── Install ─────────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRE_CACHE).catch((err) => {
        // Non-fatal: some assets may 404 during dev
        console.warn("[SW] Pre-cache partial failure:", err);
      });
    }),
  );
  // Activate immediately without waiting for old SW to retire
  self.skipWaiting();
});

// ── Activate ────────────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((n) => n !== CACHE_NAME)
          .map((n) => caches.delete(n)),
      ),
    ),
  );
  // Take control of all open pages immediately
  self.clients.claim();
});

// ── Fetch strategy ──────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1) SOS API calls — network-only; offline handled by sos-offline.js
  if (url.pathname.startsWith(API_SOS_PATH)) {
    event.respondWith(
      fetch(request).catch(() =>
        new Response(
          JSON.stringify({ ok: false, error: "offline" }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );
    return;
  }

  // 2) Static assets — cache-first
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((resp) => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, clone));
          }
          return resp;
        }).catch(() => new Response("", { status: 504 }));
      }),
    );
    return;
  }

  // 3) Navigation requests — network-first, fallback to cache
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          // Cache successful HTML pages so they work offline
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, clone));
          }
          return resp;
        })
        .catch(() => caches.match(request)),
    );
    return;
  }

  // 4) Everything else — network with cache fallback
  event.respondWith(
    fetch(request).catch(() => caches.match(request)),
  );
});

// ── Background Sync (if supported) ──────────────────────────────

self.addEventListener("sync", (event) => {
  if (event.tag === "sos-sync") {
    event.waitUntil(
      // Notify all controlled pages to run SOS.syncQueue()
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: "SOS_SYNC_REQUEST" });
        });
      }),
    );
  }
});

// ── Push notification placeholder ───────────────────────────────

self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || "SOS Emergency Alert";
  const options = {
    body: data.body || "A mother needs immediate assistance.",
    icon: "/static/images/sos-icon.png",
    badge: "/static/images/sos-badge.png",
    vibrate: [200, 100, 200, 100, 200],
    tag: "sos-emergency",
    requireInteraction: true,
    data: data,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      // Focus existing window or open dashboard
      for (const client of clients) {
        if (client.url.includes("/dashboard") && "focus" in client) {
          return client.focus();
        }
      }
      return self.clients.openWindow("/dashboard/");
    }),
  );
});
