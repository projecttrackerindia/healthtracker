// ===================== live layer 30: the launch period — every feature free until 31 March 2027 =====================
// Families first. Nothing in the app is sold to them for now; the money comes from lab bookings, medicine orders and the
// shop. While the period runs the Plan page is one honest card — no prices, no subscribe buttons, nothing to cancel. The
// server decides (`launch` in /config and /hello), so on the day it ends the old plan page comes back on its own.
{
const P=SX.p,S=SX.S;
const L=()=>{const c=(SX.cfg&&SX.cfg.launch)||(SX.acct&&SX.acct.launch)||null;return c&&c.free?c:null};
const loc=()=>S.lang==='hi'?'hi-IN':S.lang==='te'?'te-IN':'en-IN';
const fmt=ts=>new Date(ts*1000).toLocaleDateString(loc(),{day:'numeric',month:'long',year:'numeric'});
const daysLeft=ts=>Math.max(0,Math.ceil((ts*1000-Date.now())/864e5));

SX.addPhrases({
 'Free for your whole family':['आपके पूरे परिवार के लिए मुफ़्त','మీ కుటుంబం మొత్తానికి ఉచితం'],
 'Everything is free until':['सब कुछ मुफ़्त है, इस तारीख़ तक:','అంతా ఉచితం, ఈ తేదీ వరకు:'],
 'No plan to choose, no card to add, nothing to cancel.':['कोई प्लान चुनना नहीं, कोई कार्ड जोड़ना नहीं, कुछ रद्द करना नहीं।','ప్లాన్ ఎంచుకోవడం లేదు, కార్డ్ జోడించడం లేదు, రద్దు చేయడం లేదు.'],
 'Everything included':['सब कुछ शामिल','అంతా కలిపి'],
 'How we earn':['हम कमाते कैसे हैं','మేము ఎలా సంపాదిస్తాం'],
 'A small share from the labs and pharmacies you order through — never from you, and never from your records. Your health data is not sold, to anyone, ever.':
  ['आप जिन लैब और फ़ार्मेसी से ऑर्डर करते हैं, उनसे हमें छोटा हिस्सा मिलता है — आपसे कभी नहीं, और आपके रिकॉर्ड से कभी नहीं। आपका स्वास्थ्य डेटा किसी को नहीं बेचा जाता।',
   'మీరు ఆర్డర్ చేసే ల్యాబ్‌లు, ఫార్మసీల నుండి చిన్న వాటా — మీ నుండి ఎప్పుడూ కాదు, మీ రికార్డుల నుండి ఎప్పుడూ కాదు. మీ ఆరోగ్య డేటా ఎవరికీ అమ్మబడదు.'],
 'After that':['उसके बाद','ఆ తర్వాత'],
 'We will say so well in advance, and the records you have added stay yours either way.':
  ['कुछ भी बदलने से काफ़ी पहले हम बता देंगे, और आपके जोड़े हुए रिकॉर्ड हर हाल में आपके ही रहेंगे।',
   'ఏదైనా మారే ముందు చాలా ముందుగానే చెబుతాం, మీరు చేర్చిన రికార్డులు ఎలాగైనా మీవే.'],
 'days left':['दिन बाकी','రోజులు మిగిలి'],
 'Unlimited':['असीमित','అపరిమితం'],
 'Smart readings this month':['इस महीने स्मार्ट रीडिंग','ఈ నెల స్మార్ట్ రీడింగ్‌లు'],
 'Family profiles, records and the vault':['परिवार की प्रोफ़ाइल, रिकॉर्ड और वॉल्ट','కుటుంబ ప్రొఫైల్‌లు, రికార్డులు, వాల్ట్'],
 'Smart reading of reports and prescriptions':['रिपोर्ट और पर्चों की स्मार्ट रीडिंग','రిపోర్టులు, ప్రిస్క్రిప్షన్ల స్మార్ట్ రీడింగ్'],
 'Doctor summaries you can share':['डॉक्टर के लिए साझा करने योग्य सारांश','డాక్టర్‌కు పంచుకునే సారాంశాలు'],
 'English, Hindi and Telugu':['अंग्रेज़ी, हिन्दी और तेलुगु','ఇంగ్లిష్, హిందీ, తెలుగు'],
 'Invoices':['इनवॉइस','ఇన్‌వాయిస్‌లు']});

const INCLUDED=()=>[
 ['users',P('Family profiles, records and the vault')],
 ['pulse',P('3D body, Heart Lab and Pregnancy')],
 ['records',P('Smart reading of reports and prescriptions')],
 ['pill',P('Medicine and lab price comparison')],
 ['calendar',P('Home sample collection booking')],
 ['cross',P('SOS, first aid and Medical ID')],
 ['id',P('Doctor summaries you can share')],
 ['heart',P('English, Hindi and Telugu')]];

function launchCard(l){const ic=k=>(SX.ico&&SX.ico(k))||'';
 return `<div class="card wide lv30-free">
  <div class="lv30-badge">${P('Free for your whole family')}</div>
  <h2 class="lv30-h">${P('Everything is free until')} <b>${E(fmt(l.until))}</b></h2>
  <p class="lv30-sub">${P('No plan to choose, no card to add, nothing to cancel.')} <span class="lv30-days">${daysLeft(l.until)} ${P('days left')}</span></p>
  <div class="lv30-grid">${INCLUDED().map(([k,t])=>`<div class="lv30-item"><i>${ic(k)}</i><span>${E(t)}</span></div>`).join('')}</div>
  <div class="lv30-note"><b>${P('How we earn')}</b><p>${P('A small share from the labs and pharmacies you order through — never from you, and never from your records. Your health data is not sold, to anyone, ever.')}</p></div>
  <div class="lv30-note"><b>${P('After that')}</b><p>${P('We will say so well in advance, and the records you have added stay yours either way.')}</p></div>
 </div>`}

// the whole Plan page while the period runs; the original page (prices, subscribe, invoices) returns untouched after it
if(typeof PAGES==='object'&&PAGES.plan){
 const base=PAGES.plan,headBase=(SX.heads&&SX.heads.plan)||null;
 SX.reg('plan',{
  head:()=>{const l=L();return l?[P('Plan'),P('Everything is free until')+' '+fmt(l.until)]:(headBase?headBase():[P('Plan'),''])},
  render:(...a)=>{const l=L();if(!l)return base(...a);
   const inv=(typeof PLANS==='object'&&PLANS&&PLANS.history)||[];
   return launchCard(l)+(inv.length?`<div class="card wide"><h4 class="sx-h4">${P('Invoices')}</h4><table class="sx-tbl"><tbody>${inv.map(h=>`<tr><td><b>${E(h.invoice||'—')}</b><br><small class="mute">${E(h.plan)} · ${E(h.provider)}</small></td><td style="text-align:right">₹${Math.round(h.amount).toLocaleString('en-IN')}</td></tr>`).join('')}</tbody></table></div>`:'')}});
}
// nothing can start a payment for a plan while there is nothing to buy
const sub0=SX.act.sub;SX.act.sub=a=>{const l=L();if(l){toast(P('Everything is free until')+' '+fmt(l.until));return}return sub0(a)};

// the quota line anywhere else in the app reads "Unlimited" rather than a number from a plan nobody is paying for
function quota(){if(!L())return;document.querySelectorAll('#page .mute.sm').forEach(p=>{if(p.dataset.lv30)return;
 if(/\d+\s*\/\s*(\d+|∞)/.test(p.textContent)&&/AI|smart|स्मार्ट|స్మార్ట్/i.test(p.textContent)){p.dataset.lv30='1';p.innerHTML=`${P('Smart readings this month')}: <b>${P('Unlimited')}</b>`}})}
new MutationObserver(()=>{clearTimeout(window.__lv30t);window.__lv30t=setTimeout(quota,60)}).observe(document.body,{childList:true,subtree:true});
setTimeout(quota,500);
SX.launch=L;
}
