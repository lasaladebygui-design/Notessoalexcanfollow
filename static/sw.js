const CACHE_NAME = "notas-cache-v1";
const OFFLINE_URL = "/estas-sin-conexion/";
const PRECACHE = [OFFLINE_URL, "/static/icons/icon-192.png"];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
        ).then(() => self.clients.claim())
    );
});

// Network-first para páginas (para no servir contenido viejo/privado sin
// darse cuenta); si no hay red, cae a una pantalla de "sin conexión" en
// vez de dejar el navegador con su error genérico.
self.addEventListener("fetch", (event) => {
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(OFFLINE_URL))
        );
        return;
    }

    if (event.request.destination === "image") {
        event.respondWith(
            caches.match(event.request).then((cached) => cached || fetch(event.request))
        );
    }
});
