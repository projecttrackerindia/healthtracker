const V='dk-r9a1',SHELL=['/app','/manifest.webmanifest','/icon.svg','/brand/png/user-icon-192.png','/brand/png/user-icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V&&x.startsWith('dk-')).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==location.origin||u.pathname.startsWith('/api/'))return;
 if(u.pathname.startsWith('/a/')){e.respondWith(caches.open(V).then(async c=>{const h=await c.match(e.request);if(h)return h;const r=await fetch(e.request);if(r.ok)c.put(e.request,r.clone());return r}));return}
 e.respondWith(fetch(e.request).then(r=>{if(r.ok&&u.pathname==='/app')caches.open(V).then(c=>c.put('/app',r.clone()));return r}).catch(()=>caches.match(e.request).then(h=>h||(u.pathname==='/app'?caches.match('/app'):h))))});

self.addEventListener('push',e=>{let d={};try{d=e.data?e.data.json():{}}catch(x){d={body:e.data&&e.data.text()}}
 const title=d.title||'TheHealthTracker';const opt={body:d.body||'',icon:'/brand/png/user-icon-192.png',badge:'/brand/png/user-icon-192.png',tag:d.tag||'tht',renotify:!!d.tag,data:{url:d.url||'/app'},vibrate:[80,40,80]};
 e.waitUntil(self.registration.showNotification(title,opt))});
self.addEventListener('notificationclick',e=>{e.notification.close();const url=(e.notification.data&&e.notification.data.url)||'/app';
 e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(ws=>{for(const w of ws){if(w.url.includes('/app')&&'focus' in w)return w.focus()}return clients.openWindow(url)}))});
