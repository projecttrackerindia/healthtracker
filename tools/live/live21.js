// ===================== live layer 21: SOS that acts — one press calls, locates, alerts; a live page for the people alerted =====================
{
const P=SX.p,S=SX.S;
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1','x-dokko-key':(S.key||'')},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status});return j});
const native=()=>!!(window.Capacitor&&Capacitor.isNativePlatform&&Capacitor.isNativePlatform());
const android=()=>/Android/.test(navigator.userAgent),ios=()=>/iP(hone|ad|od)/.test(navigator.userAgent);
const fmtT=t=>new Date(t).toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit'});
S.sosCall=S.sosCall||'112';
S.sosPerm=S.sosPerm||{};

// ---------------------------------------------------------------- location: asked once at set-up, instant at the moment it matters
let lastFix=null;
function locate(ms){return new Promise(res=>{if(!navigator.geolocation||S.consent.sos_location===false)return res(null);let fin=false;const to=setTimeout(()=>{if(!fin){fin=true;res(lastFix)}},ms);
 try{navigator.geolocation.getCurrentPosition(p=>{if(fin)return;fin=true;clearTimeout(to);lastFix={lat:p.coords.latitude,lng:p.coords.longitude,acc:Math.round(p.coords.accuracy||0),t:Date.now()};res(lastFix)},()=>{if(fin)return;fin=true;clearTimeout(to);res(lastFix)},{enableHighAccuracy:true,timeout:ms,maximumAge:20000})}catch(e){if(!fin){fin=true;clearTimeout(to);res(lastFix)}}})}
SX.act.sosperm=async()=>{toast(P('Allowing location…'));const f=await locate(12000);try{const C=window.Capacitor,SOSP=C&&C.Plugins&&C.Plugins.Sos;if(native()&&android()&&SOSP)await SOSP.prepare()}catch(e){}   // Android: the call permission too, so the call starts by itself
 if(f){S.sosPerm.loc=Date.now();SX.save();toast(P('Location is ready for SOS'));render()}else toast(P('Location was not allowed. Check the phone’s settings for this app.'))};

// ---------------------------------------------------------------- who to call first
function callTarget(m){const v=S.sosCall||'112';if(v==='112'||v==='108')return {num:v,label:v,who:v==='108'?P('Ambulance'):P('Emergency services')};const c=SX.contactsOf(m.id).find(x=>x.id===v&&x.ph);return c?{num:c.ph,label:c.n,who:c.rel}:{num:'112',label:'112',who:P('Emergency services')}}
async function placeCall(num){try{const C=window.Capacitor,SOSP=C&&C.Plugins&&C.Plugins.Sos;if(native()&&android()&&SOSP){await SOSP.call({number:num});return 'auto'}}catch(e){}
 try{location.href='tel:'+num}catch(e){}return 'dialer'}
SX.chg.soscall=(a,el)=>{S.sosCall=el.value;SX.save();toast(P('SOS will call')+' '+el.options[el.selectedIndex].text)};

// ---------------------------------------------------------------- the set-up card on the Safety page
SX.extend('sos',{before(){const m=SX.me(),cs=SX.contactsOf(m.id),withEm=cs.filter(c=>c.em).length,perm=!!S.sosPerm.loc;
 return `<div class="card lv21-setup"><div class="hd"><div><h3>${P('When you press SOS')}</h3><small class="mute">${P('One press. The phone calls, your location goes out, and everyone you chose is told — with a live map they can open.')}</small></div></div>
  <div class="lv21-row"><div class="grow"><b>${P('Call first')}</b><small>${android()&&native()?P('On this phone the call starts by itself.'):P('The dialer opens with the number ready.')}</small></div><select data-sxc="soscall" class="lv21-sel"><option value="112" ${S.sosCall==='112'?'selected':''}>112 · ${P('Emergency services')}</option><option value="108" ${S.sosCall==='108'?'selected':''}>108 · ${P('Ambulance')}</option>${cs.filter(c=>c.ph).map(c=>`<option value="${E(c.id)}" ${S.sosCall===c.id?'selected':''}>${E(c.n)} · ${E(c.rel)}</option>`).join('')}</select></div>
  <div class="lv21-row"><div class="grow"><b>${P('Location')}</b><small>${perm?P('Allowed · ready in an instant'):P('Allow it now, so the emergency moment has no pop-ups.')}</small></div>${perm?`<span class="lv21-ok">✓</span>`:`<button class="btn p sm" data-sx="sosperm">${P('Allow')}</button>`}</div>
  <div class="lv21-row"><div class="grow"><b>${P('Instant alerts')}</b><small>${cs.length?(withEm?withEm+' '+P('of')+' '+cs.length+' '+P('contacts get an email the moment you press; everyone gets WhatsApp/SMS with one tap. Family members with the app get a push alert.'):P('Add an email to your contacts so they are told the moment you press, with no tap from you. Family members with the app get a push alert.')):P('Add an emergency contact first.')}</small></div><button class="btn s sm" data-sx="tab:contacts">${P('Contacts')}</button></div></div>`}});

// ---------------------------------------------------------------- the press
let A=null;   // the open alert: {id, token, url, m, timer, loc}
let cd=null;
SX.openSOS=()=>{const m=SX.me();if(A&&A.active){SX.modal(activeHTML(m),{cls:'sx-sos-m lv21-m',label:'SOS',sticky:true});wire();return}
 const t=callTarget(m);let n=3;
 SX.modal(`<div class="lv21-cd"><div class="lv21-ring"><b id="lv21n">${n}</b></div><h2>${P('Calling')} ${E(t.label)}</h2><p>${P('and alerting your family with your location')}</p><button class="lv21-cancel" id="lv21cancel">${P('Cancel')}</button><button class="lv21-now" id="lv21now">${P('Send now')}</button></div>`,{cls:'sx-sos-m lv21-m',label:'SOS',sticky:true});
 locate(2500);   // warm the fix while the ring counts down
 const stop=()=>{clearInterval(cd);cd=null};
 document.getElementById('lv21cancel').onclick=()=>{stop();SX.closeModal();toast(P('SOS cancelled'))};
 document.getElementById('lv21now').onclick=()=>{stop();fire(m)};
 cd=setInterval(()=>{n--;const el=document.getElementById('lv21n');if(!el){stop();return}if(n<=0){stop();fire(m)}else el.textContent=n},1000)};
SX.act.sos=()=>SX.openSOS();

async function fire(m){const t=callTarget(m),cs=SX.contactsOf(m.id).filter(c=>c.notify);
 A={m:m.id,active:true,call:t,sent:[],loc:lastFix,created:Date.now(),hosp:null};
 SX.modal(activeHTML(m),{cls:'sx-sos-m lv21-m',label:'SOS',sticky:true});wire();
 // 1. the call — first, nothing waits for the network
 try{navigator.vibrate&&navigator.vibrate([200,100,200])}catch(e){}
 A.how=await placeCall(t.num);paint(m);
 // 2. the alert — with whatever location we already have; the first fix follows as an update
 const loc=A.loc||await locate(6000);A.loc=loc;
 const body={member:m.id,name:m.name,phone:(m.rel==='You'&&SX.user&&SX.user.phone)||'',summary:SX.medSummary(m),blood:(SX.midOf(m.id).blood||''),loc:loc?{lat:loc.lat,lng:loc.lng,acc:loc.acc}:null,contacts:cs.map(c=>({n:c.n,ph:c.ph||'',em:c.em||''})),lang:S.lang||'en'};
 try{const r=await J('/sos/start','POST',body);Object.assign(A,{id:r.id,token:r.token,url:r.url,sent:r.sent||[],msg:r.message});S.sos.unshift({t:Date.now(),m:m.id,loc:loc?{lat:+loc.lat.toFixed(4),lng:+loc.lng.toFixed(4)}:null,n:cs.filter(c=>c.ph).length,url:r.url});S.sos.length=Math.min(S.sos.length,30);SX.ledger('sos',true,'SOS sent · live page '+r.url,m.id);SX.save()}
 catch(e){A.err=e.message;A.msg=offlineMsg(m,loc)}
 paint(m);
 // 3. keep the live page moving while the alert is open
 if(A.id){A.timer=setInterval(async()=>{if(!A||!A.active)return;const f=await locate(8000);if(f&&(!A.loc||Math.abs(f.lat-A.loc.lat)>1e-5||Math.abs(f.lng-A.loc.lng)>1e-5)){A.loc=f;try{const r=await J('/sos/'+A.id+'/loc','POST',{loc:{lat:f.lat,lng:f.lng,acc:f.acc}});if(r.sent)A.sent=r.sent}catch(e){}paint(m)}},30000)}
 else if(!loc){const f=await locate(15000);if(f){A.loc=f;A.msg=offlineMsg(m,f);paint(m)}}
 hospitals(m)}
function offlineMsg(m,loc){return [`EMERGENCY: ${m.name} needs help.`,loc?`Location: https://maps.google.com/?q=${loc.lat.toFixed(6)},${loc.lng.toFixed(6)}`:'Location: not available. Please call them.',SX.medSummary(m),'Call them or 112 now. Sent from Urban Health SOS.'].join('\n')}
async function hospitals(m){if(!A||!A.loc||A.hosp)return;try{const r=await J(`/places?kind=hospital&lat=${A.loc.lat}&lng=${A.loc.lng}&radius=6000`);A.hosp=(r.items||[]).slice(0,3);paint(m)}catch(e){A.hosp=[]}}

// ---------------------------------------------------------------- the active sheet
function activeHTML(m){return `<div class="lv21-act" id="lv21act">${activeBody(m)}</div>`}
function paint(m){const el=document.getElementById('lv21act');if(el){el.innerHTML=activeBody(m);wire()}}
function activeBody(m){if(!A)return '';const cs=SX.contactsOf(m.id).filter(c=>c.notify),t=A.call,loc=A.loc;
 const ch=(n,c)=>A.sent.some(x=>x.n===n&&x.channel===c&&x.ok);
 const wa=c=>c.ph?`<a class="lv21-chip wa" href="https://wa.me/${c.ph.replace(/\D/g,'')}?text=${encodeURIComponent(A.msg||'')}" target="_blank" rel="noopener">WhatsApp</a>`:'';
 const sms=c=>c.ph?`<a class="lv21-chip" href="sms:${c.ph}${ios()?'&':'?'}body=${encodeURIComponent(A.msg||'')}">SMS</a>`:'';
 return `<div class="lv21-head"><span class="lv21-live"><i></i>${A.active?P('SOS active'):P('SOS ended')} · ${fmtT(A.created)}</span>${A.active?`<button class="lv21-safe" data-sx="sossafe">${P('I’m safe')}</button>`:''}</div>
 <div class="lv21-calls"><a class="lv21-call main" href="tel:${E(t.num)}"><small>${A.how==='auto'?P('Calling'):P('Call')}</small><b>${E(t.label)}</b></a>${t.num!=='112'?`<a class="lv21-call" href="tel:112"><small>${P('Call')}</small><b>112</b></a>`:`<a class="lv21-call" href="tel:108"><small>${P('Call')}</small><b>108</b></a>`}</div>
 <div class="lv21-sec"><div class="lv21-sh"><b>${P('Your location')}</b><small>${loc?(loc.acc?P('about')+' '+loc.acc+' m':P('found')):(S.consent.sos_location===false?P('sharing is off in Consent'):P('finding…'))}</small></div>
  <div class="lv21-chips">${loc?`<a class="lv21-chip" href="https://maps.google.com/?q=${loc.lat.toFixed(6)},${loc.lng.toFixed(6)}" target="_blank" rel="noopener">${P('Open map')}</a>`:''}${A.url?`<button class="lv21-chip" data-sx="soslink">${P('Share live link')}</button>`:''}${A.err?`<span class="lv21-err">${P('Offline: alerts go by SMS/WhatsApp below')}</span>`:''}</div></div>
 <div class="lv21-sec"><div class="lv21-sh"><b>${P('Alerted')}</b><small>${A.id?P('email + app alerts sent'):A.err?P('could not reach the server'):P('sending…')}</small></div>
  ${cs.length?cs.map(c=>`<div class="lv21-c"><div class="grow"><b>${E(c.n)}</b><small>${[ch(c.n,'email')?'✓ '+P('email'):c.em?P('email…'):'',ch(c.n,'sms')?'✓ SMS':'',c.ph?'':P('no number')].filter(Boolean).join(' · ')}</small></div>${wa(c)}${sms(c)}</div>`).join(''):`<p class="mute sm">${P('No emergency contacts yet.')} <button class="sx-lk" data-sx="tab:contacts">${P('Add one')}</button></p>`}
  ${A.sent.some(x=>x.channel==='push')?`<div class="lv21-c"><div class="grow"><b>${P('Family phones')}</b><small>✓ ${P('app alert with the live map')}</small></div></div>`:''}
  ${cs.filter(c=>c.ph).length>1?`<a class="lv21-chip all" href="sms:${cs.filter(c=>c.ph).map(c=>c.ph).join(',')}${ios()?'&':'?'}body=${encodeURIComponent(A.msg||'')}">${P('SMS everyone')}</a>`:''}</div>
 ${A.hosp&&A.hosp.length?`<div class="lv21-sec"><div class="lv21-sh"><b>${P('Nearest hospitals')}</b></div>${A.hosp.map(h=>`<div class="lv21-c"><div class="grow"><b>${E(h.name)}</b><small>${h.km} km${h.emergency?' · '+P('emergency ward'):''}</small></div>${h.phone?`<a class="lv21-chip" href="tel:${E(h.phone)}">${P('Call')}</a>`:''}<a class="lv21-chip" href="https://www.google.com/maps/dir/?api=1&destination=${h.lat},${h.lng}&travelmode=driving" target="_blank" rel="noopener">${P('Directions')}</a></div>`).join('')}</div>`:''}
 <div class="lv21-foot"><button class="btn s" data-sx="sosclose">${A.active?P('Hide (stays active)'):P('Close')}</button></div>`}
function wire(){}
SX.act.soslink=async()=>{if(!A||!A.url)return;const text=A.msg||A.url;try{if(navigator.share)await navigator.share({title:'Emergency',text,url:A.url});else{await navigator.clipboard.writeText(A.url);toast(P('Live link copied'))}}catch(e){if(e&&e.name!=='AbortError'){try{await navigator.clipboard.writeText(A.url);toast(P('Live link copied'))}catch(_){}}}};
SX.act.sossafe=async()=>{if(!A)return;A.active=false;clearInterval(A.timer);if(A.id){try{await J('/sos/'+A.id+'/end','POST',{})}catch(e){}}toast(P('Alert ended — your family is told you are safe'));const m=SX.member(A.m)||SX.me();paint(m);setTimeout(()=>{if(A&&!A.active){A=null;SX.closeModal();try{render()}catch(e){}}},1500)};
SX.act.sosclose=()=>{SX.closeModal();if(A&&!A.active)A=null;try{render()}catch(e){}};
// an alert that is still open shows a thin bar at the top of every screen
setInterval(()=>{const on=!!(A&&A.active);let b=document.getElementById('lv21bar');if(on&&!b){b=document.createElement('button');b.id='lv21bar';b.innerHTML=`<i></i>${P('SOS active')} · ${P('tap to open')}`;b.onclick=()=>SX.openSOS();document.body.appendChild(b)}else if(!on&&b)b.remove()},1000);
}
