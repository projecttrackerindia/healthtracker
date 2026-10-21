// ===================== live layer 34: places you can actually use — pick a lab, see it, book it, and stop the shaking =====================
// Three real faults, from a phone in Chennai: the Call/Directions buttons squeezed into vertical letters, selecting a
// place re-rendered the whole page (which rebuilt the Google map underneath — the shake), and a Google-listed lab had
// no way to book because only partner stores carry prices. A place is now a card you tap, a sheet you read, and a
// booking you can complete: with a partner, on their price list; with any other lab, by sending the list and calling.
{
const P=SX.p,S=SX.S;
const money=n=>'₹'+Math.round(+n||0).toLocaleString('en-IN');
const digits=s=>String(s||'').replace(/[^\d+]/g,'');

SX.addPhrases({
 'Open now':['अभी खुला है','ఇప్పుడు తెరిచి ఉంది'],
 'Closed now':['अभी बंद है','ఇప్పుడు మూసి ఉంది'],
 'Partner lab':['पार्टनर लैब','భాగస్వామి ల్యాబ్'],
 'Prices and booking in the app':['ऐप में क़ीमतें और बुकिंग','యాప్‌లో ధరలు, బుకింగ్'],
 'Book a test here':['यहाँ जाँच बुक करें','ఇక్కడ టెస్ట్ బుక్ చేయండి'],
 'Send the list and call':['सूची भेजें और कॉल करें','జాబితా పంపి కాల్ చేయండి'],
 'Pick the tests, send them on WhatsApp, then call to confirm the slot. We save it so the report lands back here.':
  ['जाँचें चुनें, WhatsApp पर भेजें, फिर स्लॉट पक्का करने के लिए कॉल करें। हम इसे सेव कर लेते हैं ताकि रिपोर्ट यहीं आए।',
   'టెస్టులు ఎంచుకోండి, WhatsAppలో పంపండి, స్లాట్ ఖరారుకు కాల్ చేయండి. రిపోర్ట్ ఇక్కడికే వచ్చేలా మేము సేవ్ చేస్తాం.'],
 'Which tests?':['कौन-सी जाँचें?','ఏ టెస్టులు?'],
 'Send on WhatsApp':['WhatsApp पर भेजें','WhatsAppలో పంపండి'],
 'Call the lab':['लैब को कॉल करें','ల్యాబ్‌కు కాల్ చేయండి'],
 'Save as planned':['योजना में सेव करें','ప్లాన్‌గా సేవ్ చేయండి'],
 'Planned at':['यहाँ नियोजित','ఇక్కడ ప్లాన్ చేయబడింది'],
 'Saved. It is on Book a test until the report arrives.':['सेव हो गया। रिपोर्ट आने तक यह “जाँच बुक करें” में दिखेगा।','సేవ్ అయింది. రిపోర్ట్ వచ్చే వరకు “టెస్ట్ బుక్” లో ఉంటుంది.'],
 'Planned tests':['नियोजित जाँचें','ప్లాన్ చేసిన టెస్టులు'],
 'Mark done':['पूरा हुआ','పూర్తయింది'],
 'Remove':['हटाएँ','తీసివేయండి'],
 'Map':['मैप','మ్యాప్'],
 'Call':['कॉल','కాల్'],
 'Directions':['रास्ता','దారి'],
 'No number listed':['नंबर उपलब्ध नहीं','నంబర్ లేదు'],
 'Hours':['समय','సమయాలు']});

// ---------------------------------------------------------------- A. the place sheet
const PL=()=>{try{return (SX.placesData&&SX.placesData())||{}}catch(e){return {}}};
const FB={};
function findPlace(id){if(FB[id])return FB[id];const d=PL();for(const k in d){const x=[...((d[k]||{}).partners||[]),...((d[k]||{}).places||[])].find(p=>String(p.id)===String(id));if(x)return x}return null}
SX.act.plopen=([id])=>{const p=findPlace(decodeURIComponent(id));if(p)SX.placeSheet(p)};
SX.placeSheet=p=>{const openNow=p.open===true?`<span class="lv34-open">● ${P('Open now')}</span>`:p.open===false?`<span class="lv34-shut">● ${P('Closed now')}</span>`:'';
 const hrs=(p.hours||'').split(';').map(s=>s.trim()).filter(Boolean);
 SX.modal(`<div class="lv34-sheet">
  <div class="lv34-top"><div class="grow"><h2>${E(p.name)}</h2>
   <p class="lv34-meta">${[p.km!=null?p.km+' km':'',p.rating?'★ '+p.rating+(p.ratings?' ('+p.ratings+')':''):''].filter(Boolean).join(' · ')} ${openNow}</p></div>
   ${p.partner?`<span class="lv34-badge">${P('Partner lab')}</span>`:''}</div>
  ${p.address?`<p class="lv34-addr">${E(p.address)}</p>`:''}
  ${hrs.length?`<details class="lv34-hrs"><summary>${P('Hours')}</summary><ul>${hrs.map(h=>`<li>${E(h)}</li>`).join('')}</ul></details>`:''}
  <div class="lv34-acts">
   <button class="btn p lv34-book" data-sx="plbook:${encodeURIComponent(p.id)}">${p.partner?P('Book a test here'):P('Book a test here')}</button>
   <div class="lv34-row2">${p.phone?`<a class="btn s" href="tel:${E(digits(p.phone))}">📞 ${P('Call')}</a>`:`<span class="btn s" aria-disabled="true">${P('No number listed')}</span>`}
    <a class="btn s" href="https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lng}" target="_blank" rel="noopener">🧭 ${P('Directions')}</a>
    <button class="btn s" data-sx="plmap:${encodeURIComponent(p.id)}">🗺️ ${P('Map')}</button></div></div>
  ${p.partner?`<p class="lv34-note">${P('Prices and booking in the app')}</p>`:`<p class="lv34-note">${P('Pick the tests, send them on WhatsApp, then call to confirm the slot. We save it so the report lands back here.')}</p>`}
 </div>`,{label:p.name,cls:'lv34-m'})};
SX.act.plmap=([id])=>{SX.closeModal();SX.act.mapsel([id])};

// ---------------------------------------------------------------- B. booking at any lab, partner or not
SX.act.plbook=([id])=>{const p=findPlace(decodeURIComponent(id));if(!p)return;SX.closeModal();
 if(p.partner&&SX.labOpen)return SX.labOpen(['cbc','lipid','hba1c'],p.id);
 pickTests(p)};
async function pickTests(p){let T=(SX.labCatalogue&&SX.labCatalogue())||[];
 if(!T.length){try{const r=await SX.api('/labs/tests',{silent:true});T=r.tests||[]}catch(e){T=[]}}let sel=[];
 const body=()=>`<div class="lv34-pick"><h2>${P('Which tests?')}</h2><p class="mute sm">${E(p.name)}${p.km!=null?' · '+p.km+' km':''}</p>
  <div class="lv34-tests">${T.map(t=>`<button type="button" class="lv34-t ${sel.includes(t.code)?'on':''}" data-t="${t.code}"><span>${E(t.name)}</span><i>${money(t.typical)}</i></button>`).join('')}</div>
  <div class="lv34-sum"><b>${sel.length} ${sel.length===1?P('test'):P('tests')}</b><span>${P('about')} ${money(T.filter(t=>sel.includes(t.code)).reduce((a,t)=>a+t.typical,0))}</span></div>
  <div class="lv34-acts"><button class="btn p" id="lv34wa" ${sel.length?'':'disabled'}>${P('Send on WhatsApp')}</button>
   <div class="lv34-row2">${p.phone?`<a class="btn s" href="tel:${E(digits(p.phone))}">📞 ${P('Call the lab')}</a>`:''}<button class="btn s" id="lv34save" ${sel.length?'':'disabled'}>${P('Save as planned')}</button></div></div></div>`;
 const wire=()=>{document.querySelectorAll('.lv34-t').forEach(b=>b.onclick=()=>{const c=b.dataset.t;sel=sel.includes(c)?sel.filter(x=>x!==c):sel.concat([c]);paint()});
  const wa=document.getElementById('lv34wa');if(wa)wa.onclick=()=>send(p,sel,T);
  const sv=document.getElementById('lv34save');if(sv)sv.onclick=()=>{plan(p,sel,T);SX.closeModal();toast(P('Saved. It is on Book a test until the report arrives.'));try{render()}catch(e){}}};
 const paint=()=>{const w=document.querySelector('.sx-modal .sx-sheet');if(!w)return;w.innerHTML=body();wire()};
 SX.modal(body(),{label:P('Which tests?'),cls:'lv34-m'});wire()}
function msg(p,sel,T){const m=SX.me(),names=T.filter(t=>sel.includes(t.code)).map(t=>'• '+t.name);
 return [`Hello ${p.name},`,'',`I would like to book these tests${m?' for '+m.name:''}:`,...names,'',
  S.net.where?`Area: ${[S.net.where.place,S.net.where.city].filter(Boolean).join(', ')}`:'',
  'Please tell me the price, the slot and whether home collection is possible.','',`Sent from Urban Health`].filter(Boolean).join('\n')}
function send(p,sel,T){const t=encodeURIComponent(msg(p,sel,T));const n=digits(p.phone);
 plan(p,sel,T);
 const url=n?`https://wa.me/${n.replace(/^\+/,'')}?text=${t}`:`https://wa.me/?text=${t}`;
 try{window.open(url,'_blank','noopener')}catch(e){location.href=url}
 SX.closeModal();toast(P('Saved. It is on Book a test until the report arrives.'));try{render()}catch(e){}}
function plan(p,sel,T){const m=SX.me();S.labPlan=S.labPlan||{};const list=S.labPlan[m.id]=S.labPlan[m.id]||[];
 list.unshift({id:'lp'+Math.random().toString(36).slice(2,8),t:Date.now(),lab:p.name,phone:p.phone||'',lat:p.lat,lng:p.lng,
  codes:sel.slice(),names:T.filter(x=>sel.includes(x.code)).map(x=>x.name),est:T.filter(x=>sel.includes(x.code)).reduce((a,x)=>a+x.typical,0)});
 list.length=Math.min(list.length,12);SX.ledger&&SX.ledger('labplan',true,'Planned tests at '+p.name,m.id);SX.save()}
SX.act.lpdone=([id])=>{const m=SX.me();S.labPlan[m.id]=(S.labPlan[m.id]||[]).filter(x=>x.id!==id);SX.save();render();toast(P('Mark done'))};
SX.act.lpcall=([id])=>{const m=SX.me(),x=(S.labPlan[m.id]||[]).find(a=>a.id===id);if(x&&x.phone)location.href='tel:'+digits(x.phone)};

// the planned tests sit at the top of Book a test until the report arrives
SX.extend('labshop',{before(){const m=SX.me(),list=(S.labPlan&&S.labPlan[m.id])||[];if(!list.length)return '';
 return `<div class="card wide lv34-plan"><div class="hd"><div><h3>${P('Planned tests')}</h3><small class="mute">${P('Saved. It is on Book a test until the report arrives.')}</small></div></div>
  ${list.map(x=>`<div class="lv34-prow"><div class="grow"><b>${E(x.lab)}</b><small>${E(x.names.slice(0,4).join(' · '))}${x.names.length>4?' +'+(x.names.length-4):''}${x.est?' · '+P('about')+' '+money(x.est):''}</small></div>
   ${x.phone?`<button class="btn s sm" data-sx="lpcall:${x.id}">📞</button>`:''}<button class="btn s sm" data-sx="lpdone:${x.id}">${P('Mark done')}</button></div>`).join('')}</div>`}});

// ---------------------------------------------------------------- C. the row itself: tappable, readable, with buttons that never collapse
function rows(){document.querySelectorAll('.lv6-pl').forEach(r=>{if(r.dataset.lv34)return;r.dataset.lv34='1';
 const acts=r.querySelector('.lv6-pla');if(!acts)return;
 const id=(r.dataset.sx||'').replace(/^mapsel:/,'');
 const p=findPlace(decodeURIComponent(id));
 // one primary action on the row; everything else lives in the sheet
 acts.innerHTML=`<button class="btn p sm lv34-rb" data-sx="plopen:${id}">${P('Book')}</button>`;
 if(p){const small=r.querySelector('small');if(small&&p.open!==undefined&&!small.dataset.lv34){small.dataset.lv34='1';
  small.insertAdjacentHTML('beforeend',p.open===true?` · <b class="lv34-open">${P('Open now')}</b>`:p.open===false?` · <b class="lv34-shut">${P('Closed now')}</b>`:'')}}})}

// ---------------------------------------------------------------- D. selecting a place must not rebuild the page (that was the shake)
if(typeof SX.act.mapsel==='function'){
 SX.act.mapsel=([id])=>{const v=decodeURIComponent(id);
  try{if(SX.setPlSel)SX.setPlSel(v)}catch(e){}
  document.querySelectorAll('.lv6-pl').forEach(r=>r.classList.toggle('on',decodeURIComponent((r.dataset.sx||'').replace(/^mapsel:/,''))===v));
  document.querySelectorAll('.lv6-pin').forEach(b=>b.classList.toggle('on',decodeURIComponent((b.dataset.sx||'').split(':').slice(1).join(':'))===v));
  const el=document.querySelector('.lv6-pl.on');if(el)el.scrollIntoView({block:'nearest',behavior:'smooth'});
  const p=findPlace(v);if(p&&SX.gmapPan)SX.gmapPan(p)};
}
// and nothing repaints while a finger is on the screen
let scrolling=0;
addEventListener('scroll',()=>{scrolling=Date.now();document.body.classList.add('lv34-scroll');clearTimeout(window.__lv34s);
 window.__lv34s=setTimeout(()=>document.body.classList.remove('lv34-scroll'),180)},{passive:true,capture:true});
SX.busyScroll=()=>Date.now()-scrolling<180;
new MutationObserver(()=>{clearTimeout(window.__lv34t);window.__lv34t=setTimeout(()=>{if(SX.busyScroll())return;rows()},90)}).observe(document.body,{childList:true,subtree:true});
setTimeout(rows,800);


// ---------------------------------------------------------------- E. a lab list that is never empty
// /labs/quotes only knows partner stores. Where we have no partner yet the sheet came back blank — prices,
// no labs, no way to book. Fall back to the labs Google actually lists near the person and let them book those.
if(SX.labSheetHook){
 SX.labSheetHook(()=>{
  const L=SX.labQuotes?SX.labQuotes():null;
  if(!L||L.error||(L.labs&&L.labs.length))return;
  const w=document.querySelector('.sx-modal');if(!w||w.querySelector('.lv34-fb'))return;
  const anchor=w.querySelector('.sx-disc')||w.lastElementChild;
  anchor.insertAdjacentHTML('beforebegin',`<div class="lv34-fb"><p class="sx-h4" style="margin:4px 0 6px">${P('Labs near you')}</p><div class="lv34-fbl"><div class="sx-livel"><div class="sx-spin sm"></div> ${P('Finding labs…')}</div></div></div>`);
  fbLabs(w.querySelector('.lv34-fbl'))})}

async function fbLabs(box){if(!box)return;
 let g=null;try{g=await SX.geo(false)}catch(e){}
 if(!g){box.innerHTML=`<p class="mute sm">${P('Share your location to see labs near you.')}</p>`;return}
 let r=null;try{r=await SX.api(`/places?kind=lab&lat=${g.lat}&lng=${g.lng}&radius=6000`,{silent:true})}catch(e){}
 const list=((r&&r.places)||[]).concat((r&&r.partners)||[]).sort((a,b)=>a.km-b.km).slice(0,6);
 if(!list.length){box.innerHTML=`<p class="mute sm">${P('No labs listed near you yet. Try a wider area, or call a lab you know.')}</p>`;return}
 box.innerHTML=list.map(l=>`<button class="lv34-fbr" data-lv34="${E(l.id)}"><div class="grow"><b>${E(l.name)}</b><small>${l.km} km${l.rating?' · ★ '+l.rating:''}${l.open===true?' · <i class="lv34-open">'+P('Open now')+'</i>':l.open===false?' · <i class="lv34-shut">'+P('Closed now')+'</i>':''}</small></div><span class="btn p sm">${P('Book')}</span></button>`).join('')
  +`<p class="mute sm" style="margin:8px 0 0">${P('These labs are not partners yet, so we cannot hold the price. Pick your tests and we will send them the list — they confirm the amount.')}</p>`;
 list.forEach(l=>FB[l.id]=l);
 box.querySelectorAll('[data-lv34]').forEach(b=>b.onclick=()=>{const l=list.find(x=>String(x.id)===b.dataset.lv34);if(!l)return;SX.closeModal();pickTests(l)})}

}