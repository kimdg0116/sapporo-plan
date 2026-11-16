/* 삿포로 플랜 - 오프라인 캐시. 버전은 version.json 과 같이 올린다 */
const VERSION = '26.11.16-1';
const CACHE = 'sp-v' + VERSION;
const CORE = ['./', './index.html', './places.js', './manifest.webmanifest', './apple-touch-icon.png', './icon-192.png', './icon-512.png'];
const fresh = u => new Request(u, { cache: 'reload' });

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE.map(fresh))
    .then(() => fetch(fresh('./places.json')).then(r => r.json()))
    .then(d => Promise.all(Object.values(d).filter(p => p.photo).map(p =>     // 사진도 미리 받아 둔다 (공항·버스에서 데이터 없어도 보이게)
      fetch('./' + p.photo).then(r => r.ok && c.put('./' + p.photo, r)).catch(() => {})))))
    .catch(() => {}).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.map(k => k === CACHE ? null : caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || e.request.url.includes('version.json')) return;
  e.respondWith(caches.match(e.request, { ignoreSearch: e.request.mode === 'navigate' }).then(hit => hit || fetch(e.request).then(res => {
    const u = e.request.url;
    if (res.ok && (u.startsWith(self.location.origin) || u.startsWith('https://cdn.jsdelivr.net/'))) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {}); }
    return res;
  }).catch(() => caches.match('./index.html'))));
});
