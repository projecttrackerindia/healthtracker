// ===================== live layer 29: fixes from the phone — zoom lock, tab bar, assistant + keyboard, the body's head, Heart Lab under Care,
// one location with a Google map everywhere, SOS that acts the moment it is pressed, card vault arrows, every string translated =====================
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;
const ls=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){return null}};
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1','x-dokko-key':(S.key||'')},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status});return j});
const native=()=>!!(window.Capacitor&&Capacitor.isNativePlatform&&Capacitor.isNativePlatform());
const ios=()=>/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
S.net=S.net||{};

// ---------------------------------------------------------------- A. a mobile app does not pinch or double-tap zoom (the 3D stages keep their own pinch)
document.addEventListener('gesturestart',e=>{if(!e.target.closest||!e.target.closest('#stage,#hstage,#pstage,.lv29-pm'))e.preventDefault()},{passive:false});
document.addEventListener('touchmove',e=>{if(e.touches.length>1&&!(e.target.closest&&e.target.closest('#stage,#hstage,#pstage,.lv29-pm')))e.preventDefault()},{passive:false});
{let last=0;document.addEventListener('touchend',e=>{const t=Date.now();if(t-last<300&&!(e.target.closest&&e.target.closest('input,textarea,select,button,a,[data-sx],#stage,#hstage,#pstage,.lv29-pm')))e.preventDefault();last=t},{passive:false})}

// ---------------------------------------------------------------- B. the assistant's mark: a living orb with a pulse line
function mark(id){id=id||'m';return `<svg class="lv29-mark" viewBox="0 0 120 120" aria-hidden="true"><defs>
 <radialGradient id="lv29g${id}" cx="36%" cy="28%" r="82%"><stop offset="0" stop-color="#e8efff"/><stop offset=".22" stop-color="#8aa8ff"/><stop offset=".55" stop-color="#2f5bff"/><stop offset=".85" stop-color="#1733c2"/><stop offset="1" stop-color="#0a1570"/></radialGradient>
 <radialGradient id="lv29t${id}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#5ef2d8" stop-opacity=".95"/><stop offset="1" stop-color="#5ef2d8" stop-opacity="0"/></radialGradient>
 <radialGradient id="lv29p${id}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ff7ad9" stop-opacity=".9"/><stop offset="1" stop-color="#ff7ad9" stop-opacity="0"/></radialGradient>
 <radialGradient id="lv29h${id}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
 <clipPath id="lv29c${id}"><circle cx="60" cy="60" r="54"/></clipPath></defs>
 <circle cx="60" cy="60" r="54" fill="url(#lv29g${id})"/>
 <g clip-path="url(#lv29c${id})">
  <ellipse cx="86" cy="84" rx="44" ry="26" fill="url(#lv29t${id})" transform="rotate(-28 86 84)"/>
  <ellipse cx="30" cy="92" rx="38" ry="22" fill="url(#lv29p${id})" transform="rotate(16 30 92)"/>
  <ellipse cx="44" cy="30" rx="26" ry="13" fill="url(#lv29h${id})" transform="rotate(-28 44 30)"/>
  <path class="lv29-line" d="M20 64h14l6-13 9 29 8-22 5 8h30" fill="none" stroke-width="4.2" stroke-linecap="round" stroke-linejoin="round"/>
  <path class="lv29-pulse" d="M20 64h14l6-13 9 29 8-22 5 8h30" fill="none" stroke-width="5.4" stroke-linecap="round" stroke-linejoin="round"/>
 </g>
 <circle class="lv29-ring" cx="60" cy="60" r="57.5" fill="none" stroke-width="1.6" stroke-dasharray="3 12" stroke-linecap="round"/>
 <circle class="lv29-edge" cx="60" cy="60" r="54" fill="none" stroke-width=".9"/></svg>`}
SX.assistMark=mark;
function paintOrb(){document.querySelectorAll('.lv22-orb:not([data-lv29])').forEach(o=>{o.dataset.lv29='1';o.innerHTML=mark('o')});
 document.querySelectorAll('.lv5-msg.ai:not([data-lv29]),.lv5-a:not([data-lv29])').forEach(m=>{m.dataset.lv29='1'})}
// the keyboard: the hero folds away (CSS) and the ask bar rides just above the keys
const vv=window.visualViewport;
function askBar(){const f=document.querySelector('body[data-page=assist] .lv5-ask');if(!f)return;const kb=document.body.classList.contains('lv17-kb')&&phone();
 if(kb&&vv){f.classList.add('lv29-float');f.style.bottom=Math.max(0,Math.round(innerHeight-(vv.height+vv.offsetTop)))+8+'px';const log=document.querySelector('.lv5-log,.lv5-thread');if(log)log.scrollTop=log.scrollHeight}
 else{f.classList.remove('lv29-float');f.style.bottom=''}}
if(vv){vv.addEventListener('resize',()=>setTimeout(askBar,30));vv.addEventListener('scroll',()=>askBar())}
document.addEventListener('focusin',()=>setTimeout(askBar,120));document.addEventListener('focusout',()=>setTimeout(askBar,150));

// ---------------------------------------------------------------- C. Heart Lab belongs under Care, and only when the heart is the subject
const HEART=/heart|cardi|hypertens|high bp|\bbp\b|cholesterol|arrhythm|atrial|angina|stent|bypass|valve|murmur|palpitat|\becg\b|lipid|statin|infarct|cabg|pacemaker|amlodipine|telmisartan|losartan|olmesartan|metoprolol|atenolol|bisoprolol|carvedilol|propranolol|atorva|rosuva|clopidogrel|ecosprin|aspirin 75|ramipril|enalapril|lisinopril|digoxin|warfarin|apixaban|rivaroxaban|dabigatran|nitro|sorbitrate|isosorbide|diltiazem|verapamil|amiodarone|furosemide|spironolactone|torsemide|sacubitril|ticagrelor|prasugrel/i;
SX.heartOn=m=>{try{return heartOn(m)}catch(e){return false}};
function heartOn(m){m=m||SX.me();if(!m)return false;if(S.heartLab===true)return true;if(S.heartLab===false)return false;
 const mid=(S.mid&&SX.midOf&&SX.midOf(m.id))||{};const txt=[...(mid.conditions||[]),mid.doctor||'',mid.notes||'',mid.history||'',...(S.meds&&S.meds[m.id]||[]).map(x=>[x.n,x.gen,x.for,x.why].filter(Boolean).join(' '))].join(' | ');
 if(HEART.test(txt))return true;
 const v=((S.vitals&&S.vitals[m.id])||[]).filter(x=>x.sys).slice(-12);if(v.filter(x=>x.sys>=140||x.dia>=90).length>=2)return true;
 try{if((S.meds[m.id]||[]).some(x=>(SX.medClasses(x)||[]).some(c=>/bp|cardiac|statin|anticoag|antiplatelet|betablock|ace|arb|diuretic/i.test(c))))return true}catch(e){}
 return false}
SX.heartWhy=m=>{m=m||SX.me();if(S.heartLab===true)return P('Switched on in Settings');const mid=(S.mid&&SX.midOf&&SX.midOf(m.id))||{};const c=(mid.conditions||[]).find(x=>HEART.test(x));if(c)return P('Condition')+': '+c;if(HEART.test(mid.doctor||''))return P('Doctor')+': '+mid.doctor;const md=(S.meds[m.id]||[]).find(x=>HEART.test([x.n,x.gen,x.for].join(' ')));if(md)return P('Medicine')+': '+md.n;return P('Blood pressure readings')};
{const home=SX.G.find(g=>g.k==='home');if(home)home.tabs=home.tabs.filter(t=>t!=='heart');
 const place=()=>{const care=SX.G.find(g=>g.k==='care');if(!care)return;care.tabs=care.tabs.filter(t=>t!=='heart');if(SX.heartOn())care.tabs.push('heart')};
 const pn0=SX.pregNav;SX.pregNav=function(){try{pn0&&pn0.apply(this,arguments)}catch(e){}place()};place();
 const sv0=SX.save;SX.save=function(){const r=sv0.apply(this,arguments);try{place()}catch(e){}return r};
 SX.addStrings&&SX.addStrings({'tab.heart':SX.D('Heart Lab','हार्ट लैब','హార్ట్ ల్యాబ్')});}
SX.chg.heartlab=(a,el)=>{S.heartLab=el.value==='auto'?null:el.value==='on';SX.save();SX.pregNav();try{render();SX.paintNav()}catch(e){}};
SX.extend('set',{after(){const on=SX.heartOn();return `<div class="card"><div class="hd"><div><h3>❤️ ${P('Heart Lab')}</h3><small class="mute">${P('A living 3D heart for people with a heart condition, BP medicines or a cardiologist. It appears under Care.')}</small></div></div>
 <div class="row" style="gap:10px;align-items:center;flex-wrap:wrap"><select data-sxc="heartlab" class="lv21-sel"><option value="auto" ${S.heartLab==null?'selected':''}>${P('Automatic')}</option><option value="on" ${S.heartLab===true?'selected':''}>${P('Always show')}</option><option value="off" ${S.heartLab===false?'selected':''}>${P('Never show')}</option></select><small class="mute">${on?'✓ '+P('Shown')+' · '+SX.heartWhy():P('Hidden for')+' '+E(SX.me().name.split(' ')[0])}</small></div></div>`}});
// phones: fewer controls on the heart stage until asked for
function heartChrome(){if(!phone())return;const st=document.getElementById('hstage');if(!st||st.hidden||document.getElementById('lv29hx'))return;const b=document.createElement('button');b.id='lv29hx';b.type='button';b.textContent=P('Controls');b.onclick=()=>{st.classList.toggle('lv29-hx');b.classList.toggle('on',st.classList.contains('lv29-hx'))};st.appendChild(b)}

// ---------------------------------------------------------------- D. one location for the whole app, picked on a map
const STATES={'Andhra Pradesh':'AP','Telangana':'TS','Karnataka':'KA','Tamil Nadu':'TN','Kerala':'KL','Maharashtra':'MH','Gujarat':'GJ','Delhi':'DL','Uttar Pradesh':'UP','West Bengal':'WB','Rajasthan':'RJ','Madhya Pradesh':'MP','Punjab':'PB','Haryana':'HR','Bihar':'BR','Odisha':'OD','Assam':'AS','Jharkhand':'JH','Chhattisgarh':'CG','Uttarakhand':'UK','Himachal Pradesh':'HP','Goa':'GA','Jammu and Kashmir':'JK','Puducherry':'PY','Chandigarh':'CH'};
const INDIA={lat:20.5937,lng:78.9629};
SX.loc={
 get:()=>S.net.geo?{lat:S.net.geo.lat,lng:S.net.geo.lng}:null,
 where:()=>S.net.where||null,
 text:()=>{const w=S.net.where;if(!w)return '';return w.label||[w.place,w.city,w.state].filter(Boolean).join(', ')},
 short:()=>{const w=S.net.where;if(!w)return '';return [w.place,w.city].filter((x,i,a)=>x&&a.indexOf(x)===i).join(', ')},
 // the single write path: everything that shows a position or "near you" reads S.net.geo / S.net.where
 set:(lat,lng,where,manual)=>{S.net.geo={lat:+(+lat).toFixed(5),lng:+(+lng).toFixed(5),t:Date.now()};S.net.geoManual=!!manual;
  S.net.where={ok:true,...(where||{}),lat:S.net.geo.lat,lng:S.net.geo.lng,t:Date.now()};if(where&&where.state)S.state=where.state;SX.save(true);
  try{const a=document.getElementById('lv6Loc');if(a)a.querySelector('span').textContent=SX.loc.short()||P('Located')}catch(e){}
  document.dispatchEvent(new CustomEvent('tht:location',{detail:S.net.geo}))},
 gps:(ms)=>new Promise(res=>{if(!navigator.geolocation)return res(null);let done=false;const to=setTimeout(()=>{if(!done){done=true;res(null)}},ms||9000);
  navigator.geolocation.getCurrentPosition(p=>{if(done)return;done=true;clearTimeout(to);res({lat:+p.coords.latitude.toFixed(5),lng:+p.coords.longitude.toFixed(5),acc:Math.round(p.coords.accuracy||0)})},()=>{if(!done){done=true;clearTimeout(to);res(null)}},{enableHighAccuracy:true,timeout:ms||9000,maximumAge:30000})}),
 resolve:async(lat,lng)=>{try{const r=await J(`/geo/where?lat=${lat}&lng=${lng}`);if(r&&r.ok)return r}catch(e){}return null}};
const gready=()=>!!(window.google&&google.maps&&google.maps.Map);
const gwait=ms=>new Promise(res=>{if(!(SX.gmapsOn&&SX.gmapsOn()))return res(false);const t0=Date.now();(function w(){if(gready())return res(true);if(Date.now()-t0>ms)return res(false);setTimeout(w,120)})()});
const PIN=`<svg viewBox="0 0 34 46" width="34" height="46"><path d="M17 1C8.2 1 1 8.1 1 16.8c0 11.3 13.2 25.9 15 27.9a1.3 1.3 0 0 0 2 0c1.8-2 15-16.6 15-27.9C33 8.1 25.8 1 17 1z" fill="#2f5bff" stroke="#fff" stroke-width="2"/><circle cx="17" cy="17" r="6" fill="#fff"/></svg>`;
const GPSI=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>`;
// from a Google Geocoder result to the fields the app keeps
function gaddr(res){const c={};(res.address_components||[]).forEach(x=>(x.types||[]).forEach(t=>{if(!c[t])c[t]=x.long_name}));const place=c.sublocality_level_1||c.sublocality||c.neighborhood||c.sublocality_level_2||c.locality||'',city=c.locality||c.administrative_area_level_3||c.administrative_area_level_2||'',state=c.administrative_area_level_1||'';
 return {ok:true,place,city,district:c.administrative_area_level_2||'',state,stateCode:STATES[state]||'',pin:c.postal_code||'',label:(res.formatted_address||'').slice(0,160)}}
const osmPosToTile=(lat,lng,z)=>{const n=Math.pow(2,z);return {x:(lng+180)/360*n,y:(1-Math.log(Math.tan(lat*Math.PI/180)+1/Math.cos(lat*Math.PI/180))/Math.PI)/2*n}};
const osmTileToPos=(x,y,z)=>{const n=Math.pow(2,z);const lng=x/n*360-180,lat=Math.atan(Math.sinh(Math.PI*(1-2*y/n)))*180/Math.PI;return {lat:+lat.toFixed(6),lng:+lng.toFixed(6)}};
function osmTiles(el,c,z){const W=el.clientWidth||360,H=el.clientHeight||300,n=Math.pow(2,z),t=osmPosToTile(c.lat,c.lng,z),x0=t.x-W/512,y0=t.y-H/512;let h='';
 for(let x=Math.floor(x0);x<=Math.floor(x0+W/256);x++)for(let y=Math.floor(y0);y<=Math.floor(y0+H/256);y++){if(y<0||y>=n)continue;h+=`<img src="https://tile.openstreetmap.org/${z}/${((x%n)+n)%n}/${y}.png" style="left:${Math.round((x-x0)*256)}px;top:${Math.round((y-y0)*256)}px" alt="" draggable="false">`}
 return h}
// the picker: a map that moves under a fixed pin (Rapido / Uber style), search, "locate me", then the door and landmark
SX.mapPick=(opt={})=>new Promise(async resolve=>{
 let cur=opt.center||SX.loc.get()||null,z=cur?16:5,info=null,map=null,drag=null,tdeb=null,sdeb=null,done=false,label=opt.label||'home';if(!cur){cur={...INDIA}}
 const fields=opt.address?`<div class="lv29-lbl">${[['home','🏠',P('Home')],['work','💼',P('Work')],['other','📍',P('Other')]].map(([k,i,t])=>`<button type="button" data-l="${k}" class="${k===label?'on':''}">${i} ${t}</button>`).join('')}</div>
  <div class="lv29-fields"><input class="full" id="lv29door" placeholder="${E(P('House / flat, building'))}" value="${E(opt.door||'')}" maxlength="120"><input id="lv29lm" placeholder="${E(P('Landmark'))}" value="${E(opt.landmark||'')}" maxlength="80"><input id="lv29pin" placeholder="PIN" inputmode="numeric" maxlength="6" value="${E(opt.pin||'')}"></div>`:'';
 SX.modal(`<div class="lv29-pick"><div class="lv29-pm" id="lv29pm"><div class="lv29-tiles" id="lv29tiles"></div><div class="lv29-pin">${PIN}</div><span class="lv29-attr" id="lv29attr"></span><button type="button" class="lv29-gps" id="lv29gps" aria-label="${E(P('Use my current location'))}">${GPSI}</button></div>
  <div class="lv29-ptop"><button type="button" class="lv29-back" id="lv29back" aria-label="${E(P('Back'))}">‹</button><div class="lv29-ps"><input id="lv29q" placeholder="${E(P('Search area, landmark or PIN'))}" autocomplete="off"><div class="lv29-sug" id="lv29sug"></div></div></div>
  <div class="lv29-sheet"><div class="lv29-addr"><i>📍</i><div class="grow"><b id="lv29addr">${P('Move the map to your door')}</b><small id="lv29sub">${P('The pin stays in the middle; drag the map underneath it.')}</small></div></div>${fields}
   <button class="btn p" id="lv29ok" type="button">${E(opt.cta||P('Confirm location'))}</button><p class="lv29-note">${P('Used for nearby labs, hospitals, deliveries and SOS. Not shared with other families.')}</p></div></div>`,{cls:'lv29-pm-m',label:opt.title||P('Your location'),sticky:true,onclose:()=>{if(!done){done=true;resolve(null)}}});
 const pm=document.getElementById('lv29pm'),tiles=document.getElementById('lv29tiles'),addr=document.getElementById('lv29addr'),sub=document.getElementById('lv29sub'),sug=document.getElementById('lv29sug'),q=document.getElementById('lv29q'),gps=document.getElementById('lv29gps');
 const show=()=>{if(!info){addr.textContent=P('Finding the address…');sub.textContent=cur.lat.toFixed(5)+', '+cur.lng.toFixed(5);return}addr.textContent=info.label||[info.place,info.city].filter(Boolean).join(', ')||P('Pinned');sub.textContent=[info.place,info.city,info.state,info.pin].filter((x,i,a)=>x&&a.indexOf(x)===i).join(' · ');const pin=document.getElementById('lv29pin');if(pin&&info.pin&&!pin.value)pin.value=info.pin};
 const g=await gwait(5000);
 const reverse=async()=>{const at={...cur};info=null;show();let r=null;
  if(g){try{const res=await new Promise((ok,no)=>new google.maps.Geocoder().geocode({location:at,region:'IN'},(x,st)=>st==='OK'&&x&&x.length?ok(x):no(st)));r=gaddr(res[0]);for(const x of res.slice(1,4)){const o=gaddr(x);['place','city','district','state','pin'].forEach(k=>{r[k]=r[k]||o[k]})}}catch(e){}}
  if(!r)r=await SX.loc.resolve(at.lat,at.lng);if(at.lat!==cur.lat||at.lng!==cur.lng)return;info=r||{ok:false,label:''};show()};
 const moved=()=>{clearTimeout(tdeb);tdeb=setTimeout(reverse,g?250:700)};
 const goTo=(lat,lng,zoom)=>{cur={lat:+(+lat).toFixed(6),lng:+(+lng).toFixed(6)};if(zoom)z=zoom;if(map){map.setZoom(z);map.panTo(cur)}else{tiles.innerHTML=osmTiles(pm,cur,z);tiles.style.transform='';moved()}};
 if(g){const gd=document.createElement('div');gd.className='lv29-g';pm.insertBefore(gd,tiles);tiles.remove();document.getElementById('lv29attr').remove();
  map=new google.maps.Map(gd,{center:cur,zoom:z,disableDefaultUI:true,gestureHandling:'greedy',clickableIcons:false,keyboardShortcuts:false});
  map.addListener('dragstart',()=>pm.classList.add('drag'));map.addListener('idle',()=>{pm.classList.remove('drag');const c=map.getCenter();if(!c)return;cur={lat:+c.lat().toFixed(6),lng:+c.lng().toFixed(6)};moved()})}
 else{document.getElementById('lv29attr').textContent='© OpenStreetMap';tiles.innerHTML=osmTiles(pm,cur,z);
  pm.addEventListener('pointerdown',e=>{if(e.target.closest('button,input'))return;drag={x:e.clientX,y:e.clientY,dx:0,dy:0};pm.setPointerCapture(e.pointerId);pm.classList.add('drag')});
  pm.addEventListener('pointermove',e=>{if(!drag)return;drag.dx=e.clientX-drag.x;drag.dy=e.clientY-drag.y;tiles.style.transform=`translate(${drag.dx}px,${drag.dy}px)`});
  const end=()=>{if(!drag)return;const t=osmPosToTile(cur.lat,cur.lng,z);const p=osmTileToPos(t.x-drag.dx/256,t.y-drag.dy/256,z);drag=null;pm.classList.remove('drag');goTo(p.lat,p.lng)};
  pm.addEventListener('pointerup',end);pm.addEventListener('pointercancel',end);
  pm.addEventListener('wheel',e=>{e.preventDefault();z=Math.max(4,Math.min(18,z+(e.deltaY<0?1:-1)));goTo(cur.lat,cur.lng)},{passive:false});
  moved()}
 if(!opt.center&&(!S.net.geoManual||!SX.loc.get())){gps.classList.add('busy');SX.loc.gps(8000).then(f=>{gps.classList.remove('busy');if(f&&!done)goTo(f.lat,f.lng,16)})}   // a fresh fix unless the family chose a point by hand
 gps.onclick=async()=>{gps.classList.add('busy');const f=await SX.loc.gps(10000);gps.classList.remove('busy');if(f)goTo(f.lat,f.lng,Math.max(z,16));else toast(P('Location is blocked for this site. Allow it in the browser’s site settings, or search your area.'))};
 q.oninput=()=>{clearTimeout(sdeb);const v=q.value.trim();if(v.length<2){sug.innerHTML='';return}sdeb=setTimeout(async()=>{try{const r=await J('/geo/search?q='+encodeURIComponent(v));if(q.value.trim()!==v)return;sug.innerHTML=(r.results||[]).map((x,i)=>`<button type="button" data-i="${i}"><i>📍</i><div><b>${E(x.place||x.city||x.label)}</b><small>${E(x.label)}</small></div></button>`).join('')||`<button type="button" disabled><small>${P('Nothing found. Try the city name or PIN.')}</small></button>`;
   sug.querySelectorAll('[data-i]').forEach(b=>b.onclick=()=>{const x=r.results[+b.dataset.i];sug.innerHTML='';q.value=x.place||x.city||'';q.blur();info=null;goTo(x.lat,x.lng,/^\d{6}$/.test(v)?14:16)})}catch(e){sug.innerHTML=''}},350)};
 q.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();const b=sug.querySelector('[data-i]');if(b)b.click()}};
 document.querySelectorAll('.lv29-lbl button').forEach(b=>b.onclick=()=>{label=b.dataset.l;document.querySelectorAll('.lv29-lbl button').forEach(x=>x.classList.toggle('on',x===b))});
 document.getElementById('lv29back').onclick=()=>{done=true;SX.closeModal();resolve(null)};
 document.getElementById('lv29ok').onclick=async()=>{const ok=document.getElementById('lv29ok');ok.disabled=true;ok.textContent=P('Saving…');let w=info&&info.ok?info:null;if(!w){w=await SX.loc.resolve(cur.lat,cur.lng)}w=w||{ok:true,place:'',city:'',state:'',pin:'',label:cur.lat.toFixed(5)+', '+cur.lng.toFixed(5)};
  const pinEl=document.getElementById('lv29pin');if(pinEl&&/^\d{6}$/.test(pinEl.value.trim()))w.pin=pinEl.value.trim();
  const out={lat:cur.lat,lng:cur.lng,where:w,label,door:(document.getElementById('lv29door')||{}).value||'',landmark:(document.getElementById('lv29lm')||{}).value||''};done=true;SX.closeModal();resolve(out)};
});
// "Set location" everywhere opens the picker and writes the one location
SX.act.locset=async()=>{const r=await SX.mapPick({title:P('Your location')});if(!r)return;SX.loc.set(r.lat,r.lng,r.where,true);toast(P('Location set')+' · '+(SX.loc.short()||''));try{render()}catch(e){}};
// a manual choice wins over an automatic refresh; a GPS fix that moved us far away replaces a stale automatic one
const geo0=SX.geo;SX.geo=async ask=>{if(S.net.geoManual&&S.net.geo)return {lat:S.net.geo.lat,lng:S.net.geo.lng};const g=await geo0(ask);return g};
// Today: the location card with a live map, right under the greeting
function miniMap(c){if(!c)return '';if(SX.gmapsOn&&SX.gmapsOn()&&SX.gmapHTML)return SX.gmapHTML(c,[],{h:64,zoom:15,static:true});const z=15,t=osmPosToTile(c.lat,c.lng,z),x=Math.floor(t.x),y=Math.floor(t.y),ox=Math.round((t.x-x)*256),oy=Math.round((t.y-y)*256);
 return `<img src="https://tile.openstreetmap.org/${z}/${x}/${y}.png" style="left:${42-ox}px;top:${32-oy}px" alt="">`}
SX.locCard=(opt={})=>{const c=SX.loc.get(),w=S.net.where;return `<div class="lv29-loc" data-lv29="loc"><div class="lv29-mini">${miniMap(c)}${c?'<i class="lv29-dot"></i>':''}</div><div class="grow"><b>${c?E(SX.loc.short()||P('Located')):P('Where are you?')}</b><small>${c?E(w&&w.label?w.label:(w?[w.district,w.state].filter(Boolean).join(', '):P('Position set')))+(S.net.geoManual?' · '+P('chosen on the map'):''):P('Nearby labs, hospitals, deliveries and SOS use this.')}</small></div><button class="btn ${c?'s':'p'} sm" data-sx="locset">${c?P('Change'):P('Set')}</button></div>`};
SX.extend('dash',{before(){return phone()?SX.locCard():''}});
SX.extend('book',{before(){return SX.locCard()}});
// the address book: pick on the map first (Uber style), then the door — the typed form stays for edits
const ae0=SX.act.addredit;
SX.act.addredit=async a=>{const id=a&&a[0];const me=SX.me();
 if(id==='new'){const r=await SX.mapPick({address:true,title:P('Add address'),cta:P('Save address')});if(!r)return;const w=r.where||{};
  const o={id:'ad'+Math.random().toString(36).slice(2,9),label:r.label||'home',t:Date.now(),name:me.name,phone:(SX.user&&SX.user.phone)||'',line1:r.door.trim(),line2:'',landmark:r.landmark.trim(),area:w.place||'',city:w.city||'',state:w.state||'',pin:w.pin||'',lat:r.lat,lng:r.lng,default:!S.addresses.length};
  if(o.default)S.addresses.forEach(x=>x.default=false);S.addresses.push(o);S.addr=SX.addrFmt(o);SX.save();try{SX.act.addrpick([o.id])}catch(e){}
  if(!o.line1||!/^\d{6}$/.test(o.pin)){toast(P('Pinned. Add the house and PIN.'));return ae0([o.id])}
  toast(P('Address saved'));try{render()}catch(e){}const c=document.getElementById('caddr');if(c)c.value=S.addr;return}
 ae0(a);const b=document.getElementById('aduse');if(!b)return;b.textContent='🗺️ '+P('Pick on the map');
 b.onclick=async()=>{const F=document.getElementById('adf');const keep={};['name','phone','line1','line2','landmark','area','city','state','pin','label'].forEach(k=>{const el=F.elements[k];if(el)keep[k]=el.value});
  const r=await SX.mapPick({address:true,title:P('Pin the address'),cta:P('Use this spot'),door:keep.line1,landmark:keep.landmark,pin:keep.pin,label:keep.label||'home'});if(!r){return SX.act.addredit([id])}
  const ad=S.addresses.find(x=>x.id===id);if(ad){Object.assign(ad,{lat:r.lat,lng:r.lng});if(r.where){ad.area=r.where.place||ad.area;ad.city=r.where.city||ad.city;ad.state=r.where.state||ad.state;ad.pin=r.where.pin||ad.pin}if(r.door)ad.line1=r.door;if(r.landmark)ad.landmark=r.landmark;Object.keys(keep).forEach(k=>{if(['name','phone','line2'].includes(k)&&keep[k])ad[k]=keep[k]});SX.save()}
  SX.act.addredit([id])}};

// ---------------------------------------------------------------- E. SOS: siren + vibration until "I'm safe"; a map of the live position; what went out by itself
let ctx=null,osc=null,gain=null,vib=null,sweep=null,muted=false;
SX.siren={
 start(){if(osc)return;muted=false;try{ctx=ctx||new (window.AudioContext||window.webkitAudioContext)();if(ctx.state==='suspended')ctx.resume();osc=ctx.createOscillator();gain=ctx.createGain();osc.type='square';gain.gain.value=.0001;osc.connect(gain);gain.connect(ctx.destination);osc.start();
   gain.gain.exponentialRampToValueAtTime(.35,ctx.currentTime+.15);let up=true;const step=()=>{if(!osc)return;const t=ctx.currentTime;osc.frequency.cancelScheduledValues(t);osc.frequency.setValueAtTime(up?620:1180,t);osc.frequency.linearRampToValueAtTime(up?1180:620,t+.55);up=!up};step();sweep=setInterval(step,550)}catch(e){}
  try{if(navigator.vibrate){navigator.vibrate([500,200,500,200,500]);vib=setInterval(()=>navigator.vibrate([500,200,500,200,500]),2000)}}catch(e){}
  try{if(window.Capacitor&&Capacitor.Plugins&&Capacitor.Plugins.Haptics)Capacitor.Plugins.Haptics.vibrate({duration:600})}catch(e){}
  document.body.classList.add('lv29-siren')},
 mute(){muted=true;try{if(gain&&ctx)gain.gain.exponentialRampToValueAtTime(.0001,ctx.currentTime+.1)}catch(e){}clearInterval(sweep);sweep=null;setTimeout(()=>{try{osc&&osc.stop()}catch(e){}osc=null},150)},
 stop(){this.mute();clearInterval(vib);vib=null;try{navigator.vibrate&&navigator.vibrate(0)}catch(e){}document.body.classList.remove('lv29-siren')},
 on:()=>!!osc};
SX.act.sosmute=()=>{SX.siren.mute();const b=document.getElementById('lv29mute');if(b)b.textContent='🔇 '+P('Siren off')};
let CH=null;J('/sos/channels').then(j=>{CH=j}).catch(()=>{});
function sosChrome(){const act=document.getElementById('lv21act');if(!act)return;const head=act.querySelector('.lv21-head');
 if(head&&!document.getElementById('lv29mute')&&SX.siren.on()){const b=document.createElement('button');b.id='lv29mute';b.className='lv29-mute';b.type='button';b.textContent='🔊 '+P('Siren');b.onclick=SX.act.sosmute;head.insertBefore(b,head.querySelector('.lv21-safe'));head.querySelector('.lv21-live')&&head.querySelector('.lv21-live').classList.add('lv29-alarm')}
 const sec=act.querySelector('.lv21-sec');if(sec&&!sec.querySelector('.lv29-sosmap')){const a=act.querySelector('a[href*="maps.google.com/?q="]');const m=a&&a.getAttribute('href').match(/q=(-?[\d.]+),(-?[\d.]+)/);const c=m?{lat:+m[1],lng:+m[2]}:SX.loc.get();
  if(c){const d=document.createElement('div');d.className='lv29-sosmap';d.innerHTML=SX.mapHTML?SX.mapHTML(c,[],{h:160,zoom:15}):miniMap(c);sec.appendChild(d)}}
 const al=act.querySelectorAll('.lv21-sec')[1];if(al&&CH&&!al.querySelector('.lv29-ch')){const d=document.createElement('div');d.className='lv29-ch';d.innerHTML=[['push',P('Family phones')],['email',P('Email')],['sms','SMS'],['whatsapp','WhatsApp']].map(([k,t])=>`<span class="${CH[k]?'on':''}">${CH[k]?'✓':'·'} ${t}${CH[k]?'':' · '+P('one tap')}</span>`).join('');al.querySelector('.lv21-sh').after(d)}}
SX.extend('sos',{after(){if(!CH)return '';const auto=[['push',P('App alert on family phones')],['email',P('Email to contacts')],['sms',P('SMS to contacts')],['whatsapp',P('WhatsApp to contacts')]];
 return `<div class="card"><div class="hd"><div><h3>⚡ ${P('Goes out the moment you press')}</h3><small class="mute">${P('No countdown, no confirmation. A siren sounds and your phone buzzes until you tap “I’m safe”.')}</small></div></div><div class="lv29-ch">${auto.map(([k,t])=>`<span class="${CH[k]?'on':''}">${CH[k]?'✓ ':''}${t}${CH[k]?'':' · '+P('one tap')}</span>`).join('')}</div>${CH.sms&&CH.whatsapp?'':`<p class="mute sm" style="margin:8px 0 0">${P('SMS and WhatsApp that leave without a tap need a registered sender (DLT template / WhatsApp Business); until then they open ready to send with one tap.')}</p>`}</div>`}});
// the WhatsApp / SMS chips open by themselves for the first contact when the server cannot send them (one tap fewer in the moment)
// (nothing automatic here: a browser cannot send a message without the person's tap)

// ---------------------------------------------------------------- F. Devices: install the way this phone installs
SX.a2hs=()=>{SX.modal(`<h2>📲 ${P('Install on iPhone')}</h2><ol class="lv-steps" style="padding-left:18px;line-height:1.7"><li>${P('Tap the Share button')} <b>⎙</b> ${P('at the bottom of Safari')}</li><li>${P('Choose')} <b>${P('Add to Home Screen')}</b></li><li>${P('Tap')} <b>${P('Add')}</b> — ${P('TheHealthTracker opens full-screen like an app, with your sign-in kept.')}</li></ol><p class="mute sm">${P('Apple Health sync arrives with the App Store app.')}</p><div class="lv-row-end"><button class="btn p" data-sx="closeModal">${P('Got it')}</button></div>`,{label:'Install'})};
SX.act.a2hs=()=>SX.a2hs();

// the tab bar keeps its short labels and icons when the nav is rebuilt
function tabLabels(){const bar=document.getElementById('mtab');if(!bar)return;bar.querySelectorAll('button span').forEach(sp=>{const t=sp.textContent.trim();if(t==='Medicines'||t===P('Medicines'))sp.textContent=P('Meds')})}

// the week strip's day letters follow the language too
function weekDays(){if(LANG()==='en')return;const box=document.querySelector('.lv22-days');if(!box||box.dataset.lv29===LANG())return;box.dataset.lv29=LANG();
 const cells=[...box.querySelectorAll('i')],L=LANG()==='hi'?'hi-IN':'te-IN';
 cells.forEach((c,k)=>{const d=new Date();d.setDate(d.getDate()-(cells.length-1-k));const t=d.toLocaleDateString(L,{weekday:'narrow'});
  [...c.childNodes].forEach(n=>{if(n.nodeType===3&&n.nodeValue.trim())n.nodeValue=t})})}

// ---------------------------------------------------------------- G. card vault: previous / next
function walletNav(){const w=document.querySelector('.lv2-wallet');if(!w||w.previousElementSibling&&w.previousElementSibling.classList.contains('lv29-wnav'))return;const slots=[...w.querySelectorAll('.lv2-slot:not(.lv2-add)')];if(slots.length<1)return;
 const i=Math.max(0,slots.findIndex(s=>s.classList.contains('on')));const nav=document.createElement('div');nav.className='lv29-wnav';nav.innerHTML=`<button type="button" ${i<=0?'disabled':''} aria-label="${E(P('Previous card'))}">‹</button><small>${i+1} / ${slots.length}</small><button type="button" ${i>=slots.length-1?'disabled':''} aria-label="${E(P('Next card'))}">›</button>`;
 const [prev,,next]=nav.children;const goI=k=>{const s=slots[k];if(!s)return;const id=(s.dataset.sx||'').replace(/^wsel:/,'');if(id)SX.act.wsel(id.split(':'))};
 prev.onclick=()=>goI(i-1);next.onclick=()=>goI(i+1);w.before(nav);
 const dots=document.createElement('div');dots.className='lv29-wdots';dots.innerHTML=slots.map((s,k)=>`<i class="${k===i?'on':''}"></i>`).join('');w.after(dots);
 const on=slots[i];if(on)setTimeout(()=>{try{on.scrollIntoView({inline:'center',block:'nearest',behavior:'instant'})}catch(e){on.scrollIntoView()}},0);
 let sx=0;w.addEventListener('touchstart',e=>{sx=e.touches[0].clientX},{passive:true});w.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-sx;if(Math.abs(dx)>60)goI(dx<0?i+1:i-1)},{passive:true})}

// ---------------------------------------------------------------- H. translations on every string the screen paints
// dates and times follow the chosen language (the app asks for 'en-IN' in a hundred places; one interception covers them all)
{const LOC={hi:'hi-IN',te:'te-IN'};['toLocaleDateString','toLocaleTimeString','toLocaleString'].forEach(k=>{const f=Date.prototype[k];Date.prototype[k]=function(l,o){const L=LOC[S.lang||'en'];return f.call(this,(!l||l==='en-IN'||l==='en')&&L?L:l,o)}})}
SX.addPhrases(/*LV29_CORE*/{}/*/LV29_CORE*/);   // the round-29 strings, by hand (inlined from tools/i18n/core.py at patch time)
const LANG=()=>S.lang||'en';
const SKIP='script,style,textarea,code,pre,svg,canvas,#stage,#hstage,#pstage,[data-noi18n],.lv-card-num,.lv29-sug,.lv29-addr,[contenteditable]';
const tr=s=>{let r=P(s);if(r!==s)return r;const m=s.match(/^(.*?)([:…·.!?]+)$/);if(m){r=P(m[1]);if(r!==m[1])return r+m[2]}const m2=s.match(/^([\u{1F300}-\u{1FAFF}☀-➿✓✔•·—–]️?\s*)(.+)$/u);if(m2){r=P(m2[2]);if(r!==m2[2])return m2[1]+r}return null};
let missing=new Set(),sentSet=null,flushT=null,applying=false;
const sentLoad=()=>{if(sentSet)return;sentSet=new Set();try{(JSON.parse(ls('tht.i18n.sent')||'[]')).forEach(x=>sentSet.add(x))}catch(e){}};
function names(){const out=[];(S.members||[]).forEach(m=>{(m.name||'').split(/\s+/).forEach(w=>{if(w.length>2)out.push(w)})});if(SX.user&&SX.user.name)out.push(SX.user.name.split(/\s+/)[0]);return out}
function note(s){if(LANG()==='en')return;if(s.length>200||!/[A-Za-z]{3,}/.test(s)||/[{}<>]|\$\{|https?:|@/.test(s)||/^[A-Z0-9 _\-./]{2,12}$/.test(s))return;
 if(/\d/.test(s)&&!/\s/.test(s))return;
 if(names().some(n=>s.includes(n)))return;   // a line with a family name in it is one person's, not a phrase
 sentLoad();if(sentSet.has(s)||missing.has(s))return;missing.add(s);clearTimeout(flushT);flushT=setTimeout(flush,2500)}
async function flush(){if(!missing.size||LANG()==='en')return;const items=[...missing].slice(0,150);items.forEach(x=>{missing.delete(x);sentSet.add(x)});try{ls('tht.i18n.sent',JSON.stringify([...sentSet].slice(-4000)))}catch(e){}
 try{const r=await J('/i18n/missing','POST',{items});if(r.added&&r.translator){let n=0;const again=()=>{if(n++>4)return;setTimeout(async()=>{const fresh=await table(true);if(!fresh)again()},n*12000)};again()}}catch(e){}
 if(missing.size)flushT=setTimeout(flush,3000)}
function textNode(n){const v=n.nodeValue;if(!v||!/\S/.test(v))return;const s=v.trim();if(s.length<2||s.length>240)return;if(n.__i18n===s)return;const r=tr(s);if(r){applying=true;n.nodeValue=v.replace(s,r);n.__i18n=r;applying=false}else{n.__i18n=s;if(/[A-Za-z]{2,}/.test(s))note(s)}}
const AK={placeholder:'i18nPh','aria-label':'i18nAria',title:'i18nTitle'};
function attrs(el){for(const a in AK){const v=el.getAttribute&&el.getAttribute(a);if(!v||el.dataset[AK[a]]===v)continue;const r=tr(v.trim());if(r){el.setAttribute(a,r);el.dataset[AK[a]]=r}else{el.dataset[AK[a]]=v;note(v.trim())}}
 if(el.tagName==='INPUT'&&/^(submit|button)$/.test(el.type)&&el.value){const r=tr(el.value.trim());if(r)el.value=r}}
function walk(root){if(LANG()==='en'||!root)return;if(root.nodeType===3){const p=root.parentElement;if(p&&!p.closest(SKIP))textNode(root);return}if(root.nodeType!==1||root.closest(SKIP))return;
 const tw=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>{const p=n.parentElement;return p&&!p.closest(SKIP)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT}});const nodes=[];let n;while((n=tw.nextNode()))nodes.push(n);nodes.forEach(textNode);
 if(root.matches&&root.matches('[placeholder],[aria-label],[title],input'))attrs(root);root.querySelectorAll('[placeholder],[aria-label],[title],input[type=submit]').forEach(attrs)}
SX.i18nDom=root=>walk(root||document.body);
// the table: always fresh (no stale cache), re-applied when it changes
let tv=ls('tht.i18n.v')||'';
async function table(quiet){if(LANG()==='en')return false;try{const r=await fetch('/api/v1/i18n',{cache:'no-store',headers:{'x-tht':'1'}});if(!r.ok)return false;const j=await r.json();const v=String(j.__v||'');delete j.__v;if(v&&v===tv&&quiet)return false;SX.addPhrases(j);ls('tht.i18n',JSON.stringify(j));ls('tht.i18n.v',v);const changed=v!==tv;tv=v;
  if(changed){document.querySelectorAll('[data-i18n-ph],[data-i18n-aria],[data-i18n-title]').forEach(el=>{delete el.dataset.i18nPh;delete el.dataset.i18nAria;delete el.dataset.i18nTitle});const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while((n=tw.nextNode()))if(n.__i18n===n.nodeValue.trim())delete n.__i18n;walk(document.body);try{SX.paintNav&&SX.paintNav()}catch(e){}}return changed}catch(e){return false}}
SX.i18nRefresh=()=>table(false);
const lang0=SX.act.lang;SX.act.lang=async a=>{await lang0(a);document.documentElement.lang=LANG();if(LANG()!=='en'){await table(false);walk(document.body)}};
document.documentElement.lang=LANG();
// one observer for all the after-paint work: translations, the orb, the heart chrome, the SOS sheet, the wallet arrows
let obT=null,pend=[];
const after=()=>{obT=null;tabLabels();weekDays();const nodes=pend;pend=[];if(LANG()!=='en'&&!applying)nodes.forEach(n=>{if(n.isConnected)walk(n)});paintOrb();heartChrome();sosChrome();walletNav();askBar()};
new MutationObserver(ms=>{if(applying)return;ms.forEach(m=>m.addedNodes.forEach(n=>pend.push(n)));if(!obT)obT=setTimeout(after,40)}).observe(document.body,{childList:true,subtree:true});
setTimeout(()=>{if(LANG()!=='en'){table(true).then(()=>walk(document.body));walk(document.body)}paintOrb();heartChrome();walletNav();tabLabels();SX.pregNav&&SX.pregNav()},300);
addEventListener('focus',()=>{if(LANG()!=='en')table(true)});
}
