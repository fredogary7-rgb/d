/* ============================================================
   TransAfrik Service Worker — v1.0.2
   PWA Production : Cache intelligent, offline, network-first
   Protège contre les schémas chrome-extension:, edge-extension:, etc.
   ============================================================ */

const CACHE_VERSION = 'transafrik-v1.0.2';
const CACHE_STATIC = `${CACHE_VERSION}-static`;
const CACHE_DYNAMIC = `${CACHE_VERSION}-dynamic`;
const CACHE_PAGES = `${CACHE_VERSION}-pages`;
const CACHE_FONTS = `${CACHE_VERSION}-fonts`;

/* --- Ressources à pré-cacher (caches automatiquement à l'installation) --- */
const PRECACHE_URLS = [
  '/',
  '/offline',
  '/static/manifest.json',
  '/static/logo.png',
  '/static/img/icons/icon-72x72.png',
  '/static/img/icons/icon-96x96.png',
  '/static/img/icons/icon-128x128.png',
  '/static/img/icons/icon-144x144.png',
  '/static/img/icons/icon-152x152.png',
  '/static/img/icons/icon-192x192.png',
  '/static/img/icons/icon-384x384.png',
  '/static/img/icons/icon-512x512.png',
  '/static/img/icons/maskable-512x512.png',
  '/static/js/pwa.js',
  '/static/css/fees_calculator.css',
  '/static/css/scan.css',
  '/static/js/scan.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;500;600;700;800;900&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
];

/* --- URLs à NE JAMAIS mettre en cache (sécurité) --- */
const NO_CACHE_PATTERNS = [
  '/api/',
  '/login',
  '/register',
  '/transfer',
  '/deposit',
  '/payment',
  '/otp',
  '/verify-otp',
  '/kyc',
  '/admin',
  '/withdraw',
  '/profile/upload',
  '/profile/change-password',
  '/profile/change-pin',
  '/profile/delete',
  '/webhook',
  '/receive',
  '/support',
  '/send-money',
  '/request/',
  '/pay/',
  '/history',
  '/fees-calculator',
  '/scan',
  '/settings',
  '/profile',
  '/converter',
  '/beneficiaries',
  '/my-qrcode',
  '/qr-history',
  '/forgot-password',
  '/reset-password',
];

/* --- Vérifie si une URL ne doit pas être cachée --- */
function isNoCache(url) {
  return NO_CACHE_PATTERNS.some(pattern => url.includes(pattern));
}

/* --- Vérifie si le protocole est compatible avec Cache Storage --- */
function isCacheableProtocol(url) {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch (_) {
    return url.startsWith('http://') || url.startsWith('https://');
  }
}

/* ============================================================
   INSTALL — Pré-cache des ressources critiques
   ============================================================ */
self.addEventListener('install', (event) => {
  console.log('[SW] Installation — Pré-cache des ressources...');
  event.waitUntil(
    caches.open(CACHE_STATIC)
      .then(cache => {
        console.log('[SW] Pré-cache de', PRECACHE_URLS.length, 'ressources');
        return Promise.allSettled(
          PRECACHE_URLS.map(url => {
            if (!isCacheableProtocol(url)) {
              console.log('[SW] Pré-cache IGNORÉ (protocole non http(s)):', url.substring(0, 60));
              return Promise.resolve();
            }
            return cache.add(url).catch(err =>
              console.warn('[SW] Échec pré-cache:', url, err.message)
            );
          })
        );
      })
      .then(() => {
        console.log('[SW] Installation terminée — skipWaiting');
        return self.skipWaiting();
      })
  );
});

/* ============================================================
   ACTIVATE — Nettoyage des anciens caches + claim clients
   ============================================================ */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activation — Nettoyage des anciens caches...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name =>
            name.startsWith('transafrik-') &&
            name !== CACHE_STATIC &&
            name !== CACHE_DYNAMIC &&
            name !== CACHE_PAGES &&
            name !== CACHE_FONTS
          )
          .map(name => {
            console.log('[SW] Suppression ancien cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      console.log('[SW] Activation terminée — claim clients');
      return self.clients.claim();
    })
  );
});

/* ============================================================
   FETCH — Stratégies de cache intelligentes
   ============================================================ */

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  /* --- Ignorer les requêtes non-GET ou vers des domaines externes non-critiques --- */
  if (request.method !== 'GET') return;

  /* --- Ne jamais mettre en cache les API sensibles --- */
  if (isNoCache(url.pathname)) {
    console.log('[SW] No-cache:', url.pathname);
    return; // network-only (pas d'interception)
  }

  /* --- Stratégie 1: Cache-First pour les assets statiques versionnés --- */
  if (
    url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/) ||
    url.pathname.startsWith('/static/') ||
    url.hostname === 'fonts.googleapis.com' ||
    url.hostname === 'fonts.gstatic.com' ||
    url.hostname === 'cdnjs.cloudflare.com'
  ) {
    event.respondWith(cacheFirst(request, getCacheName(url)));
    return;
  }

  /* --- Stratégie 2: Stale-While-Revalidate pour les pages HTML --- */
  if (request.mode === 'navigate' || url.pathname.match(/\.html$/) || !url.pathname.match(/\.\w+$/)) {
    event.respondWith(staleWhileRevalidate(request, CACHE_PAGES));
    return;
  }

  /* --- Stratégie 3: Network-First pour tout le reste --- */
  event.respondWith(networkFirst(request, CACHE_DYNAMIC));
});

/* ============================================================
   STRATÉGIES DE CACHE
   ============================================================ */

/* Cache-First : sert le cache, met à jour en arrière-plan */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) {
    // Mise à jour en arrière-plan (stale-while-revalidate light)
    const reqUrl = request.url;
    fetch(request).then(response => {
      if (response && response.status === 200 && isCacheableProtocol(reqUrl)) {
        caches.open(cacheName).then(cache => cache.put(request, response));
      }
    }).catch(() => {});
    return cached;
  }
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      if (isCacheableProtocol(request.url)) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
      }
    }
    return response;
  } catch (err) {
    return offlineFallback(request);
  }
}

/* Network-First : essaie le réseau, fallback vers le cache */
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      if (isCacheableProtocol(request.url)) {
        const cache = await caches.open(cacheName);
        cache.put(request, response.clone());
      }
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return offlineFallback(request);
  }
}

/* Stale-While-Revalidate : sert le cache immédiatement, rafraîchit en arrière-plan */
async function staleWhileRevalidate(request, cacheName) {
  const cached = await caches.match(request);
  const reqUrl = request.url;
  const fetchPromise = fetch(request).then(response => {
    if (response && response.status === 200 && isCacheableProtocol(reqUrl)) {
      caches.open(cacheName).then(cache => cache.put(request, response.clone()));
    }
    return response;
  }).catch(() => cached);
  return cached || fetchPromise;
}

/* Offline fallback */
async function offlineFallback(request) {
  if (request.mode === 'navigate') {
    const offlinePage = await caches.match('/offline');
    if (offlinePage) return offlinePage;
    return new Response(
      '<html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#0B1120;color:#F1F5F9;text-align:center"><div><h1>📡</h1><h2>Hors connexion</h2><p>Veuillez vérifier votre connexion Internet.</p></div></body></html>',
      { status: 503, statusText: 'Service Unavailable', headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }
  return new Response('', { status: 504, statusText: 'Gateway Timeout' });
}

/* Retourne le nom du cache approprié selon l'URL */
function getCacheName(url) {
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
    return CACHE_FONTS;
  }
  if (url.pathname.startsWith('/static/')) {
    return CACHE_STATIC;
  }
  return CACHE_DYNAMIC;
}

/* ============================================================
   MESSAGE — Gestion des messages du client
   ============================================================ */
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  if (event.data === 'CLEAR_ALL_CACHES') {
    caches.keys().then(names =>
      Promise.all(names.map(name => caches.delete(name)))
    ).then(() => {
      console.log('[SW] Tous les caches ont été vidés');
      // Notify all clients
      self.clients.matchAll().then(clients =>
        clients.forEach(client =>
          client.postMessage({ type: 'CACHES_CLEARED' })
        )
      );
    });
  }
});

/* ============================================================
   PUSH NOTIFICATIONS
   ============================================================ */
self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    const options = {
      body: data.body || '',
      icon: data.icon || '/static/img/icons/icon-192x192.png',
      badge: '/static/img/icons/icon-72x72.png',
      vibrate: [200, 100, 200],
      data: {
        url: data.url || '/',
        ...data,
      },
      actions: data.actions || [],
      tag: data.tag || 'transafrik-notif',
      renotify: true,
      requireInteraction: data.requireInteraction || false,
    };
    event.waitUntil(
      self.registration.showNotification(data.title || 'TransAfrik', options)
    );
  } catch (e) {
    console.warn('[SW] Erreur notification push:', e);
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clients => {
      const existing = clients.find(c => c.url.includes(url) && 'focus' in c);
      if (existing) return existing.focus();
      return self.clients.openWindow(url);
    })
  );
});

console.log('[SW] Service Worker TransAfrik initialisé —', CACHE_VERSION);