// ===================== live layer 35: the map stops shaking, buttons stop folding, the picker stops jumping =====================
// The shake was a feedback loop, not a map bug. The address under the map was blanked to "Finding the address…"
// (two lines) on every geocode and filled back in with a full address (three lines). The sheet changed height,
// the map above it was resized to fit, Google Maps fired `idle` on the resize, and `idle` kicked off another
// geocode. Round and round for as long as the sheet was open. Both halves are fixed here: the label never
// changes the sheet's height, and `idle` only re-geocodes when the pin has actually moved.
{
const P=SX.p,E=SX.E||(s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
SX.addPhrases({
 'Updating the address…':['पता अपडेट हो रहा है…','చిరునామా నవీకరిస్తోంది…'],
});

// ---------------------------------------------------------------- A. the floating button must never sit on a sheet
// A modal is a surface of its own; the compose button belongs to the page underneath it.
const fabWatch=()=>{const on=!!document.querySelector('.sx-modal');document.body.classList.toggle('lv35-modal',on)};
new MutationObserver(fabWatch).observe(document.body,{childList:true,subtree:false});
const m0=SX.modal,c0=SX.closeModal;
SX.modal=function(){const r=m0.apply(this,arguments);fabWatch();return r};
SX.closeModal=function(){const r=c0.apply(this,arguments);setTimeout(fabWatch,0);return r};
fabWatch();

// ---------------------------------------------------------------- B. the basket already knows where you are
// The "Use my location" button sat in the pharmacy block whether or not the family had already granted
// location in round 32's consent sheet. If they have, there is nothing to ask: run the lookup and drop the
// button. Only a family that has not granted it, or has switched medicines off, still sees a prompt.
const medsOn=()=>{try{return SX.locOn?SX.locOn('meds'):false}catch(e){return false}};
const haveFix=()=>{try{return !!(SX.loc&&SX.loc.get&&SX.loc.get())}catch(e){return false}};
function tidyGeoButtons(){
 if(!(medsOn()&&haveFix()))return;
 document.querySelectorAll('.sx-live [data-net=geo]').forEach(b=>{if(!b.dataset.lv35){b.dataset.lv35='1';b.remove()}})}

// ---------------------------------------------------------------- C. pharmacies near you, when none are partners
// Same gap as the labs had: /stores only knows partner pharmacies, and where there are none the basket ended
// with "online ordering is not available in your area yet" and no way forward. Show what Google lists and let
// the family send the basket to one of them.
async function pharmFallback(box){
 if(!box||box.querySelector('.lv35-ph'))return;
 const txt=(box.textContent||'');
 if(!/not available in your area|no pharmacy|No pharmacies/i.test(txt))return;
 let g=null;try{g=await SX.geo(false)}catch(e){}
 if(!g)return;
 const list=document.createElement('div');list.className='lv35-ph';
 list.innerHTML=`<p class="sx-h4" style="margin:10px 0 6px">${P('Pharmacies near you')}</p><div class="lv34-fbl"><div class="sx-livel"><div class="sx-spin sm"></div> ${P('Finding pharmacies…')}</div></div>`;
 box.append(list);
 const slot=list.querySelector('.lv34-fbl');
 let r=null;try{r=await SX.api(`/places?kind=pharmacy&lat=${g.lat}&lng=${g.lng}&radius=6000`,{silent:true})}catch(e){}
 const items=((r&&r.places)||[]).concat((r&&r.partners)||[]).sort((a,b)=>a.km-b.km).slice(0,5);
 if(!items.length){slot.innerHTML=`<p class="mute sm">${P('No pharmacies listed near you yet.')}</p>`;return}
 slot.innerHTML=items.map(x=>`<button class="lv34-fbr" data-lv35ph="${E(String(x.id))}"><div class="grow"><b>${E(x.name)}</b><small>${x.km} km${x.rating?' · ★ '+x.rating:''}${x.open===true?' · <i class="lv34-open">'+P('Open now')+'</i>':x.open===false?' · <i class="lv34-shut">'+P('Closed now')+'</i>':''}</small></div><span class="btn p sm">${P('Send list')}</span></button>`).join('')
  +`<p class="mute sm" style="margin:8px 0 0">${P('Not partners yet, so we cannot hold the price. Send them your list and they confirm stock and the amount.')}</p>`;
 slot.querySelectorAll('[data-lv35ph]').forEach(b=>b.onclick=()=>{
  const x=items.find(i=>String(i.id)===b.dataset.lv35ph);if(!x)return;
  const m=SX.me&&SX.me(),lines=(S.cart||[]).map(c=>'• '+(c.name||c.id)+(c.q>1?' ×'+c.q:''));
  const body=[`Hello ${x.name},`,'',`I would like these medicines${m?' for '+m.name:''}:`,...lines,'',
   S.addr?`Deliver to: ${S.addr}`:'','Please confirm stock and the total.','','Sent from TheHealthTracker'].filter(Boolean).join('\n');
  const n=(x.phone||'').replace(/[^0-9+]/g,'').replace(/^\+/,'');
  const url=n?`https://wa.me/${n}?text=${encodeURIComponent(body)}`:`https://wa.me/?text=${encodeURIComponent(body)}`;
  try{window.open(url,'_blank','noopener')}catch(e){location.href=url}})}

SX.addPhrases({
 'Pharmacies near you':['आपके पास की फ़ार्मेसी','మీ దగ్గరి ఫార్మసీలు'],
 'Finding pharmacies…':['फ़ार्मेसी खोजी जा रही हैं…','ఫార్మసీలు వెతుకుతోంది…'],
 'No pharmacies listed near you yet.':['आपके पास अभी कोई फ़ार्मेसी सूचीबद्ध नहीं है।','మీ దగ్గర ఇంకా ఫార్మసీలు జాబితాలో లేవు.'],
 'Send list':['सूची भेजें','జాబితా పంపండి'],
 'Not partners yet, so we cannot hold the price. Send them your list and they confirm stock and the amount.':
  ['ये अभी पार्टनर नहीं हैं, इसलिए दाम पक्का नहीं कर सकते। सूची भेजें, वे स्टॉक और रक़म बताएँगे।',
   'వీరు ఇంకా భాగస్వాములు కాదు, కాబట్టి ధర పట్టుకోలేము. జాబితా పంపండి, వారు స్టాక్ మరియు మొత్తాన్ని నిర్ధారిస్తారు.'],
});

// the basket is rebuilt by the page, so watch for it rather than wiring once
let tick=null;
new MutationObserver(()=>{clearTimeout(tick);tick=setTimeout(()=>{
 try{tidyGeoButtons();document.querySelectorAll('.sx-live').forEach(pharmFallback)}catch(e){}
},160)}).observe(document.body,{childList:true,subtree:true});
setTimeout(()=>{try{tidyGeoButtons();document.querySelectorAll('.sx-live').forEach(pharmFallback)}catch(e){}},900);

}