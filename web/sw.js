const V='dk-r153',SHELL=['/app','/manifest.webmanifest','/icon.svg','/brand/png/user-icon-192.png','/brand/png/user-icon-512.png','/a/fa-body.5aa85d80.webp','/a/fa-chest.9f8362f8.webp'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V&&x!==V+'-api'&&x.startsWith('dk-')).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
const SWR=/^\/api\/v1\/(config|plans|shop\/products|app\/(android|ios)|seasonal|videos|hospitals|places|labs\/quotes|anatomy\/review)/;
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==location.origin)return;
 if(u.pathname.startsWith('/api/')){if(!SWR.test(u.pathname))return;
  // reference data: answer from cache at once, refresh in the background (offline-first for the lists that do not change by the minute)
  e.respondWith(caches.open(V+'-api').then(async c=>{const h=await c.match(e.request);const f=fetch(e.request).then(r=>{if(r.ok)c.put(e.request,r.clone());return r}).catch(()=>h);return h||f}));return}
 if(u.pathname.startsWith('/a/')){e.respondWith(caches.open(V).then(async c=>{const h=await c.match(e.request);if(h)return h;const r=await fetch(e.request);if(r.ok)c.put(e.request,r.clone());return r}));return}
 e.respondWith(fetch(e.request).then(r=>{if(r.ok&&u.pathname.startsWith('/app'))caches.open(V).then(c=>c.put('/app',r.clone()));return r}).catch(()=>caches.match(e.request).then(h=>h||(u.pathname.startsWith('/app')?caches.match('/app'):h))))});

self.addEventListener('push',e=>{let d={};try{d=e.data?e.data.json():{}}catch(x){d={body:e.data&&e.data.text()}}
 const title=d.title||'Urban Health';const opt={body:d.body||'',icon:'/brand/png/user-icon-192.png',badge:'/brand/png/user-icon-192.png',tag:d.tag||'tht',renotify:!!d.tag,data:{url:d.url||'/app',act:d.act||null},vibrate:[80,40,80]};if(d.act&&d.act.meds&&d.act.meds.length)opt.actions=[{action:'take',title:'Taken'},{action:'snooze',title:'In 10 min'},{action:'skip',title:'Skip'}];
 e.waitUntil(self.registration.showNotification(title,opt))});
const post=(u,b)=>fetch(u,{method:'POST',credentials:'include',headers:{'x-tht':'1','content-type':'application/json'},body:JSON.stringify(b)});
async function doseAct(a,act){if(a==='snooze')return post(`/api/v2/people/${act.pid}/snooze`,{time:act.t,minutes:10,day:act.day});
 const at=Date.now();await Promise.all(act.meds.map(med=>post(`/api/v2/people/${act.pid}/records`,{kind:'dose',day:act.day,data:Object.assign({med,time:act.t,at},a==='skip'?{skipped:true}:{})})));
 const ws=await clients.matchAll({type:'window',includeUncontrolled:true});ws.forEach(w=>w.postMessage({uh:'dose'}))}
self.addEventListener('notificationclick',e=>{const act=e.notification.data&&e.notification.data.act;if(act&&['take','snooze','skip'].includes(e.action)){e.notification.close();e.waitUntil(doseAct(e.action,act).catch(()=>self.registration.showNotification('Could not save',{body:'Open Urban Health to tick it.',icon:'/brand/png/user-icon-192.png',data:{url:'/app/meds'}})));return}
 e.notification.close();const url=(e.notification.data&&e.notification.data.url)||'/app';
 e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(ws=>{for(const w of ws){if(url.startsWith('/app')&&w.url.includes('/app')&&'focus' in w)return w.focus()}return clients.openWindow(url)}))});
