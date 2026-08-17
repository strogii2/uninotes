/* ============================================================
   UniNotes — service worker
   Ține aplicația în memoria telefonului, ca să pornească instant
   și să meargă fără internet după prima deschidere.
   ============================================================ */

const CACHE = 'uninotes-v21';

/**
 * Cele trei fișiere de mai jos trebuie să fie din aceeași versiune, altfel
 * aplicația se rupe: un app.js nou peste un index.html vechi caută butoane
 * care nu există. De aceea se pun cu addAll — sau intră toate, sau niciunul,
 * iar versiunea veche rămâne în funcțiune până data viitoare.
 */
const NUCLEU = [
  './',
  './index.html',
  './styles.css',
  './app.js'
];

/* astea pot lipsi fără să strice nimic */
const IN_PLUS = [
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache =>
      cache.addAll(NUCLEU)                        // pică tot dacă unul singur lipsește
        .then(() => Promise.all(IN_PLUS.map(u => cache.add(u).catch(() => null))))
        .then(() => self.skipWaiting())
    )
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

  // Căutăm doar în cache-ul versiunii curente: un caches.match() nelegat ar putea
  // scoate un fișier dintr-o versiune veche și l-ar amesteca cu unul nou.
  event.respondWith(
    caches.open(CACHE).then(c => c.match(req)).then(hit => {
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
        if (req.mode === 'navigate') return caches.open(CACHE).then(c => c.match('./index.html'));
        return new Response('', { status: 504, statusText: 'Offline' });
      });
    })
  );
});

/* permite paginii să ceară activarea imediată a unei versiuni noi */
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});
