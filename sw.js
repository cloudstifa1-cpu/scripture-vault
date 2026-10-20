// Scripture Vault offline cache. Bump VERSION when the app page changes.
var VERSION = 'sv-5', DATA = 'sv-bible-1';
var CORE = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(CORE); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== VERSION && k !== DATA; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.pathname.indexOf('/data/') >= 0) {
    // Bible text never changes: use the saved copy, download once.
    e.respondWith(caches.open(DATA).then(function (c) {
      return c.match(e.request).then(function (m) { return m || fetch(e.request).then(function (r) { if (r.ok) c.put(e.request, r.clone()); return r; }); });
    }));
    return;
  }
  // App files: newest when online, saved copy when offline.
  e.respondWith(fetch(e.request).then(function (r) {
    var copy = r.clone(); caches.open(VERSION).then(function (c) { c.put(e.request, copy); }); return r;
  }).catch(function () {
    return caches.match(e.request, { ignoreSearch: true }).then(function (m) { return m || caches.match('index.html'); });
  }));
});
