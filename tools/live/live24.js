// ===================== live layer 24: medicine refills — days left, a "running low" card, reminders on the phone =====================
{
const P=SX.p,S=SX.S;
const SLOTS=['Morning','Afternoon','Evening','Night'],WD=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const meds=m=>(S.meds[m.id]=S.meds[m.id]||[]);
const perDay=x=>(x.when||[]).reduce((n,w)=>n+(SLOTS.includes(w)?1:WD.includes(w)?1/7:0),0);
const daysLeft=x=>{if(x.left==null)return null;const p=perDay(x);return p?x.left/p:null};
SX.medDaysLeft=daysLeft;
const low=m=>meds(m).map(x=>({x,d:daysLeft(x)})).filter(o=>o.d!=null&&o.d<=7).sort((a,b)=>a.d-b.d);
const when=d=>d<1?P('runs out today'):d<2?P('1 day left'):Math.floor(d)+' '+P('days left');
const runout=d=>{const t=new Date();t.setDate(t.getDate()+Math.floor(d));return t.toLocaleDateString('en-IN',{day:'numeric',month:'short'})};

function card(m){const L=low(m);if(!L.length)return '';
 return `<div class="card lv24-low"><div class="hd"><div><h3>${P('Running low')}</h3><small class="mute">${P('Counted from the doses ticked each day. Order a refill before it runs out.')}</small></div></div>
  ${L.map(({x,d})=>`<div class="lv24-row ${d<=3?'urgent':''}"><div class="lv24-ic">${SX.ico?SX.ico('pill'):'💊'}</div><div class="grow"><b>${E(x.n)}</b><small>${x.left?x.left+' '+P('left'):P('none left')} · ${when(d)}${d>=1?' · '+P('until')+' '+runout(d):''}</small></div><button class="btn ${d<=3?'p':'s'} sm" data-sx="refill:${E(x.id)}">${P('Reorder')}</button></div>`).join('')}</div>`}
SX.extend('rx',{before(){return card(SX.me())}});
SX.extend('dash',{before(){const m=SX.me();const L=low(m).filter(o=>o.d<=3);if(!L.length)return '';return `<div class="card lv24-low lv24-home"><div class="lv24-row urgent"><div class="lv24-ic">${SX.ico?SX.ico('pill'):'💊'}</div><div class="grow"><b>${P('Refill soon')}</b><small>${L.map(({x,d})=>E(x.n)+' · '+when(d)).join(' · ')}</small></div><button class="btn p sm" data-sx="refill:${E(L[0].x.id)}">${P('Reorder')}</button></div></div>`}});

// the push notification's link lands on the right medicine
if(/#refill=/.test(location.hash)){const id=/#refill=([^&]+)/.exec(location.hash)[1];history.replaceState(null,'',location.pathname);setTimeout(()=>{try{SX.act.refill([decodeURIComponent(id)])}catch(e){}},1200)}

// the phone app: a local notification at 09:00 for anything running out within 3 days (web and PWA get the server's push)
async function schedule(){try{const C=window.Capacitor;if(!C||!C.isNativePlatform||!C.isNativePlatform())return;const LN=C.Plugins&&C.Plugins.LocalNotifications;if(!LN)return;
 const items=[];(S.members||[]).forEach(m=>low(m).filter(o=>o.d<=3).forEach(o=>items.push({m,o})));
 const old=await LN.getPending().catch(()=>({notifications:[]}));const mine=(old.notifications||[]).filter(n=>n.id>=7100&&n.id<7200);if(mine.length)await LN.cancel({notifications:mine.map(n=>({id:n.id}))}).catch(()=>{});
 if(!items.length)return;const perm=await LN.checkPermissions();if(perm.display!=='granted')return;
 const at=new Date();at.setHours(9,0,0,0);if(at<=new Date())at.setDate(at.getDate()+1);
 await LN.schedule({notifications:items.slice(0,20).map(({m,o},i)=>({id:7100+i,title:P('Refill soon')+(m.rel==='You'?'':' · '+m.name.split(' ')[0]),body:o.x.n+' — '+when(o.d),schedule:{at},extra:{refill:o.x.id}}))})}catch(e){}}
setTimeout(schedule,3000);
const save0=SX.save;SX.save=function(){const r=save0.apply(this,arguments);clearTimeout(window.__lv24t);window.__lv24t=setTimeout(schedule,2000);return r};
SX.lv24={low,daysLeft,when};
}
