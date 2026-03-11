const CACHE = "itcs-mobile-v2";
const ASSETS = ["/m/tasks", "/manifest.webmanifest"];
self.addEventListener("install", (event) => { event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).catch(() => {})); self.skipWaiting(); });
self.addEventListener("activate", (event) => { event.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", (event) => { if (event.request.method !== "GET") return; event.respondWith(fetch(event.request).catch(() => caches.match(event.request))); });
self.addEventListener('push', (event) => { let data = { title: 'ITCS', body: 'Новое уведомление', url: '/m/tasks' }; try { if (event.data) data = { ...data, ...event.data.json() }; } catch (e) {} event.waitUntil(self.registration.showNotification(data.title || 'ITCS', { body: data.body || 'Новое уведомление', tag: data.tag || 'itcs', data: { url: data.url || '/m/tasks' } })); });
self.addEventListener('notificationclick', (event) => { event.notification.close(); const url = event.notification?.data?.url || '/m/tasks'; event.waitUntil(clients.openWindow(url)); });
