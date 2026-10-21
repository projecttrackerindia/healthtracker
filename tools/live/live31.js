// ===================== live layer 31: the shop comes first — Book a test, Order medicines, and every suggestion ends in a basket =====================
// Three engines were already in the app and none of them ended anywhere you could buy: the checks-due engine stopped at
// advice, the lab price comparison was reachable only from a buried sheet, and "Reorder" dropped a word into a search box.
// This layer puts the shop at the front of Tests & records and Medicines, and wires all three into the basket.
{
const P=SX.p,S=SX.S;
const money=n=>'₹'+Math.round(+n||0).toLocaleString('en-IN');

SX.addPhrases({
 'Book a test':['जाँच बुक करें','టెస్ట్ బుక్ చేయండి'],
 'Order medicines':['दवाइयाँ मँगाएँ','మందులు ఆర్డర్ చేయండి'],
 'Due for':['के लिए अभी ज़रूरी','వీరికి ఇప్పుడు అవసరం'],
 'Based on age, sex, conditions and past results. Not a diagnosis — your doctor knows your full history.':
  ['उम्र, लिंग, स्थितियों और पिछले नतीजों के आधार पर। यह निदान नहीं है — आपके डॉक्टर को पूरा इतिहास पता है।',
   'వయస్సు, లింగం, పరిస్థితులు, గత ఫలితాల ఆధారంగా. ఇది రోగ నిర్ధారణ కాదు — మీ డాక్టర్‌కు పూర్తి చరిత్ర తెలుసు.'],
 'Nothing is due right now':['अभी कुछ ज़रूरी नहीं है','ఇప్పుడు ఏదీ అవసరం లేదు'],
 'Your checks are up to date. Book anything else below.':['आपकी जाँचें अप-टू-डेट हैं। नीचे से कुछ और बुक करें।','మీ చెకప్‌లు తాజాగా ఉన్నాయి. కింద నుండి ఇంకేదైనా బుక్ చేయండి.'],
 'Book':['बुक करें','బుక్ చేయండి'],
 'from':['से','నుండి'],
 'Popular packages':['लोकप्रिय पैकेज','ప్రసిద్ధ ప్యాకేజీలు'],
 'Panels families book most often.':['परिवार सबसे ज़्यादा यही पैकेज बुक करते हैं।','కుటుంబాలు ఎక్కువగా బుక్ చేసే ప్యానెల్స్.'],
 'tests':['जाँचें','టెస్టులు'],
 'test':['जाँच','టెస్ట్'],
 'about':['लगभग','సుమారు'],
 'Typical prices. The labs near you quote the real price before you confirm.':['सामान्य क़ीमतें। पास की लैब पक्का करने से पहले असली क़ीमत बताती हैं।','సాధారణ ధరలు. మీ దగ్గరి ల్యాబ్‌లు నిర్ధారణకు ముందు అసలు ధర చెబుతాయి.'],
 'Thyroid profile (T3, T4, TSH)':['थायरॉइड प्रोफ़ाइल (T3, T4, TSH)','థైరాయిడ్ ప్రొఫైల్ (T3, T4, TSH)'],
 'Search tests':['जाँच खोजें','టెస్టులు వెతకండి'],
 'e.g. thyroid, HbA1c, vitamin D':['जैसे थायरॉइड, HbA1c, विटामिन D','ఉదా. థైరాయిడ్, HbA1c, విటమిన్ D'],
 'Selected':['चुनी गई','ఎంచుకున్నవి'],
 'Get prices':['क़ीमतें देखें','ధరలు చూడండి'],
 'Clear':['हटाएँ','తొలగించు'],
 'fasting':['खाली पेट','ఖాళీ కడుపుతో'],
 'Reports come back into the vault':['रिपोर्ट सीधे वॉल्ट में आती है','రిపోర్టులు నేరుగా వాల్ట్‌కు వస్తాయి'],
 'Partner labs send the report straight into the app, where it is explained in plain words and added to the trends.':
  ['पार्टनर लैब रिपोर्ट सीधे ऐप में भेजती है, जहाँ वह आसान भाषा में समझाई जाती है और ट्रेंड में जुड़ जाती है।',
   'భాగస్వామి ల్యాబ్‌లు రిపోర్టును నేరుగా యాప్‌కు పంపుతాయి, అక్కడ సులభ భాషలో వివరించి ట్రెండ్‌లలో చేరుస్తాం.'],
 'Reorder':['फिर से मँगाएँ','మళ్లీ ఆర్డర్'],
 'Added to the basket':['बास्केट में जोड़ा गया','బాస్కెట్‌లో చేర్చబడింది'],
 'Full body checkup':['फुल बॉडी चेकअप','ఫుల్ బాడీ చెకప్'],
 'Diabetes panel':['डायबिटीज़ पैनल','డయాబెటిస్ ప్యానెల్'],
 'Heart and cholesterol':['हृदय और कोलेस्ट्रॉल','గుండె మరియు కొలెస్ట్రాల్'],
 'Thyroid':['थायरॉइड','థైరాయిడ్'],
 'Anaemia and vitamins':['एनीमिया और विटामिन','రక్తహీనత మరియు విటమిన్లు'],
 'Pregnancy — first visit':['गर्भावस्था — पहली जाँच','గర్భం — మొదటి విజిట్'],
 'Seniors — yearly':['बुज़ुर्गों के लिए — सालाना','పెద్దలకు — వార్షికం'],
 'Kidney and liver':['किडनी और लिवर','కిడ్నీ మరియు కాలేయం']});

// ---------------------------------------------------------------- A. the shop goes first in both groups
{const rec=SX.G.find(g=>g.k==='records');
 if(rec){rec.tabs=['labshop','tests','vault','insights'].filter(t=>t==='labshop'||rec.tabs.includes(t)||t==='tests'||t==='vault'||t==='insights')}
 const med=SX.G.find(g=>g.k==='meds');
 if(med&&med.tabs.includes('finder'))med.tabs=['finder','rx','orders'].filter(t=>med.tabs.includes(t));
 SX.addStrings&&SX.addStrings({'tab.labshop':SX.D('Book a test','जाँच बुक करें','టెస్ట్ బుక్'),
  'tab.tests':SX.D('My reports','मेरी रिपोर्ट','నా రిపోర్టులు'),'tab.finder':SX.D('Order','मँगाएँ','ఆర్డర్'),
  'tab.rx':SX.D('My medicines','मेरी दवाइयाँ','నా మందులు')});}

// ---------------------------------------------------------------- B. a suggestion that can be booked knows which tests it means
const TESTMAP={lipid:['lipid'],sugar:['hba1c','glu_f'],hb:['cbc'],hb2:['cbc','ferr'],tsh:['tsh'],vitd:['vitd'],
 kidney:['kft','urine'],liver:['lft','usg'],psa:['psa'],cervix:['pap'],'p-early':['cbc','tsh','glu_f','urine'],'p-ogtt':['ogtt'],'p-anom':['usg'],thy:['thy'],b12:['b12']};
const PACKS=()=>[
 {k:'full',t:P('Full body checkup'),codes:['cbc','lipid','lft','kft','tsh','glu_f','urine','vitd'],sub:P('Blood count, sugar, cholesterol, thyroid, kidney, liver, vitamin D, urine')},
 {k:'dia',t:P('Diabetes panel'),codes:['hba1c','glu_f','glu_pp','kft','lipid'],sub:P('HbA1c, fasting and post-meal sugar, kidney, cholesterol')},
 {k:'heart',t:P('Heart and cholesterol'),codes:['lipid','ecg','echo'],sub:P('Lipid profile, ECG, echo')},
 {k:'thy',t:P('Thyroid'),codes:['thy','tsh'],sub:P('Thyroid profile (T3, T4, TSH)')},
 {k:'anae',t:P('Anaemia and vitamins'),codes:['cbc','iron','b12','vitd'],sub:P('Blood count, iron, B12, vitamin D')},
 {k:'preg',t:P('Pregnancy — first visit'),codes:['cbc','tsh','glu_f','urine'],sub:P('Blood count, thyroid, sugar, urine')},
 {k:'sr',t:P('Seniors — yearly'),codes:['cbc','lipid','kft','lft','tsh','vitd','b12','urine','ecg'],sub:P('The yearly set, with ECG')},
 {k:'kl',t:P('Kidney and liver'),codes:['kft','lft','urine'],sub:P('Creatinine, urea, liver enzymes, urine')}];

let TESTS=null,pick=[],q='';
const have=c=>!TESTS||TESTS.some(t=>t.code===c);
const nameOf=c=>{const t=TESTS&&TESTS.find(x=>x.code===c);return t?t.name:c.toUpperCase()};
const typical=codes=>codes.reduce((a,c)=>{const t=TESTS&&TESTS.find(x=>x.code===c);return a+(t?t.typical:0)},0);
SX.labTestsHave=have;
async function loadTests(){if(TESTS)return TESTS;try{const r=await SX.api('/labs/tests',{silent:true});TESTS=r.tests||[]}catch(e){TESTS=[]}return TESTS}
const open=(codes,sel)=>{const cs=(codes||[]).filter(have);if(!cs.length)return toast(P('Nothing found. Try the city name or PIN.'));SX.labOpen?SX.labOpen(cs,sel):SX.act.labs([cs.join('+')])};
SX.act.labbook=a=>open(String(a[0]||'').split('+'),a[1]);
SX.act.labpack=([k])=>{const p=PACKS().find(x=>x.k===k);if(p)open(p.codes)};
SX.act.labpick=([c])=>{pick=pick.includes(c)?pick.filter(x=>x!==c):pick.concat([c]);render()};
SX.act.labclear=()=>{pick=[];render()};
SX.act.labgo2=()=>{if(pick.length)open(pick)};

// ---------------------------------------------------------------- C. the Book a test page
function dueRows(m){const sug=(SX.suggestions?SX.suggestions(m):[]).filter(s=>s.st!=='ok');
 const rows=sug.map(s=>({s,codes:(TESTMAP[s.id]||[]).filter(have)})).filter(x=>x.codes.length);
 if(!rows.length)return `<div class="lv31-none"><b>${P('Nothing is due right now')}</b><small>${P('Your checks are up to date. Book anything else below.')}</small></div>`;
 return rows.map(({s,codes})=>`<div class="lv31-row"><div class="grow"><b>${E(s.t)}</b><small>${E((s.why||'').slice(0,120))}</small>
  <span class="lv31-codes">${codes.map(c=>E(nameOf(c))).join(' · ')}${typical(codes)?' · '+P('about')+' '+money(typical(codes)):''}</span></div>
  <button class="btn p sm" data-sx="labbook:${codes.join('+')}">${P('Book')}</button></div>`).join('')}

function packRows(){return PACKS().map(p=>{const cs=p.codes.filter(have);if(!cs.length)return '';
 return `<button class="lv31-pack" data-sx="labpack:${p.k}"><b>${E(p.t)}</b><small>${E(p.sub)}</small><span>${cs.length} ${cs.length===1?P('test'):P('tests')} · ${P('about')} ${money(typical(cs))}</span></button>`}).join('')}

function searchRows(){const list=(TESTS||[]).filter(t=>!q||(t.name+' '+t.code).toLowerCase().includes(q.toLowerCase())).slice(0,40);
 return list.map(t=>`<button class="lv31-test ${pick.includes(t.code)?'on':''}" data-sx="labpick:${t.code}"><span class="grow"><b>${E(t.name)}</b>${t.fasting?`<small>${P('fasting')}</small>`:''}</span><i>${money(t.typical)}</i></button>`).join('')||`<p class="mute sm">${P('Nothing found. Try the city name or PIN.')}</p>`}

SX.reg('labshop',{
 head:()=>[P('Book a test'),P('Prices from labs near you, home collection, and the report back in the app.')],
 render(){const m=SX.me();
  return `<div class="card wide lv31-due"><div class="hd"><div><h3>${P('Due for')} ${E(m.name.split(' ')[0])}</h3><small class="mute">${P('Based on age, sex, conditions and past results. Not a diagnosis — your doctor knows your full history.')}</small></div></div>${dueRows(m)}</div>
  <div class="card wide"><div class="hd"><div><h3>${P('Popular packages')}</h3><small class="mute">${P('Panels families book most often.')} ${P('Typical prices. The labs near you quote the real price before you confirm.')}</small></div></div><div class="lv31-packs">${packRows()}</div></div>
  <div class="card wide"><div class="hd"><h3>${P('Search tests')}</h3>${pick.length?`<span class="lv31-sel">${P('Selected')}: ${pick.length}</span>`:''}</div>
   <input id="lv31q" type="search" placeholder="${E(P('e.g. thyroid, HbA1c, vitamin D'))}" value="${E(q)}" autocomplete="off">
   <div class="lv31-tests">${searchRows()}</div>
   ${pick.length?`<div class="lv31-bar"><button class="btn s sm" data-sx="labclear">${P('Clear')}</button><button class="btn p" data-sx="labgo2">${P('Get prices')} · ${pick.length}</button></div>`:''}</div>
  <div class="card wide lv31-note"><b>${P('Reports come back into the vault')}</b><p class="mute sm">${P('Partner labs send the report straight into the app, where it is explained in plain words and added to the trends.')}</p></div>
  ${SX.placesHTML?SX.placesHTML('lab',P('Labs near you'),{partnerAct:'labgo',partnerCta:P('Prices & book')}):''}`},
 after(){const i=document.getElementById('lv31q');if(i){i.oninput=()=>{q=i.value;const box=document.querySelector('.lv31-tests');if(box)box.innerHTML=searchRows()}}
  if(!TESTS)loadTests().then(()=>{if(page==='labshop')render()})}});

// a partner lab card now opens the price sheet with that lab chosen, instead of the old results page
SX.act.labgo=([id])=>{const m=SX.me(),sug=(SX.suggestions?SX.suggestions(m):[]).filter(s=>s.st!=='ok');
 const codes=[].concat(...sug.map(s=>(TESTMAP[s.id]||[]))).filter(have);
 open(codes.length?[...new Set(codes)].slice(0,6):['cbc','lipid','hba1c'],id)};

// the checks-due list on Insights gets the same button
SX.extend('insights',{mounted(){document.querySelectorAll('#page .sx-sugb').forEach(box=>{if(box.dataset.lv31)return;box.dataset.lv31='1';
  const b=box.querySelector('[data-sx^="sugbook:"]');const id=b&&b.dataset.sx.split(':')[1];const codes=(TESTMAP[id]||[]).filter(have);
  if(!codes.length)return;const n=document.createElement('button');n.className='btn p sm';n.dataset.sx='labbook:'+codes.join('+');n.textContent=P('Book');box.prepend(n)})}});

// ---------------------------------------------------------------- D. Reorder puts the medicine in the basket instead of a search box
SX.act.refill=([id])=>{const m=SX.me(),x=(S.meds[m.id]||[]).find(a=>a.id===id);if(!x)return;
 const C=SX.medCatalog?SX.medCatalog():[];const n=(x.n||'').toLowerCase(),gen=(x.gen||'').toLowerCase();
 const hit=C.find(c=>c.n.toLowerCase()===n)||C.find(c=>n.includes(c.n.toLowerCase())||c.n.toLowerCase().includes(n.split(' ')[0]))||(gen?C.find(c=>(c.gen||'').toLowerCase().includes(gen)):null);
 if(hit){try{SX.act.cartadd([hit.id]);toast(P('Added to the basket')+' · '+hit.n);SX.act.cart&&SX.act.cart();return}catch(e){}}
 if(SX.fsearch)SX.fsearch(x.n);else go('finder')};

// the running-low card belongs on the order page too, where the basket is
SX.extend('finder',{before(){const m=SX.me(),low=(S.meds[m.id]||[]).map(x=>({x,d:SX.medDaysLeft?SX.medDaysLeft(x):null})).filter(o=>o.d!==null&&o.d<=7).sort((a,b)=>a.d-b.d);
 if(!low.length)return '';
 return `<div class="card lv24-low"><div class="hd"><div><h3>${P('Running low')}</h3><small class="mute">${P('Counted from the doses ticked each day. Order a refill before it runs out.')}</small></div></div>
  ${low.map(({x,d})=>`<div class="lv24-row ${d<=3?'urgent':''}"><div class="lv24-ic">${SX.ico?SX.ico('pill'):'💊'}</div><div class="grow"><b>${E(x.n)}</b><small>${d<=0?P('none left'):d+' '+P('days left')}</small></div><button class="btn ${d<=3?'p':'s'} sm" data-sx="refill:${E(x.id)}">${P('Reorder')}</button></div>`).join('')}</div>`}});
}
