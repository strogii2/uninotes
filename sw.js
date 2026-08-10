/* ============================================================
   UniNotes — service worker
   Ține aplicația în memoria telefonului, ca să pornească instant
   și să meargă fără internet după prima deschidere.
   ============================================================ */

const CACHE = 'uninotes-v3';

const SHELL = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      // addAll pică tot dacă un singur fișier lipsește; le punem una câte una
      .then(cache => Promise.all(SHELL.map(url => cache.add(url).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  event.respondWith(
    caches.match(req).then(hit => {
      if (hit) {
        // fonturile Google se împrospătează în fundal, fără să întârzie afișarea
        if (new URL(req.url).origin !== self.location.origin) {
          fetch(req).then(res => {
            if (res && res.ok) caches.open(CACHE).then(c => c.put(req, res.clone()));
          }).catch(() => {});
        }
        return hit;
      }
      return fetch(req).then(res => {
        if (res && res.ok && (res.type === 'basic' || res.type === 'cors')) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => {
        // offline și necache-uit: pentru navigări întoarcem aplicația
        if (req.mode === 'navigate') return caches.match('./index.html');
        return new Response('', { status: 504, statusText: 'Offline' });
      });
    })
  );
});

/* permite paginii să ceară activarea imediată a unei versiuni noi */
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});
