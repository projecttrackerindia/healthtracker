// ===================== live layer 32: one location for the whole app — one permission, one sheet, one chip =====================
// Before this, six places asked for a position in six ways. Now there is one door: SX.needLoc(module). The first time it
// opens the Allow-your-location sheet, where the family sees exactly which parts of the app will use it and can switch
// any of them off — except emergency SOS, which is required and says so. Everything else (labs, pharmacies, doctors,
// alerts, live tracking in an emergency) reads the same saved position and the same permission.
{
const P=SX.p,S=SX.S;
S.net=S.net||{};
const phone=()=>matchMedia('(max-width:720px)').matches;

SX.addPhrases({
 'Allow your location':['अपनी लोकेशन की अनुमति दें','మీ లొకేషన్‌ను అనుమతించండి'],
 'One permission, used across the app':['एक बार अनुमति, पूरे ऐप में उपयोग','ఒకసారి అనుమతి, యాప్ అంతటా వాడకం'],
 'Choose what it is used for. You can change any of this later in Settings.':
  ['चुनें कि इसका उपयोग किसके लिए हो। आप इसे बाद में सेटिंग्स में बदल सकते हैं।','దేనికోసం వాడాలో ఎంచుకోండి. తర్వాత సెట్టింగ్‌లలో మార్చుకోవచ్చు.'],
 'Required':['ज़रूरी','తప్పనిసరి'],
 'Emergency SOS':['आपातकालीन SOS','అత్యవసర SOS'],
 'Your location goes to the people you chose, and to the live map they open. SOS cannot work without it.':
  ['आपकी लोकेशन उन लोगों तक जाती है जिन्हें आपने चुना है, और उस लाइव मैप तक जिसे वे खोलते हैं। इसके बिना SOS काम नहीं करता।',
   'మీరు ఎంచుకున్న వ్యక్తులకు, వారు తెరిచే లైవ్ మ్యాప్‌కు మీ లొకేషన్ వెళ్తుంది. దీని లేకుండా SOS పనిచేయదు.'],
 'Labs and tests near you':['आपके पास की लैब और जाँचें','మీ దగ్గరి ల్యాబ్‌లు, టెస్టులు'],
 'Prices, home collection and distance from accredited labs.':['मान्यता प्राप्त लैब से क़ीमतें, घर से सैंपल और दूरी।','గుర్తింపు పొందిన ల్యాబ్‌ల ధరలు, ఇంటి వద్ద శాంపిల్, దూరం.'],
 'Pharmacies and delivery':['फ़ार्मेसी और डिलीवरी','ఫార్మసీలు, డెలివరీ'],
 'Which chemists can deliver to you, and how fast.':['कौन-सी दुकानें आप तक पहुँचा सकती हैं और कितनी जल्दी।','ఏ మందుల దుకాణాలు మీకు డెలివరీ చేయగలవు, ఎంత త్వరగా.'],
 'Doctors and hospitals':['डॉक्टर और अस्पताल','డాక్టర్లు, ఆసుపత్రులు'],
 'Clinics near you when you book a visit.':['विज़िट बुक करते समय पास के क्लिनिक।','విజిట్ బుక్ చేసేటప్పుడు దగ్గరి క్లినిక్‌లు.'],
 'Alerts for your area':['आपके इलाक़े के अलर्ट','మీ ప్రాంత అలర్ట్‌లు'],
 'Dengue, heat and air-quality warnings for your city.':['आपके शहर के लिए डेंगू, गर्मी और हवा की चेतावनी।','మీ నగరానికి డెంగ్యూ, వేడి, గాలి నాణ్యత హెచ్చరికలు.'],
 'Live location in an emergency':['आपात स्थिति में लाइव लोकेशन','అత్యవసరంలో లైవ్ లొకేషన్'],
 'While an SOS is open, the map keeps moving with you until you tap “I’m safe”.':
  ['जब तक SOS खुला है, मैप आपके साथ चलता रहता है — जब तक आप “मैं सुरक्षित हूँ” न दबाएँ।',
   'SOS తెరిచి ఉన్నంత వరకు, “నేను క్షేమం” నొక్కే వరకు మ్యాప్ మీతో కదులుతూ ఉంటుంది.'],
 'Allow location':['लोकेशन की अनुमति दें','లొకేషన్ అనుమతించండి'],
 'Maybe later':['बाद में','తర్వాత'],
 'Only while you use the app. Your position is never sold or shared with other families.':
  ['सिर्फ़ ऐप इस्तेमाल करते समय। आपकी लोकेशन न बेची जाती है, न दूसरे परिवारों से साझा होती है।',
   'మీరు యాప్ వాడుతున్నప్పుడు మాత్రమే. మీ లొకేషన్ అమ్మబడదు, ఇతర కుటుంబాలతో పంచుకోబడదు.'],
 'Location is off for this':['इसके लिए लोकेशन बंद है','దీనికి లొకేషన్ ఆఫ్‌లో ఉంది'],
 'Turn it on':['चालू करें','ఆన్ చేయండి'],
 'Location':['लोकेशन','లొకేషన్'],
 'Used by':['उपयोग','వాడకం'],
 'Change':['बदलें','మార్చండి'],
 'Not set':['सेट नहीं है','సెట్ చేయలేదు'],
 'Locating…':['लोकेशन खोजी जा रही है…','లొకేషన్ కనుగొంటోంది…'],
 'Location is blocked in the browser. Allow it in site settings, or choose your area on the map.':
  ['ब्राउज़र में लोकेशन ब्लॉक है। साइट सेटिंग्स में अनुमति दें, या मैप पर अपना इलाक़ा चुनें।',
   'బ్రౌజర్‌లో లొకేషన్ బ్లాక్ చేయబడింది. సైట్ సెట్టింగ్‌లలో అనుమతించండి, లేదా మ్యాప్‌లో మీ ప్రాంతాన్ని ఎంచుకోండి.'],
 'Live':['लाइव','లైవ్'],
 'SOS needs your location':['SOS को आपकी लोकेशन चाहिए','SOSకి మీ లొకేషన్ అవసరం'],
 'Fix it now':['अभी ठीक करें','ఇప్పుడే సరిచేయండి']});

// ---------------------------------------------------------------- A. the one permission record
const MODULES=()=>[
 {k:'sos',req:true,ic:'cross',t:P('Emergency SOS'),s:P('Your location goes to the people you chose, and to the live map they open. SOS cannot work without it.')},
 {k:'labs',ic:'records',t:P('Labs and tests near you'),s:P('Prices, home collection and distance from accredited labs.')},
 {k:'meds',ic:'pill',t:P('Pharmacies and delivery'),s:P('Which chemists can deliver to you, and how fast.')},
 {k:'care',ic:'heart',t:P('Doctors and hospitals'),s:P('Clinics near you when you book a visit.')},
 {k:'alerts',ic:'home',t:P('Alerts for your area'),s:P('Dengue, heat and air-quality warnings for your city.')},
 {k:'live',ic:'pulse',t:P('Live location in an emergency'),s:P('While an SOS is open, the map keeps moving with you until you tap “I’m safe”.')}];
const perm=()=>{const p=S.net.perm=S.net.perm||{};p.mod=p.mod||{};MODULES().forEach(m=>{if(p.mod[m.k]===undefined)p.mod[m.k]=true});p.mod.sos=true;return p};
SX.locPerm=perm;
SX.locOn=k=>{const p=perm();return k==='sos'?true:p.mod[k]!==false};
SX.locAsked=()=>!!perm().at;
const pageModule=()=>({labshop:'labs',tests:'labs',nearlabs:'labs',vault:'labs',insights:'labs',finder:'meds',orders:'meds',rx:'meds',cart:'meds',
 book:'care',appts:'care',docs:'care',sos:'sos',aid:'sos',mid:'sos',contacts:'sos',dash:'alerts'})[typeof page!=='undefined'?page:'dash']||'labs';

// ---------------------------------------------------------------- B. the sheet the family sees once
const PIN=`<svg viewBox="0 0 160 140" class="lv32-art" aria-hidden="true">
 <circle cx="80" cy="66" r="52" class="lv32-ring1"/><circle cx="80" cy="66" r="40" class="lv32-ring2"/>
 <path d="M80 26c-15.5 0-28 12.3-28 27.5C52 74 80 104 80 104s28-30 28-50.5C108 38.3 95.5 26 80 26z" class="lv32-pin"/>
 <circle cx="80" cy="53" r="10.5" class="lv32-pinin"/>
 <circle cx="26" cy="34" r="6" class="lv32-dot a"/><circle cx="136" cy="44" r="5" class="lv32-dot b"/><circle cx="128" cy="100" r="7" class="lv32-dot a"/><circle cx="30" cy="96" r="4.5" class="lv32-dot b"/>
 <ellipse cx="80" cy="116" rx="30" ry="6" class="lv32-shadow"/></svg>`;

SX.locSheet=(opt={})=>new Promise(resolve=>{const p=perm(),ic=k=>(SX.ico&&SX.ico(k))||'';
 let done=false;const fin=v=>{if(done)return;done=true;resolve(v)};
 SX.modal(`<div class="lv32-ask">${PIN}
  <h2>${P('Allow your location')}</h2>
  <p class="lv32-lead">${opt.why||P('One permission, used across the app')} · ${P('Choose what it is used for. You can change any of this later in Settings.')}</p>
  <div class="lv32-mods">${MODULES().map(m=>`<label class="lv32-mod ${m.req?'req':''}">
    <span class="lv32-mi">${ic(m.ic)}</span><span class="grow"><b>${E(m.t)}${m.req?` <i class="lv32-req">${P('Required')}</i>`:''}</b><small>${E(m.s)}</small></span>
    <input type="checkbox" ${m.req||p.mod[m.k]!==false?'checked':''} ${m.req?'disabled':''} data-mod="${m.k}"><i class="lv32-sw"></i></label>`).join('')}</div>
  <button class="btn p lv32-go" id="lv32allow">${P('Allow location')}</button>
  <button class="lv32-later" id="lv32later">${P('Maybe later')}</button>
  <p class="lv32-fine">${P('Only while you use the app. Your position is never sold or shared with other families.')}</p></div>`,
  {cls:'lv32-m',label:P('Allow your location'),sticky:true,onclose:()=>fin(null)});
 document.querySelectorAll('.lv32-mod input[data-mod]').forEach(i=>i.onchange=()=>{p.mod[i.dataset.mod]=i.checked;SX.save()});
 document.getElementById('lv32later').onclick=()=>{p.later=Date.now();SX.save();SX.closeModal();fin(null)};
 document.getElementById('lv32allow').onclick=async()=>{const b=document.getElementById('lv32allow');b.disabled=true;b.textContent=P('Locating…');
  const f=await SX.loc.gps(12000);
  if(!f){b.disabled=false;b.textContent=P('Allow location');
   const e=document.querySelector('.lv32-ask .lv32-err')||Object.assign(document.createElement('p'),{className:'lv32-err'});
   e.textContent=P('Location is blocked in the browser. Allow it in site settings, or choose your area on the map.');
   if(!e.parentNode)document.querySelector('.lv32-ask').insertBefore(e,document.getElementById('lv32allow'));
   const pick=document.createElement('button');pick.className='btn s lv32-pickbtn';pick.textContent=P('Pick on the map');
   if(!document.querySelector('.lv32-pickbtn')){document.querySelector('.lv32-ask').insertBefore(pick,document.getElementById('lv32later'));
    pick.onclick=async()=>{SX.closeModal();const r=await SX.mapPick({title:P('Your location')});if(r){SX.loc.set(r.lat,r.lng,r.where,true);p.at=Date.now();SX.save();fin(SX.loc.get())}else fin(null)}}
   return}
  p.at=Date.now();p.denied=false;SX.save();
  const w=await SX.loc.resolve(f.lat,f.lng);SX.loc.set(f.lat,f.lng,w,false);
  SX.closeModal();toast('📍 '+(SX.loc.short()||P('Location set')));try{render()}catch(e){}fin(SX.loc.get())}});

// the one door: everything that wants a position goes through here
SX.needLoc=async(mod,opt={})=>{mod=mod||pageModule();
 const p=perm();
 if(!p.at)return await SX.locSheet(opt);
 if(mod!=='sos'&&p.mod[mod]===false){
  const go=await new Promise(res=>{SX.modal(`<div class="lv32-small">${PIN}<h2>${P('Location is off for this')}</h2>
   <p class="mute">${E((MODULES().find(m=>m.k===mod)||{}).s||'')}</p>
   <div class="lv-row-end"><button class="btn s" data-sx="closeModal">${P('Not now')}</button><button class="btn p" id="lv32on">${P('Turn it on')}</button></div></div>`,{label:P('Location'),onclose:()=>res(false)});
   document.getElementById('lv32on').onclick=()=>{p.mod[mod]=true;SX.save();SX.closeModal();res(true)}});
  if(!go)return null}
 const cur=SX.loc.get();
 if(cur&&(S.net.geoManual||Date.now()-(S.net.geo.t||0)<30*60e3))return cur;
 const f=await SX.loc.gps(9000);
 if(f){const w=await SX.loc.resolve(f.lat,f.lng);SX.loc.set(f.lat,f.lng,w,false);return SX.loc.get()}
 return cur};

// every old call site now flows through the one door, without touching any of them
const geo0=SX.geo;
SX.geo=async ask=>{if(!ask)return SX.loc.get()||await geo0(false);const g=await SX.needLoc();return g||SX.loc.get()};

// ---------------------------------------------------------------- C. one chip, everywhere
function chip(){const w=S.net.where,c=SX.loc.get(),live=!!(SX.sosLive&&SX.sosLive());
 return `<button class="lv32-chip ${c?'on':''} ${live?'live':''}" data-sx="locset" aria-label="${E(P('Location'))}">
  <i class="lv32-cp">${(SX.ico&&SX.ico('home'))||'📍'}</i><span>${c?E(SX.loc.short()||P('Located')):P('Set location')}</span>
  ${live?`<em class="lv32-livedot">${P('Live')}</em>`:'<b class="lv32-cv">⌄</b>'}</button>`}
SX.locChip=chip;
function paintChip(){const tb=document.querySelector('.topb');if(!tb)return;
 const old=document.getElementById('lv6Loc');if(old)old.remove();
 let a=document.getElementById('lv32chip');
 if(!a){a=document.createElement('div');a.id='lv32chip';tb.insertBefore(a,tb.firstChild)}
 const html=chip();if(a.dataset.h!==html){a.dataset.h=html;a.innerHTML=html}}
document.addEventListener('tht:location',paintChip);

// the card version, for Today and Book a test (replaces the round-29 one so there is a single look)
SX.locCard=()=>{const c=SX.loc.get(),w=S.net.where;
 return `<div class="lv32-card" data-lv29="loc"><div class="lv32-mini">${c&&SX.mapHTML?SX.mapHTML(c,[],{h:72,zoom:15}):''}${c?'<i class="lv32-dot2"></i>':''}</div>
  <div class="grow"><small>${P('Your location')}</small><b>${c?E(SX.loc.short()||P('Located')):P('Not set')}</b>
   <span class="mute sm">${c?E(w&&w.label?w.label:[w&&w.district,w&&w.state].filter(Boolean).join(', ')):P('Used by labs, pharmacies, doctors and SOS.')}</span></div>
  <button class="btn ${c?'s':'p'} sm" data-sx="locset">${c?P('Change'):P('Set')}</button></div>`};

// ---------------------------------------------------------------- D. Settings: the modules, and the mandatory one
SX.chg.locmod=(a,el)=>{const k=el.dataset.k;perm().mod[k]=el.checked;SX.save();toast(el.checked?P('Turn it on'):P('Location is off for this'))};
SX.extend('set',{before(){const p=perm(),c=SX.loc.get(),ic=k=>(SX.ico&&SX.ico(k))||'';
 return `<div class="card wide lv32-set"><div class="hd"><div><h3>📍 ${P('Location')}</h3><small class="mute">${c?E(SX.loc.text()||SX.loc.short()):P('Not set')}</small></div><button class="btn s sm" data-sx="locset">${c?P('Change'):P('Set')}</button></div>
  <div class="lv32-rows">${MODULES().map(m=>`<label class="lv32-row ${m.req?'req':''}"><span class="lv32-mi">${ic(m.ic)}</span>
   <span class="grow"><b>${E(m.t)}${m.req?` <i class="lv32-req">${P('Required')}</i>`:''}</b><small>${E(m.s)}</small></span>
   ${m.req?`<span class="lv32-lock">🔒</span>`:`<input type="checkbox" data-sxc="locmod" data-k="${m.k}" ${p.mod[m.k]!==false?'checked':''}><i class="lv32-sw"></i>`}</label>`).join('')}</div></div>`}});

// ---------------------------------------------------------------- E. SOS: location is not optional, and it stays live
SX.extend('sos',{before(){const p=perm(),ok=!!p.at&&!p.denied&&!!SX.loc.get();
 if(ok)return '';
 return `<div class="card wide lv32-sosneed"><div class="lv32-sn"><i>📍</i><div class="grow"><b>${P('SOS needs your location')}</b><small>${P('Your location goes to the people you chose, and to the live map they open. SOS cannot work without it.')}</small></div></div>
  <button class="btn p" data-sx="locask">${P('Fix it now')}</button></div>`}});
SX.act.locask=async()=>{await SX.needLoc('sos',{why:P('SOS needs your location')});try{render()}catch(e){}};

// live tracking while an alert is open: a real watch, not a poll
let watch=null,liveOn=false;
SX.sosLive=()=>liveOn;
SX.sosWatch=(on,onFix)=>{if(on===liveOn)return;liveOn=on;paintChip();
 if(!on){if(watch!==null&&navigator.geolocation)navigator.geolocation.clearWatch(watch);watch=null;return}
 if(!navigator.geolocation||SX.locOn('live')===false)return;
 try{watch=navigator.geolocation.watchPosition(p=>{const f={lat:+p.coords.latitude.toFixed(5),lng:+p.coords.longitude.toFixed(5),acc:Math.round(p.coords.accuracy||0)};
   SX.loc.set(f.lat,f.lng,S.net.where,false);if(onFix)onFix(f)},()=>{},{enableHighAccuracy:true,maximumAge:5000,timeout:20000})}catch(e){}};

setTimeout(()=>{paintChip();
 // first run: ask once, after the app has settled, and never twice in a day
 const p=perm();if(!p.at&&!(p.later&&Date.now()-p.later<864e5)&&SX.user)setTimeout(()=>{if(!perm().at)SX.locSheet()},2500)},900);
new MutationObserver(()=>{clearTimeout(window.__lv32t);window.__lv32t=setTimeout(paintChip,80)}).observe(document.body,{childList:true,subtree:true});
}
