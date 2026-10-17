// ===================== six · Safety: SOS, first aid, Medical ID, contacts =====================
(()=>{
'use strict';
const SX=window.SX,S=SX.S,E=SX.E,uid=SX.uid;
const D=SX.D;

SX.addStrings({
 'sos.alerting':D('Alerting your contacts','आपके संपर्कों को सूचित किया जा रहा है','మీ కాంటాక్ట్‌లకు తెలియజేస్తోంది'),
 'sos.locating':D('Getting your location…','आपकी लोकेशन ली जा रही है…','మీ లొకేషన్ తెలుసుకుంటోంది…'),
 'sos.cancel':D('Cancel','रद्द करें','రద్దు చేయండి'),
 'sos.text':D('Text contacts','संपर्कों को संदेश भेजें','కాంటాక్ట్‌లకు సందేశం పంపండి'),
 'sos.copy':D('Copy message','संदेश कॉपी करें','సందేశం కాపీ చేయండి'),
 'sos.nocontacts':D('No emergency contacts yet. Add one in Safety → Contacts.','अभी कोई आपातकालीन संपर्क नहीं है। सुरक्षा → संपर्क में जोड़ें।','ఇంకా అత్యవసర కాంటాక్ట్‌లు లేవు. భద్రత → కాంటాక్ట్‌లలో జోడించండి.')
});

SX.init(s=>{
 s.contacts=s.contacts||{m1:[{id:'c1',n:'Ananya',rel:'Spouse',ph:'',notify:true},{id:'c2',n:'Lakshmi',rel:'Mother',ph:'',notify:true}],m2:[{id:'c3',n:'Prasanna',rel:'Spouse',ph:'',notify:true}],m3:[{id:'c4',n:'Prasanna',rel:'Son',ph:'',notify:true}],m4:[{id:'c5',n:'Prasanna',rel:'Son',ph:'',notify:true}],m5:[{id:'c6',n:'Prasanna',rel:'Brother',ph:'',notify:true}]};
 s.mid=s.mid||{m1:{blood:'B+',allergies:['Penicillin'],conditions:['High cholesterol','Gallstones'],donor:'yes',doctor:'Dr. Sarah Wilson',notes:'',policy:''},
  m2:{blood:'O+',allergies:[],conditions:[],donor:'',doctor:'Dr. Fatima Khan',notes:'',policy:''},
  m3:{blood:'A+',allergies:['Sulfa drugs'],conditions:['Coronary artery disease','Enlarged prostate'],donor:'',doctor:'Dr. Sarah Wilson',notes:'',policy:''},
  m4:{blood:'',allergies:[],conditions:[],donor:'',doctor:'',notes:'',policy:''},m5:{blood:'',allergies:[],conditions:[],donor:'',doctor:'',notes:'',policy:''}};
 s.consent=s.consent||{sos_location:true,sos_medid:true,doctor_share:false,pharmacy_rx:true};
 s.ledger=s.ledger||[{t:s.created||Date.now(),m:'all',k:'defaults',on:true,x:'Defaults set at first launch. Location and Medical ID are shared only when you press SOS.'}];
 s.sos=s.sos||[];
});

// ---------------------------------------------------------------- helpers
const phoneNorm=v=>{let d=String(v||'').replace(/[\s\-().]/g,'');if(!d)return '';const plus=d[0]==='+';d=d.replace(/\D/g,'');if(!d)return null;
 if(!plus&&d.length===10)return '+91'+d;if(!plus&&d.length===11&&d[0]==='0')return '+91'+d.slice(1);if(!plus&&d.length===12&&d.startsWith('91'))return '+'+d;if(d.length<7||d.length>15)return null;return '+'+d};
const phoneShow=p=>{if(!p)return '';const m=/^\+91(\d{5})(\d{5})$/.exec(p);return m?`+91 ${m[1]} ${m[2]}`:p};
SX.phoneNorm=phoneNorm;
const contactsOf=id=>{S.contacts[id]=S.contacts[id]||[];return S.contacts[id]};
SX.contactsOf=contactsOf;
const midOf=id=>{S.mid[id]=S.mid[id]||{blood:'',allergies:[],conditions:[],donor:'',doctor:'',notes:'',policy:''};return S.mid[id]};
SX.midOf=midOf;
SX.medNames=m=>typeof SX.medList==='function'?SX.medList(m).map(x=>x.n):[];
const listText=a=>a&&a.length?a.join(', '):'none recorded';
SX.medSummary=m=>{const d=midOf(m.id);return `Blood group: ${d.blood||'not recorded'}. Allergies: ${listText(d.allergies)}. Conditions: ${listText(d.conditions)}. Medicines: ${listText(SX.medNames(m))}.`};
const isIOS=()=>/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
const smsHref=(nums,body)=>`sms:${nums.join(',')}${isIOS()?'&':'?'}body=${encodeURIComponent(body)}`;
const ledger=(k,on,x,m)=>{S.ledger.unshift({t:Date.now(),m:m||'all',k,on,x});S.ledger.length=Math.min(S.ledger.length,200);SX.save()};
SX.ledger=ledger;

// ---------------------------------------------------------------- SOS
SX.addPhrases({"Call first, alert your family next.": ["पहले कॉल करें, फिर परिवार को बताएँ।", "ముందు కాల్ చేయండి, తర్వాత కుటుంబానికి తెలియజేయండి."], "Police · fire · ambulance": ["पुलिस · फ़ायर · एम्बुलेंस", "పోలీస్ · ఫైర్ · అంబులెన్స్"], "Medical emergency": ["चिकित्सा आपातकाल", "వైద్య అత్యవసరం"], "then alert your people": ["फिर अपने लोगों को बताएँ", "తర్వాత మీ వారికి తెలియజేయండి"], "then": ["फिर", "తర్వాత"], "Alert my contacts": ["मेरे संपर्कों को सूचित करें", "నా కాంటాక్ట్‌లకు తెలియజేయండి"], "Open SOS": ["SOS खोलें", "SOS తెరవండి"], "Gets your location and Medical ID ready as a text message. Nothing is sent until you tap Send in your messaging app.": ["आपकी लोकेशन और मेडिकल आईडी एक टेक्स्ट संदेश में तैयार हो जाती है। आपके मैसेजिंग ऐप में Send दबाने तक कुछ भी नहीं भेजा जाता।", "మీ లొకేషన్ మరియు మెడికల్ ఐడీ టెక్స్ట్ సందేశంగా సిద్ధమవుతాయి. మీ మెసేజింగ్ యాప్‌లో Send నొక్కే వరకు ఏదీ పంపబడదు."], "Be ready before it happens": ["ज़रूरत से पहले तैयार रहें", "అవసరం రాకముందే సిద్ధంగా ఉండండి"], "Emergency numbers": ["आपातकालीन नंबर", "అత్యవసర నంబర్లు"], "All emergencies": ["सभी आपात स्थितियाँ", "అన్ని అత్యవసరాలు"], "Police, fire and ambulance. Works across India.": ["पुलिस, फ़ायर और एम्बुलेंस। पूरे भारत में चालू।", "పోలీస్, ఫైర్ మరియు అంబులెన్స్. భారతదేశం అంతటా పనిచేస్తుంది."], "Ambulance": ["एम्बुलेंस", "అంబులెన్స్"], "Emergency medical help in most states.": ["ज़्यादातर राज्यों में आपातकालीन चिकित्सा सहायता।", "చాలా రాష్ట్రాల్లో అత్యవసర వైద్య సహాయం."], "Police": ["पुलिस", "పోలీస్"], "Fire": ["फ़ायर", "ఫైర్"], "Child helpline": ["चाइल्ड हेल्पलाइन", "చైల్డ్ హెల్ప్‌లైన్"], "Women helpline": ["महिला हेल्पलाइन", "మహిళా హెల్ప్‌లైన్"], "Available in most states.": ["ज़्यादातर राज्यों में उपलब्ध।", "చాలా రాష్ట్రాల్లో అందుబాటులో ఉంది."], "Free mental-health support, 24×7.": ["मुफ़्त मानसिक स्वास्थ्य सहायता, 24×7।", "ఉచిత మానసిక ఆరోగ్య సహాయం, 24×7."], "Recent alerts": ["हाल की सूचनाएँ", "ఇటీవలి అలర్ట్‌లు"], "No alerts yet. Alerts are logged on this device only.": ["अभी तक कोई सूचना नहीं। सूचनाएँ केवल इसी डिवाइस पर दर्ज होती हैं।", "ఇంకా అలర్ట్‌లు లేవు. అలర్ట్‌లు ఈ పరికరంలో మాత్రమే నమోదవుతాయి."], "Add at least one emergency contact with a phone number": ["कम से कम एक आपातकालीन संपर्क फ़ोन नंबर के साथ जोड़ें", "కనీసం ఒక అత్యవసర కాంటాక్ట్‌ను ఫోన్ నంబర్‌తో జోడించండి"], "Fill in blood group and allergies in Medical ID": ["मेडिकल आईडी में ब्लड ग्रुप और एलर्जी भरें", "మెడికల్ ఐడీలో బ్లడ్ గ్రూప్ మరియు అలర్జీలు నింపండి"], "Location sharing for SOS is on (you can turn it off in Consent)": ["SOS के लिए लोकेशन साझा करना चालू है (आप इसे सहमति में बंद कर सकते हैं)", "SOS కోసం లొకేషన్ షేరింగ్ ఆన్‌లో ఉంది (మీరు దీన్ని సమ్మతిలో ఆఫ్ చేయవచ్చు)"], "Save the Medical ID image as your lock-screen": ["मेडिकल आईडी की तस्वीर को लॉक-स्क्रीन के रूप में सेव करें", "మెడికల్ ఐడీ చిత్రాన్ని లాక్-స్క్రీన్‌గా సేవ్ చేయండి"], "Done": ["हो गया", "పూర్తయింది"], "Set up": ["सेट करें", "సెటప్ చేయండి"], "Hold for 1.5 seconds so a pocket press never sends anything.": ["जेब में गलती से दबने पर कुछ न जाए, इसलिए 1.5 सेकंड दबाए रखें।", "జేబులో పొరపాటున నొక్కితే ఏదీ వెళ్లకుండా 1.5 సెకన్లు నొక్కి ఉంచండి."], "Can't hold? Use two taps": ["दबाए नहीं रख सकते? दो बार टैप करें", "నొక్కి ఉంచలేరా? రెండుసార్లు ట్యాప్ చేయండి"]});
let sosState=null;   // {m,loc,msg}
const holdMs=1500;
function sosSheet(){
 const m=SX.me(),cs=contactsOf(m.id).filter(c=>c.notify);
 return `<h2>🚨 ${E(SX.t('sos.title'))}</h2><p class="mute" style="margin:0 0 14px">${E(SX.t('sos.sub'))}</p>
 <div class="sx-callrow"><a class="btn red sx-big" href="tel:112" autofocus><b>${E(SX.t('call112'))}</b><small>${E(SX.p('Police · fire · ambulance'))}</small></a><a class="btn red sx-big" href="tel:108"><b>${E(SX.t('call108'))}</b><small>${E(SX.p('Medical emergency'))}</small></a></div>
 <div class="sx-sep"><span>${E(SX.p('then'))}</span></div>
 <div id="sxSosBody">${sosIdle(m,cs)}</div>
 <div style="display:flex;justify-content:flex-end;margin-top:14px"><button class="btn s" data-sx="closeModal">${E(SX.t('close'))}</button></div>`}
function sosIdle(m,cs){const withPh=cs.filter(c=>c.ph).length;
 return `<button class="sx-hold" id="sxHold" aria-describedby="sxHoldH"><i></i><span>${E(SX.t('sos.hold'))}</span></button>
 <p class="mute sm" id="sxHoldH" style="margin:8px 2px 0">${cs.length?`Alerts ${cs.map(c=>E(c.n)).join(', ')}${withPh<cs.length?` · <b>${cs.length-withPh} without a phone number</b>`:''}. `:E(SX.t('sos.nocontacts'))+' '}${E(SX.p('Hold for 1.5 seconds so a pocket press never sends anything.'))} <button class="sx-lk" data-sx="sos2">${E(SX.p("Can't hold? Use two taps"))}</button></p>`}
SX.openSOS=()=>{sosState=null;SX.modal(sosSheet(),{cls:'sx-sos-m',label:SX.t('sos.title')});bindHold()};
SX.act.sos=()=>SX.openSOS();
SX.act.sos2=()=>{const b=$('#sxSosBody');if(!b)return;b.innerHTML=`<button class="btn red w" data-sx="sosgo">Tap to alert my contacts</button><p class="mute sm">Nothing is sent until you tap a Text button on the next step.</p>`};
function bindHold(){const h=$('#sxHold');if(!h)return;let t=0,raf=0,t0=0;const fill=p=>h.style.setProperty('--p',p);
 const stop=()=>{clearTimeout(t);cancelAnimationFrame(raf);h.classList.remove('hold');fill(0)};
 const start=e=>{if(e.type==='keydown'&&(e.repeat||(e.key!==' '&&e.key!=='Enter')))return;e.preventDefault();stop();h.classList.add('hold');t0=performance.now();
  const tick=()=>{const p=Math.min(1,(performance.now()-t0)/holdMs);fill(p);if(p<1)raf=requestAnimationFrame(tick)};tick();
  t=setTimeout(()=>{stop();sosGo()},holdMs)};
 h.addEventListener('pointerdown',start);['pointerup','pointerleave','pointercancel','blur'].forEach(ev=>h.addEventListener(ev,stop));
 h.addEventListener('keydown',start);h.addEventListener('keyup',stop);h.addEventListener('contextmenu',e=>e.preventDefault())}
SX.act.sosgo=()=>sosGo();
function sosGo(){const m=SX.me(),b=$('#sxSosBody');if(!b)return;sosState={m:m.id,loc:null,t:Date.now()};
 b.innerHTML=`<div class="sx-working" role="status"><i></i><span>${E(SX.t('sos.locating'))}</span></div>`;
 const done=loc=>{if(!sosState||!$('#sxSosBody'))return;sosState.loc=loc;sosResult()};
 if(S.consent.sos_location&&navigator.geolocation){let fin=false;const to=setTimeout(()=>{if(!fin){fin=true;done(null)}},9000);
  try{navigator.geolocation.getCurrentPosition(p=>{if(fin)return;fin=true;clearTimeout(to);done({lat:p.coords.latitude,lng:p.coords.longitude,acc:Math.round(p.coords.accuracy||0)})},()=>{if(fin)return;fin=true;clearTimeout(to);done(null)},{enableHighAccuracy:true,timeout:8000,maximumAge:30000})}catch(e){if(!fin){fin=true;clearTimeout(to);done(null)}}}
 else done(null)}
function sosMessage(m,loc){const lines=[`EMERGENCY: ${m.name} needs help.`];
 lines.push(loc?`Location: https://maps.google.com/?q=${loc.lat.toFixed(6)},${loc.lng.toFixed(6)}${loc.acc?` (about ${loc.acc} m)`:''}`:'Location: not available. Please call them.');
 lines.push('Time: '+new Date().toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'}));
 if(S.consent.sos_medid)lines.push(SX.medSummary(m));
 lines.push('Call them or 112 now. Sent from DoKKo SOS.');return lines.join('\n')}
function sosResult(){const m=SX.member(sosState.m)||SX.me(),loc=sosState.loc,msg=sosMessage(m,loc),cs=contactsOf(m.id).filter(c=>c.notify),withPh=cs.filter(c=>c.ph);
 sosState.msg=msg;S.sos.unshift({t:Date.now(),m:m.id,loc:loc?{lat:+loc.lat.toFixed(4),lng:+loc.lng.toFixed(4)}:null,n:withPh.length});S.sos.length=Math.min(S.sos.length,30);SX.save();
 $('#sxSosBody').innerHTML=`<div class="sx-ok"><b>${E(SX.t('sos.alerting'))}</b><span>${loc?`📍 Location found${loc.acc?` (about ${loc.acc} m)`:''}`:(S.consent.sos_location?'📍 Location not available: the message asks them to call you':'📍 Location sharing is off in Consent')}</span></div>
 <pre class="sx-msg" id="sxMsg">${E(msg)}</pre>
 <div class="sx-sendrow">${withPh.length?withPh.map(c=>`<a class="btn red" href="${E(smsHref([c.ph],msg))}">💬 ${E(c.n)}</a>`).join(''):''}${withPh.length>1?`<a class="btn red" href="${E(smsHref(withPh.map(c=>c.ph),msg))}">💬 All (${withPh.length})</a>`:''}
 <button class="btn s" data-sx="sosshare">${navigator.share?'Share…':E(SX.t('sos.copy'))}</button></div>
 ${cs.length-withPh.length?`<p class="mute sm">${cs.filter(c=>!c.ph).map(c=>E(c.n)).join(', ')} ${cs.filter(c=>!c.ph).length>1?'have':'has'} no phone number yet. <button class="sx-lk" data-sx="tab:contacts">Add numbers</button></p>`:''}
 ${cs.length?'':`<p class="mute sm">${E(SX.t('sos.nocontacts'))} <button class="sx-lk" data-sx="tab:contacts">Add contacts</button></p>`}
 <p class="mute sm" style="margin-top:10px">Your messaging app opens with this text ready; send it from there. SMS works without internet. Alerts to family members' DoKKo apps need accounts and arrive in a later release.</p>`}
SX.act.sosshare=async()=>{if(!sosState)return;try{if(navigator.share)await navigator.share({text:sosState.msg});else{await navigator.clipboard.writeText(sosState.msg);toast('Message copied')}}catch(e){if(e&&e.name!=='AbortError'){try{await navigator.clipboard.writeText(sosState.msg);toast('Message copied')}catch(_){toast('Could not copy: select the text and copy it')}}}};

// ---------------------------------------------------------------- Safety › SOS page
const NUMS=[['112','All emergencies','Police, fire and ambulance. Works across India.',1],['108','Ambulance','Emergency medical help in most states.',1],['100','Police','',0],['101','Fire','',0],['1098','Child helpline','',0],['181','Women helpline','Available in most states.',0],['14416','Tele-MANAS','Free mental-health support, 24×7.',0]];
function safetySetup(m){const c=contactsOf(m.id),d=midOf(m.id);
 return [['Add at least one emergency contact with a phone number',c.some(x=>x.ph),'contacts'],['Fill in blood group and allergies in Medical ID',!!(d.blood&&(d.allergies.length||d.conditions.length||d.notes)),'mid'],['Location sharing for SOS is on (you can turn it off in Consent)',!!S.consent.sos_location,'consent'],['Save the Medical ID image as your lock-screen',!!(S.midSaved&&S.midSaved[m.id]),'mid']]}
SX.safetySetup=safetySetup;
SX.reg('sos',{head:()=>[SX.t('sos.title'),SX.p('Call first, alert your family next.')],
 render:()=>{const m=SX.me(),st=safetySetup(m),done=st.filter(x=>x[1]).length,p=Math.round(done/st.length*100);
  return `<div class="card wide sx-sosc"><div class="sx-callrow"><a class="btn red sx-big" href="tel:112"><b>${E(SX.t('call112'))}</b><small>${E(SX.p('Police · fire · ambulance'))}</small></a><a class="btn red sx-big" href="tel:108"><b>${E(SX.t('call108'))}</b><small>${E(SX.p('Medical emergency'))}</small></a></div>
  <div class="sx-sep"><span>${E(SX.p('then alert your people'))}</span></div>
  <div class="sx-sosrow"><div><b>${m.rel==='You'?E(SX.p('Alert my contacts')):'Alert '+E(m.name)+"'s contacts"}</b><p class="mute sm" style="margin:4px 0 0">${E(SX.p('Gets your location and Medical ID ready as a text message. Nothing is sent until you tap Send in your messaging app.'))}</p></div><button class="btn red" data-sx="sos">${E(SX.p('Open SOS'))}</button></div></div>
  <div class="card"><div class="hd"><h3>${E(SX.p('Be ready before it happens'))}</h3><div class="ring" style="--p:${p}"><b>${p}%</b></div></div>${st.map(([t,ok,tab])=>`<button class="row sx-chk ${ok?'ok':''}" data-sx="tab:${tab}"><i>${ok?'✓':'○'}</i><span class="grow">${E(SX.p(t))}</span><small>${E(SX.p(ok?'Done':'Set up'))}</small></button>`).join('')}</div>
  <div class="card"><h3>${E(SX.p('Emergency numbers'))}</h3><div class="sx-nums">${NUMS.map(([n,t,d,big])=>`<a class="sx-num ${big?'big':''}" href="tel:${n}"><b>${n}</b><span>${E(SX.p(t))}</span>${d?`<small>${E(SX.p(d))}</small>`:''}</a>`).join('')}</div></div>
  <div class="card"><h3>${E(SX.p('Recent alerts'))}</h3>${S.sos.length?S.sos.slice(0,6).map(a=>{const mm=SX.member(a.m);return `<div class="row"><div style="font-size:20px">🚨</div><div class="grow"><b>${E(mm?mm.name:'Unknown')}</b><small>${E(SX.fmtT(a.t))} · ${a.loc?'location included':'no location'} · ${a.n} contact${a.n===1?'':'s'} with numbers</small></div></div>`}).join('')+`<button class="btn s sm" data-sx="clearsos">Clear log</button>`:`<p class="mute sm" style="margin:0">${E(SX.p('No alerts yet. Alerts are logged on this device only.'))}</p>`}</div>`}});
SX.act.clearsos=()=>{S.sos=[];SX.save();render()};

// ---------------------------------------------------------------- First aid
const AID=[
{id:'cpr',e:'🫀',t:'Not breathing / cardiac arrest (CPR)',tag:'Adult & child',call:'The person does not respond and is not breathing, or is only gasping.',
 steps:['Make sure the area is safe. Tap their shoulders and shout “Are you okay?”','No response and no normal breathing: shout for help and call 112 (put the phone on speaker). Ask someone to bring an AED if there is one nearby.','Lay them flat on their back on a firm surface.','Kneel beside them. Put the heel of one hand on the centre of the chest, the other hand on top, arms straight.','Push hard and fast: about 5 cm deep, 100–120 times a minute. Follow the beat below. Let the chest come back up fully each time.','Keep going until help arrives, an AED is ready, or the person moves. If an AED arrives, switch it on and follow its voice prompts.','If you are trained and willing, give 2 rescue breaths after every 30 pushes.','Swap with someone every 2 minutes if you can.'],
 dont:['Do not stop to check for a pulse.','Do not give food or water.'],note:'Child: use one hand, about 5 cm deep. Infant: two fingers in the centre of the chest, about 4 cm deep.',met:1},
{id:'choking',e:'😮',t:'Choking',tag:'Adult, child, baby',call:'They cannot cough, speak or breathe, or they turn blue.',
 steps:['Ask “Are you choking?” If they can cough, speak or breathe, encourage them to keep coughing.','If they cannot: lean them forward and give up to 5 firm back blows between the shoulder blades with the heel of your hand.','Still blocked: give up to 5 abdominal thrusts. Stand behind them, make a fist just above the belly button, grip it with the other hand and pull sharply inwards and upwards.','Repeat 5 back blows and 5 thrusts until the object comes out or they stop responding.','If they stop responding: call 112 and start CPR.'],
 dont:['Do not do blind finger sweeps.','Pregnant or very large person: use chest thrusts instead of abdominal thrusts.'],note:'Baby under 1 year: lay them face-down along your forearm with the head lower than the body, 5 back blows, then turn face-up and give 5 chest thrusts with two fingers. Never use abdominal thrusts on a baby. Call 112.'},
{id:'heart',e:'💔',t:'Possible heart attack',tag:'Adult',call:'Pressure, squeezing or heaviness in the chest for more than a few minutes, or pain spreading to the arm, jaw, neck or back, with sweating, breathlessness or nausea. Women, older people and people with diabetes may have fewer chest symptoms.',
 steps:['Call 112 straight away. Do not wait to see if it passes.','Help them sit down, half upright, in a comfortable position. Loosen tight clothing.','Keep them calm and still. Stay with them.','If the 112 operator or their doctor has told them to, and they are not allergic, they can chew one adult-strength aspirin.','If they become unresponsive and stop breathing normally, start CPR.'],dont:['Do not let them walk, drive or climb stairs.','Do not give food or drink.']},
{id:'stroke',e:'🧠',t:'Possible stroke (BE-FAST)',tag:'Adult',call:'Any one of these, even if it passes: loss of Balance, sudden trouble with Eyesight, a drooping Face, weak Arm or leg, difficult Speech.',
 steps:['Call 112 immediately and say “possible stroke”.','Note the time the symptoms started. Doctors need it.','Keep them comfortable, lying down with the head and shoulders slightly raised, or on their side if drowsy.','Stay with them and watch their breathing.','Go to a hospital that has a CT scan and stroke care. The ambulance team can advise.'],dont:['Do not give food, drink or any medicine, including aspirin.','Do not wait for it to get better.']},
{id:'bleed',e:'🩸',t:'Severe bleeding',tag:'All ages',call:'Blood is spurting, soaking through cloth, or will not stop after 10 minutes of pressure.',
 steps:['Call 112. Wear gloves or use a plastic bag on your hand if you can.','Press firmly on the wound with a clean cloth or bandage. Keep pressing.','If blood soaks through, add more cloth on top. Do not remove the first layer.','Raise the injured arm or leg above the heart if there is no broken bone.','Lay the person down and keep them warm. Watch for pale, cold, clammy skin or confusion.','Keep pressing until help arrives.'],dont:['Do not remove an object stuck in the wound. Pad around it.','Do not apply powders, turmeric or other home remedies.']},
{id:'burn',e:'🔥',t:'Burns and scalds',tag:'All ages',call:'Large burns, burns on the face, hands, feet or genitals, deep burns, chemical or electrical burns, or any burn in a baby.',
 steps:['Move away from the heat source. Remove rings, watches and clothing near the burn unless stuck to the skin.','Cool the burn under cool running tap water for 20 minutes.','Cover loosely with cling film or a clean, non-fluffy cloth.','Give pain relief the person normally uses safely, following the pack.','Call 112 or go to hospital for the serious burns listed above.'],dont:['Do not use ice, butter, toothpaste, oil or turmeric.','Do not burst blisters.','Do not pull off clothing that is stuck.']},
{id:'faint',e:'😵',t:'Fainting',tag:'All ages',call:'They do not wake within a minute, have chest pain, are pregnant, injured their head, or are not breathing normally.',
 steps:['Lay them flat and raise their legs about 30 cm.','Loosen tight clothing. Give fresh air.','Check they are breathing. If breathing and unresponsive, turn them onto their side (recovery position).','Once awake, let them rest and sip water slowly. Sit up slowly.','If they are not breathing normally, call 112 and start CPR.'],dont:['Do not give food or drink until fully awake.','Do not splash water on the face.']},
{id:'seizure',e:'⚡',t:'Seizure or fit',tag:'All ages',call:'It lasts more than 5 minutes, repeats, it is their first seizure, they are pregnant, injured, or have trouble breathing afterwards.',
 steps:['Stay calm. Note the time it started.','Clear hard or sharp things away. Put something soft under the head.','Loosen anything tight around the neck.','When the shaking stops, turn them onto their side and check breathing.','Stay with them until fully alert. Speak calmly.'],dont:['Do not hold them down.','Do not put anything in the mouth.','Do not give water or food until fully awake.']},
{id:'snake',e:'🐍',t:'Snake bite',tag:'All ages',call:'Always. Go to a hospital that has anti-snake venom as fast as you can.',
 steps:['Call 108 or 112. Move away from the snake.','Keep the person calm and as still as possible. Panic and movement spread venom faster.','Keep the bitten limb still, like a fracture: a splint or sling works. Keep it at about heart level.','Take off rings, watches and tight clothing near the bite before swelling starts.','Note the time of the bite. Remember the snake’s colour and size, but do not try to catch it.','Go straight to hospital. Do not wait for symptoms.'],dont:['Do not cut the wound, suck out venom or tie a tight band.','Do not apply ice, herbs or chemicals.','Do not give alcohol or let the person walk about.']},
{id:'animal',e:'🐕',t:'Dog, cat or monkey bite',tag:'All ages',call:'Deep or bleeding bites, bites to the face or neck, or bites from an unknown or unwell animal.',
 steps:['Wash the wound with soap and running water for 15 minutes.','Rinse again and cover with a clean dressing.','See a doctor the same day. Rabies vaccine, and sometimes immunoglobulin, may be needed even for small wounds.','Note the animal and where it can be found. Do not try to catch it.'],dont:['Do not rub in chilli, turmeric or oil.','Do not stitch or tightly bandage the wound yourself.']},
{id:'fracture',e:'🦴',t:'Broken bone or sprain',tag:'All ages',call:'Bone sticking out, the limb looks bent, severe pain, numb or blue fingers or toes, or injury to the head, neck or back.',
 steps:['Keep the injured part still. Support it in the position found.','Cover any open wound with a clean cloth. Press gently around it if bleeding.','Wrap ice in a cloth and hold it on the area for 15–20 minutes.','Support the limb with a sling or padding.','Get medical care. Call 112 for a suspected head, neck or back injury and do not move the person.'],dont:['Do not try to straighten the bone.','Do not move someone with a suspected neck or back injury.']},
{id:'poison',e:'☠️',t:'Poisoning or overdose',tag:'All ages',call:'Always. Call 112 right away and tell them what was taken, how much and when.',
 steps:['Call 112. Stay with the person.','Take the container, packet or plant to show the doctor.','If they are awake, wipe out the mouth and keep them sitting upright.','If they are drowsy but breathing, turn them onto their side.','If they stop breathing normally, start CPR.'],dont:['Do not make them vomit.','Do not give food, milk or drink unless a doctor says so.']},
{id:'allergy',e:'🤧',t:'Severe allergic reaction',tag:'All ages',call:'Swelling of the lips, tongue or throat, trouble breathing, wheeze, dizziness or collapse after a sting, food or medicine.',
 steps:['Call 112.','If they carry an adrenaline auto-injector, use it now on the outer thigh. Follow the instructions on the device.','Lay them flat with legs raised. If breathing is hard, let them sit up. Do not stand them up.','If there is no improvement after 5–15 minutes and they have a second device, use it.','Stay with them. Start CPR if they stop breathing normally.'],dont:['Do not wait to see if it settles.','Do not give food or drink.']},
{id:'lowsugar',e:'🍬',t:'Low blood sugar (diabetes)',tag:'Adult & child',call:'They are confused and cannot swallow safely, drift into unconsciousness, or do not improve after 15 minutes.',
 steps:['If awake and able to swallow: give about 15 g of fast sugar, such as 3 teaspoons of sugar in water, a small glass of fruit juice or glucose tablets.','Wait 15 minutes. If they are still shaky or confused, repeat once.','Once better, give a snack such as biscuits or a sandwich.','If they are drowsy, cannot swallow or are unconscious: call 112 and lay them on their side.'],dont:['Do not put food or drink in the mouth of someone who is drowsy or unconscious.']},
{id:'heat',e:'🥵',t:'Heat stroke',tag:'All ages',call:'Confusion, fainting, a very hot body, fits, or no sweating in the heat.',
 steps:['Call 112. Move to the shade or somewhere cool.','Remove extra clothing. Cool the body with wet cloths, fanning or cool water.','Place cool packs on the neck, armpits and groin.','If awake, give small sips of water.','Keep cooling until help arrives.'],dont:['Do not give tea, coffee or fizzy drinks.','Do not give medicine to bring down the temperature.']},
{id:'drown',e:'🌊',t:'Drowning',tag:'All ages',call:'Always. Call 112 for anyone pulled from water who was struggling, coughing or unresponsive.',
 steps:['Reach or throw something that floats. Do not jump in unless you are trained.','Once out, check for breathing. If not breathing normally, call 112 and start CPR. If trained, give 5 rescue breaths first.','If breathing, put them on their side and keep them warm.','Even if they seem fine, get medical help. Lung problems can show up later.'],dont:['Do not try to pump water out of the stomach.']},
{id:'nose',e:'👃',t:'Nosebleed',tag:'All ages',call:'Bleeding over 20 minutes, after a head injury, or in someone on blood thinners.',
 steps:['Sit up and lean forward.','Pinch the soft part of the nose for 10 minutes without letting go.','Breathe through the mouth. Spit out any blood.','If it stops, avoid blowing the nose for several hours.'],dont:['Do not tilt the head back.','Do not lie flat.']},
{id:'eye',e:'👁️',t:'Chemical in the eye',tag:'All ages',call:'Any strong chemical, or pain and blurry vision after rinsing.',
 steps:['Rinse the open eye under gently running tap water for 15–20 minutes. Tilt the head so water runs away from the other eye.','Remove contact lenses if they come out easily.','Cover loosely with a clean cloth and go to an eye hospital.'],dont:['Do not rub the eye.','Do not use eye drops or ointments.']},
{id:'preg',e:'🤰',t:'Pregnancy warning signs',tag:'Pregnancy',call:'Go to a hospital now, or call 112 if severe: heavy bleeding, severe belly pain, fluid leaking, fits, a severe headache with blurry vision or swelling, or the baby moving much less than usual.',
 steps:['Call your doctor or go to the nearest hospital. Take your pregnancy file.','Lie on your left side while arranging transport.','Note when it started and anything else you noticed.','Do not eat or drink if you may need an operation, unless the doctor says otherwise.'],dont:['Do not wait for the next appointment.','Do not take any medicine to “settle” it without asking a doctor.']}];
SX.AID=AID;
let aidQ='',aidTag='All',metOn=false;
const AIDTAGS=['All','Adult','Child','Pregnancy'];
function aidCard(a){return `<details class="sx-aid" id="aid-${a.id}" ${aidOpen===a.id?'open':''}><summary><i>${a.e}</i><span><b>${E(a.t)}</b><small>${E(a.tag)}</small></span></summary>
 <div class="sx-aidb"><div class="sx-call"><b>Call 112 if:</b> ${E(a.call)}</div><h4>What to do</h4><ol>${a.steps.map(s=>`<li>${E(s)}</li>`).join('')}</ol>
 ${a.dont&&a.dont.length?`<h4>Do not</h4><ul class="sx-dont">${a.dont.map(s=>`<li>${E(s)}</li>`).join('')}</ul>`:''}${a.note?`<p class="mute sm">${E(a.note)}</p>`:''}
 ${a.met?`<div class="sx-met" id="sxMet"><button class="btn ${metOn?'red':'p'}" data-sx="met">${metOn?'■ Stop the beat':'▶ Start the beat (110 per minute)'}</button><span id="sxMetN" class="mono">0:00 · 0 pushes</span><i id="sxMetDot"></i></div>`:''}
 <div class="sx-aidf"><a class="btn red sm" href="tel:112">${E(SX.t('call112'))}</a><a class="btn s sm" href="tel:108">${E(SX.t('call108'))}</a></div></div></details>`}
let aidOpen='';
function aidList(){const q=aidQ.trim().toLowerCase();return AID.filter(a=>{if(aidTag==='Adult'&&!/Adult|All/.test(a.tag))return false;if(aidTag==='Child'&&!/Child|All|baby/i.test(a.tag))return false;if(aidTag==='Pregnancy'&&!/Pregnancy|All/.test(a.tag))return false;
  return !q||(a.t+' '+a.call+' '+a.steps.join(' ')).toLowerCase().includes(q)})}
SX.reg('aid',{head:()=>[SX.t('firstaid'),'Plain steps for the first minutes. Call 112 first when it is serious.'],
 render:()=>{const m=SX.me(),list=aidList();if(SX.pregOn(m)&&!aidQ&&aidTag==='All'){list.sort((a,b)=>(b.id==='preg')-(a.id==='preg'))}
  return `<div class="card wide"><div class="sx-aidtop"><input id="aidq" type="search" placeholder="Search: burn, snake, choking…" value="${E(aidQ)}" aria-label="Search first aid" autocomplete="off"><div class="chips">${AIDTAGS.map(t=>`<button class="chip ${t===aidTag?'on':''}" data-sx="aidtag:${t}">${t}</button>`).join('')}</div></div>
  <p class="mute sm" style="margin:10px 0 0">This is first-aid guidance, not a diagnosis. If you are unsure, call 112.</p></div>
  <div class="wide sx-aidgrid" id="aidlist">${list.map(aidCard).join('')||'<div class="card"><p class="mute">No match. Try another word, or call 112 if it is urgent.</p></div>'}</div>`},
 after:()=>{const q=$('#aidq');if(q)q.oninput=()=>{aidQ=q.value;$('#aidlist').innerHTML=aidList().map(aidCard).join('')||'<div class="card"><p class="mute">No match. Try another word, or call 112 if it is urgent.</p></div>'};
  if(aidOpen){const el=document.getElementById('aid-'+aidOpen);if(el)setTimeout(()=>{el.scrollIntoView({behavior:'smooth',block:'start'});el.classList.add('flash')},60)}}});
SX.act.aidtag=([t])=>{aidTag=t;render()};
SX.act.aid=([id])=>{aidOpen=id;aidQ='';aidTag='All';if(page==='aid')render();else go('aid');setTimeout(()=>{aidOpen=''},1500)};
// compression beat
const MET={t:0,n:0,t0:0,ctx:null};
function beep(){try{const c=MET.ctx||(MET.ctx=new(window.AudioContext||window.webkitAudioContext)());if(c.state==='suspended')c.resume();const o=c.createOscillator(),g=c.createGain();o.frequency.value=880;g.gain.value=.0001;o.connect(g);g.connect(c.destination);const t=c.currentTime;g.gain.exponentialRampToValueAtTime(.3,t+.005);g.gain.exponentialRampToValueAtTime(.0001,t+.07);o.start(t);o.stop(t+.09)}catch(e){}}
SX.act.met=()=>{if(MET.t){stopMet();return}metOn=true;MET.n=0;MET.t0=Date.now();beep();MET.n=1;
 MET.t=setInterval(()=>{if(!document.getElementById('sxMet')){stopMet();return}MET.n++;beep();const dot=$('#sxMetDot');if(dot){dot.classList.remove('b');void dot.offsetWidth;dot.classList.add('b')}const s=Math.floor((Date.now()-MET.t0)/1000);const el=$('#sxMetN');if(el)el.textContent=`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')} · ${MET.n} pushes`;if(s>0&&s%120===0&&MET.n%66<2)toast('2 minutes: swap with someone if you can, without stopping the beat for long')},545);
 const b=$('#sxMet .btn');if(b){b.className='btn red';b.textContent='■ Stop the beat'}};
function stopMet(){clearInterval(MET.t);MET.t=0;metOn=false;const b=$('#sxMet .btn');if(b){b.className='btn p';b.textContent='▶ Start the beat (110 per minute)'}}
SX.stopMet=stopMet;

// ---------------------------------------------------------------- Medical ID
const BLOODS=['','A+','A−','B+','B−','AB+','AB−','O+','O−'];
const csv=v=>v.split(/[,;\n]/).map(x=>x.trim()).filter(Boolean).slice(0,20);
function midCard(m){const d=midOf(m.id),meds=SX.medNames(m),cs=contactsOf(m.id).filter(c=>c.notify);
 return `<div class="sx-mid" id="sxMidCard"><div class="sx-mid-h"><b>MEDICAL ID</b><span>In an emergency call 112</span></div>
 <div class="sx-mid-n"><h3>${E(m.name)}</h3><small>${m.age} years · ${m.sex==='female'?'Female':'Male'}</small></div>
 <div class="sx-mid-g"><div class="bl"><small>Blood group</small><b>${E(d.blood||'?')}</b></div><div><small>Allergies</small><b class="${d.allergies.length?'al':''}">${E(d.allergies.length?d.allergies.join(', '):'None recorded')}</b></div></div>
 <div class="sx-mid-r"><small>Conditions</small><b>${E(d.conditions.length?d.conditions.join(', '):'None recorded')}</b></div>
 <div class="sx-mid-r"><small>Regular medicines</small><b>${E(meds.length?meds.join(', '):'None recorded')}</b></div>
 ${d.notes?`<div class="sx-mid-r"><small>Notes</small><b>${E(d.notes)}</b></div>`:''}
 ${d.donor==='yes'?'<div class="sx-mid-r"><b>Organ donor</b></div>':''}
 <div class="sx-mid-r"><small>Emergency contacts</small>${cs.length?cs.map(c=>`<b>${E(c.n)} (${E(c.rel)})${c.ph?' · '+E(phoneShow(c.ph)):''}</b>`).join(''):'<b>None added</b>'}</div></div>`}
SX.reg('mid',{head:()=>['Medical ID','What a responder needs to know in the first minute.'],
 render:()=>{const m=SX.me(),d=midOf(m.id);
  return `<div class="card"><h3>Details for ${E(m.name)}</h3><div class="form" id="midForm">
   <label>Blood group<select data-sxc="midf:blood">${BLOODS.map(b=>`<option value="${b}" ${b===d.blood?'selected':''}>${b||'Not sure'}</option>`).join('')}</select></label>
   <label>Organ donor<select data-sxc="midf:donor"><option value="">Not stated</option><option value="yes" ${d.donor==='yes'?'selected':''}>Yes</option><option value="no" ${d.donor==='no'?'selected':''}>No</option></select></label>
   <label class="full">Allergies <small>separate with commas</small><input data-sxc="midf:allergies" value="${E(d.allergies.join(', '))}" placeholder="Penicillin, peanuts, bee stings" maxlength="200"></label>
   <label class="full">Conditions <small>for example diabetes, asthma, epilepsy, heart disease</small><input data-sxc="midf:conditions" value="${E(d.conditions.join(', '))}" placeholder="Type 2 diabetes, asthma" maxlength="240"></label>
   <label class="full">Regular medicines<input value="${E(SX.medNames(m).join(', ')||'None')}" disabled></label>
   <label>Regular doctor<input data-sxc="midf:doctor" value="${E(d.doctor)}" maxlength="80"></label>
   <label>Insurance policy no. <small>optional</small><input data-sxc="midf:policy" value="${E(d.policy||'')}" maxlength="40" inputmode="text" autocomplete="off"></label>
   <label class="full">Notes for responders<input data-sxc="midf:notes" value="${E(d.notes)}" maxlength="160" placeholder="Has a pacemaker, wears hearing aids…"></label></div>
   <p class="mute sm" style="margin:12px 0 0">Saved on this device. Blood group and allergies are used to warn you in the medicine finder. This card is for you to show; it is not a medical record.</p></div>
  <div class="card"><div class="hd"><h3>Card</h3><span class="demo">PREVIEW</span></div>${midCard(m)}
   <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px"><button class="btn p" data-sx="midimg">⬇ Save as lock-screen image</button><button class="btn s" data-sx="midprint">🖨 Print</button></div>
   <p class="mute sm" style="margin:10px 0 0">Set the image as your lock-screen wallpaper so a responder can read it without unlocking your phone.</p></div>`}});
SX.chg.midf=([f],el)=>{const m=SX.me(),d=midOf(m.id);const v=el.value;
 if(f==='allergies'||f==='conditions')d[f]=csv(v);else d[f]=v.trim();SX.save();ledger('medid',true,'Medical ID updated for '+m.name,m.id);
 const c=$('#sxMidCard');if(c)c.outerHTML=midCard(m);if(page==='mid'){}};
SX.act.midprint=()=>{const m=SX.me(),w=window.open('','_blank','noopener,width=520,height=720');if(!w){toast('Pop-ups are blocked: allow them to print the card');return}
 const css='body{font:16px system-ui,sans-serif;margin:24px}h1{color:#c4122f;margin:0 0 4px}small{color:#555;display:block}b{display:block;margin:2px 0 10px}.g{display:flex;gap:30px}';
 const d=midOf(m.id),meds=SX.medNames(m),cs=contactsOf(m.id).filter(c=>c.notify);
 w.document.write(`<!doctype html><title>Medical ID</title><style>${css}</style><h1>MEDICAL ID</h1><small>In an emergency call 112</small><h2>${E(m.name)}</h2><small>${m.age} years</small><div class="g"><div><small>Blood group</small><b>${E(d.blood||'?')}</b></div><div><small>Allergies</small><b>${E(d.allergies.join(', ')||'None recorded')}</b></div></div><small>Conditions</small><b>${E(d.conditions.join(', ')||'None recorded')}</b><small>Regular medicines</small><b>${E(meds.join(', ')||'None recorded')}</b>${d.notes?`<small>Notes</small><b>${E(d.notes)}</b>`:''}<small>Emergency contacts</small>${cs.map(c=>`<b>${E(c.n)} (${E(c.rel)}) ${E(phoneShow(c.ph))}</b>`).join('')||'<b>None</b>'}`);w.document.close();setTimeout(()=>w.print(),300)};
SX.act.midimg=()=>{const m=SX.me(),d=midOf(m.id),meds=SX.medNames(m),cs=contactsOf(m.id).filter(c=>c.notify);
 const W=1080,H=1920,c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');
 x.fillStyle='#ffffff';x.fillRect(0,0,W,H);x.fillStyle='#c4122f';x.fillRect(0,0,W,300);
 x.fillStyle='#fff';x.font='700 96px system-ui,Segoe UI,Arial,sans-serif';x.fillText('MEDICAL ID',60,150);x.font='500 44px system-ui,Arial,sans-serif';x.fillText('In an emergency call 112',60,230);
 let y=420;const T=(label,val,size=54,col='#111')=>{x.fillStyle='#667';x.font='600 34px system-ui,Arial,sans-serif';x.fillText(label.toUpperCase(),60,y);y+=58;x.fillStyle=col;x.font='700 '+size+'px system-ui,Arial,sans-serif';
  const words=String(val).split(' ');let line='';for(const w of words){const t=line?line+' '+w:w;if(x.measureText(t).width>W-120&&line){x.fillText(line,60,y);y+=size*1.18;line=w}else line=t}x.fillText(line,60,y);y+=size*1.18+34};
 x.fillStyle='#111';x.font='700 84px system-ui,Arial,sans-serif';x.fillText(m.name,60,380);y=470;
 T('Age',m.age+' years · '+(m.sex==='female'?'Female':'Male'),46);T('Blood group',d.blood||'Not recorded',90,'#c4122f');T('Allergies',d.allergies.length?d.allergies.join(', '):'None recorded',56,d.allergies.length?'#c4122f':'#111');
 T('Conditions',d.conditions.length?d.conditions.join(', '):'None recorded',50);T('Regular medicines',meds.length?meds.join(', '):'None recorded',46);if(d.notes)T('Notes',d.notes,44);
 T('Emergency contacts',cs.length?cs.map(k=>k.n+' ('+k.rel+')'+(k.ph?' '+phoneShow(k.ph):'')).join(' · '):'None added',44);
 x.fillStyle='#889';x.font='500 30px system-ui,Arial,sans-serif';x.fillText('Saved '+new Date().toLocaleDateString('en-IN')+' · DoKKo',60,H-60);
 c.toBlob(b=>{if(!b){toast('Could not create the image');return}const u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download='medical-id-'+m.name.toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.png';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),4000);S.midSaved=S.midSaved||{};S.midSaved[m.id]=Date.now();SX.save();toast('Medical ID image saved')},'image/png')};

// ---------------------------------------------------------------- Contacts
const RELS=['Spouse','Mother','Father','Son','Daughter','Brother','Sister','Friend','Neighbour','Doctor','Other'];
let editC=null;
SX.reg('contacts',{head:()=>['Emergency contacts','People who get your SOS message.'],
 render:()=>{const m=SX.me(),cs=contactsOf(m.id),ed=editC&&cs.find(c=>c.id===editC);
  return `<div class="card"><h3>${m.rel==='You'?'My':E(m.name)+"'s"} contacts</h3>${cs.length?cs.map(c=>`<div class="row"><div class="av" style="width:40px;height:40px;font-size:13px">${E(c.n.slice(0,2).toUpperCase())}</div><div class="grow"><b>${E(c.n)} <small>· ${E(c.rel)}</small></b><small>${c.ph?`<a href="tel:${E(c.ph)}">${E(phoneShow(c.ph))}</a>`:'<span style="color:var(--amber)">No phone number yet</span>'}</small></div>
   <label class="sx-sw" title="Include in SOS alerts"><input type="checkbox" data-sxc="cnotify:${c.id}" ${c.notify?'checked':''}><i></i><span class="sr-only">Alert on SOS</span></label><button class="btn s sm" data-sx="cedit:${c.id}">Edit</button><button class="btn s sm" data-sx="cdel:${c.id}" aria-label="Delete ${E(c.n)}">✕</button></div>`).join(''):'<p class="mute">No contacts yet.</p>'}
   <p class="mute sm" style="margin:8px 0 0">The switch decides who is included in the SOS message.</p></div>
  <div class="card"><h3>${ed?'Edit contact':'Add a contact'}</h3><form class="form" data-sxf="csave"><label>Name<input name="n" required maxlength="40" value="${E(ed?ed.n:'')}" autocomplete="off"></label>
   <label>Relation<select name="rel">${RELS.map(r=>`<option ${ed&&ed.rel===r?'selected':''}>${r}</option>`).join('')}</select></label>
   <label class="full">Mobile number<input name="ph" inputmode="tel" placeholder="98765 43210 or +91 98765 43210" value="${E(ed?ed.ph:'')}" autocomplete="off"></label>
   <div class="full" style="display:flex;gap:8px"><button class="btn p" type="submit">${ed?'Save changes':'Add contact'}</button>${ed?'<button class="btn s" type="button" data-sx="cedit:">Cancel</button>':''}</div></form>
   <p class="mute sm" style="margin:10px 0 0">Numbers stay on this device. DoKKo never messages them unless you press SOS and tap Send.</p></div>`}});
SX.act.cedit=([id])=>{editC=id||null;render()};
SX.act.cdel=([id])=>{const m=SX.me(),cs=contactsOf(m.id),c=cs.find(x=>x.id===id);if(!c)return;S.contacts[m.id]=cs.filter(x=>x.id!==id);SX.save();render();toast('Removed '+c.n)};
SX.chg.cnotify=([id],el)=>{const c=contactsOf(SX.me().id).find(x=>x.id===id);if(c){c.notify=el.checked;SX.save()}};
SX.chg.csave=(a,f)=>{const m=SX.me(),cs=contactsOf(m.id),fd=new FormData(f),n=String(fd.get('n')||'').trim().slice(0,40),rel=String(fd.get('rel')||'Other'),raw=String(fd.get('ph')||'').trim();
 if(!n)return;const ph=raw?phoneNorm(raw):'';if(ph===null){toast('That phone number does not look right');return}
 if(editC){const c=cs.find(x=>x.id===editC);if(c){c.n=n;c.rel=rel;c.ph=ph}editC=null;toast('Contact updated')}else{cs.push({id:uid('c'),n,rel,ph,notify:true});toast('Contact added')}
 SX.save();render()};
})();
