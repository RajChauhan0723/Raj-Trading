// RTW Service Worker - Cache-busting & Auto-Purge
self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map((k) => caches.delete(k)));
    }).then(() => {
      return self.clients.claim();
    }).then(() => {
      return self.registration.unregister();
    })
  );
});

// Network-only: never cache stale HTML or API payloads
self.addEventListener("fetch", (e) => {
  return;
});
