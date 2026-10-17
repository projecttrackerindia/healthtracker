// ===================== six · Home (Today) + Care (appointments) + tour =====================
(()=>{
'use strict';
const SX=window.SX,S=SX.S,E=SX.E,uid=SX.uid;

// ---------------------------------------------------------------- appointments are per person
SX.init(s=>{
 s.appts=s.appts||{m1:APPTS.map(a=>Object.assign({id:uid('a')},a)),
  m2:[{id:uid('a'),doc:'fk',when:'Wed · 2:30 PM',type:'In person',why:'Routine check-up'}],
  m3:[{id:uid('a'),doc:'sw',when:'Oct 21 · 11:00 AM',type:'In person',why:'Heart review'}],m4:[],m5:[]};
});
const appts=m=>(S.appts[m.id]=S.appts[m.id]||[]);
SX.apptsOf=appts;

// ---------------------------------------------------------------- Home › Today
const dayName=()=>new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long'});
const pregWeek=m=>{const p=S.preg[m.id];if(!p||!p.on||!p.lmp)return 0;return Math.max(0,Math.min(42,Math.floor((Date.now()-new Date(p.lmp+'T00:00'))/864e5/7)))};
const sevDot=c=>`<i class="sev" style="background:${c};width:12px;height:12px"></i>`;
function dosesCard(m){const ad=SX.adherence(m),next=SX.nextDoses(m);
 return `<div class="card"><div class="hd"><h3>Medicines today</h3><button class="btn s sm" data-sx="tab:rx">Open</button></div>
  ${ad.total?`<div class="sx-adh" style="padding-top:0"><div class="ring" style="--p:${ad.pct}" role="img" aria-label="${ad.pct}% taken"><b>${ad.pct}%</b></div><div><b>${ad.done} of ${ad.total} taken</b><small class="mute" style="display:block">${next.length?next.length+' still to take':'All done for today'}</small></div></div>
  ${next.slice(0,4).map(p=>`<label class="sx-dose"><input type="checkbox" data-sxc="dose:${p.x.id}:${p.j}"><span><b>${E(p.x.n)}</b><small>${E(p.x.dose)} · ${E(p.w.toLowerCase())}</small></span></label>`).join('')}${next.length>4?`<p class="mute sm" style="margin:6px 0 0">+ ${next.length-4} more</p>`:''}`:`<p class="mute" style="margin:0 0 10px">No doses due today.</p><button class="btn s sm" data-sx="medadd">Add a medicine</button>`}</div>`}
function attentionCard(m){const flags=SX.labFlags(m).slice(0,3),sug=SX.suggestions(m).filter(s=>s.st!=='ok')[0];
 const badge=(st)=>st.s==='in'?'b-ok':st.mild?'b-mid':'b-hi';
 return `<div class="card"><div class="hd"><h3>Worth a conversation</h3><button class="btn s sm" data-sx="tab:insights">Insights</button></div>
  ${flags.length?flags.map(({x,st})=>{const L=st.L;return `<button class="row" data-act="${x.t!=null?'test:'+x.t:'spec:'+L.sp}" style="text-align:left"><div class="grow"><b>${E(L.n)}: ${E(String(x.val))} ${E(L.u)}</b><small>${st.s==='high'?'Above':'Below'} the usual range · tap to see where it is in the body</small></div><span class="badge ${badge(st)}">${st.s==='high'?'High':'Low'}</span></button>`}).join(''):'<p class="mute" style="margin:0">Your latest results are all in the usual range.</p>'}
  ${sug?`<div class="sx-hint"><b>Suggested check</b><span>${E(sug.t)}. <button class="sx-lnk" data-sx="tab:insights">Discuss with your doctor</button></span></div>`:''}</div>`}
function visitCard(m){const a=appts(m)[0],d=a?DOC[a.doc]:null;
 return `<div class="card"><div class="hd"><h3>Next visit</h3><button class="btn s sm" data-sx="tab:appts">All</button></div>${d?`<div class="up" style="display:flex;gap:12px;align-items:center;margin-bottom:10px">${docAv(d)}<div class="grow"><b>${E(d.n)}</b><small class="mute" style="display:block">${E(SPI[d.sp].n)} · ${E(a.when)}</small><small class="mute" style="display:block">${E(a.type)} · ${E(a.why)}</small></div></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">${a.type==='Video call'?'<button class="btn p sm" data-toast="Joining video call… (demo)">▶ Join video call</button>':''}<button class="btn s sm" data-sx="tab:appts">Reschedule</button><button class="btn s sm" data-act="spec:${d.sp}">On body</button></div>`:`<p class="mute" style="margin:0 0 10px">No visits booked for ${E(m.name)}.</p><button class="btn p sm" data-sx="tab:appts">Book a visit</button>`}</div>`}
function bodyCard(m){const p=SX.pat(m);if(!p||!p.f.length)return '';
 return `<div class="card"><div class="hd"><h3>On the body</h3><button class="btn s sm" data-act="patient:${p.id}">Show all</button></div><p class="mute sm" style="margin:-6px 0 8px">Findings from ${E(m.name)}'s records, pinned where they are.</p>
  ${p.f.map((f,k)=>`<button class="row" data-act="finding:${p.id}:${k}" style="text-align:left">${sevDot(SEV[f.sev][0])}<div class="grow"><b>${E(f.t)}</b><small>${SPI[f.sp].e} ${E(SPI[f.sp].n)}</small></div><span class="badge ${SEV[f.sev][1]}">${SEV[f.sev][2]}</span></button>`).join('')}</div>`}
function vitalsCard(m){const p=SX.pat(m),bmi=SX.bmi(m);
 const v=(p?p.v:[]).slice(0,4);return `<div class="card"><h3>Vitals</h3><div class="stat sx-vst">${v.map(([a,b])=>vTile(a,b)).join('')}${bmi?vTile('BMI',bmi.toFixed(1)):''}</div>${bmi?`<p class="mute sm" style="margin:8px 0 0">${E(SX.bmiCat(m))}</p>`:''}</div>`}
// Home hero: heart rate with a dotted ECG pulse (speed follows the rate), plus the next two vitals and BMI
const ECGP='M0 40'+'h18q6 -9 12 0h14l5 5l7 -34l7 44l5 -15h12q10 -14 20 0h20'.repeat(8);
// status of a vital in plain words: [label, class]. Thresholds are general adult guidance (ICMR / WHO), not a diagnosis.
function vStatus(name,val){const n=String(name).toLowerCase(),t=String(val);const num=parseFloat(t);
 if(/blood pressure|^bp/.test(n)){const m=t.match(/(\d+)\s*\/\s*(\d+)/);if(!m)return null;const s=+m[1],d=+m[2];return s>=140||d>=90?['High','bad']:s>=130||d>=85?['Watch','warn']:s<90||d<60?['Low','warn']:['Good','ok']}
 if(/sugar|glucose/.test(n)){if(!num)return null;return num>=126?['High','bad']:num>=100?['Watch','warn']:num<70?['Low','warn']:['Good','ok']}
 if(/hba1c/.test(n)){if(!num)return null;return num>=6.5?['High','bad']:num>=5.7?['Watch','warn']:['Good','ok']}
 if(/heart|pulse/.test(n)){if(!num)return null;return num>100?['High','warn']:num<50?['Low','warn']:['Good','ok']}
 if(/spo2|oxygen/.test(n)){if(!num)return null;return num<92?['Low','bad']:num<95?['Watch','warn']:['Good','ok']}
 if(/temp/.test(n)){if(!num)return null;return num>=38?['Fever','bad']:num>=37.5?['Warm','warn']:['Normal','ok']}
 if(/bmi/.test(n)){if(!num)return null;return num<18.5?['Low','warn']:num<23?['Good','ok']:num<25?['Watch','warn']:['High','bad']}
 return null}
const vTile=(a,b)=>{const st=vStatus(a,b);return `<div><small>${E(a)}${st?` <i class="sx-st ${st[1]}">${E(SX.p(st[0]))}</i>`:''}</small><b>${E(b)}</b></div>`};
function heroCard(m){const p=SX.pat(m),v=p?p.v:[],hr=v.find(x=>/heart|pulse/i.test(x[0])),bpm=hr?(parseInt(hr[1])||72):72,rest=v.filter(x=>x!==hr).slice(0,2),bmi=SX.bmi(m),beat=Math.max(.35,Math.min(1.6,60/bpm)).toFixed(2),hs=vStatus('heart',bpm);
 return `<div class="card sx-hero" style="--beat:${beat}s"><div class="sx-hero-t"><div><small>${E(m.name)} · ${E(SX.p('Health snapshot'))}${hs?` <i class="sx-st ${hs[1]}">${E(SX.p(hs[0]))}</i>`:''}</small><b class="sx-hero-hr"><i></i>${bpm}<span>bpm</span></b></div><div class="sx-hero-v">${rest.map(([a,b])=>vTile(a,b)).join('')}${bmi?vTile('BMI',bmi.toFixed(1)):''}</div></div><div class="sx-ecg" aria-hidden="true"><svg viewBox="0 0 960 64" preserveAspectRatio="none"><path d="${ECGP}"/></svg></div></div>`}
function pregCard(m){if(!SX.pregOn(m))return '';const w=pregWeek(m);
 return `<div class="card"><div class="hd"><h3>Pregnancy</h3><span class="demo">WEEK ${w}</span></div><p class="mute sm" style="margin:0 0 10px">Week-by-week guide, tracker and 3D view.</p><button class="btn p sm" data-sx="tab:preg">Open Pregnancy</button></div>`}
function setupCard(m){if(m.rel!=='You'||!SX.safetySetup)return '';const st=SX.safetySetup(m),n=st.filter(x=>x[1]).length;if(n===st.length)return '';
 return `<div class="card"><div class="hd"><h3>Safety setup</h3><span class="demo">${n}/${st.length}</span></div>${st.filter(x=>!x[1]).slice(0,2).map(x=>`<button class="row" data-sx="tab:${x[2]}" style="text-align:left"><div class="grow"><b>${E(x[0])}</b></div><span>›</span></button>`).join('')}</div>`}
function quickCard(){const q=[['⬆','Add a report','tab:vault'],['💊','Order medicine','tab:finder'],['📅','Book a visit','tab:appts'],['🪪','Medical ID','tab:mid'],['🩹','First aid','tab:aid'],['🫀','Heart Lab','tab:heart']];
 return `<div class="card"><h3>Quick actions</h3><div class="sx-qa">${q.map(([i,t,a])=>`<button data-sx="${a}"><i>${i}</i><span>${t}</span></button>`).join('')}</div></div>`}
SX.reg('dash',{head:()=>{const m=SX.me(),f=m.name.split(' ')[0];return [m.rel==='You'?`Hello, ${f} 👋`:`${f}'s health`,dayName()+(m.rel==='You'?'. Here is today at a glance.':'. '+m.rel+'. Here is today at a glance.')]},
 render:()=>{const m=SX.me();return heroCard(m)+setupCard(m)+dosesCard(m)+attentionCard(m)+visitCard(m)+pregCard(m)+bodyCard(m)+vitalsCard(m)+quickCard()},
 after:()=>{}});

// ---------------------------------------------------------------- Care › Appointments
const TIMES=['09:30 AM','11:00 AM','02:30 PM','04:00 PM','06:00 PM'];
let bk={slot:1,type:'In person'};
const keepForm=()=>{const g=id=>{const e=$(id);return e?e.value:undefined};const o=bookPre||{};const d=g('#bdate'),w=g('#bwhy');if(d)o.date=d;if(w!==undefined)o.why=w;bookPre=o};
SX.reg('appts',{head:()=>['Appointments','Book by specialty, doctor and time.'],
 render:()=>{const m=SX.me(),sp=bookPre.sp||'cardio',docs=DOCS.filter(d=>d.sp===sp),doc=docs.find(d=>d.id===bookPre.doc)||docs[0],tm=new Date(Date.now()+864e5).toISOString().slice(0,10),list=appts(m),shareOn=!!S.consent.doctor_share;
  return `<div class="card wide"><div class="hd"><h3>${E(m.name)}'s visits</h3></div>${list.length?list.map(a=>{const d=DOC[a.doc];return `<div class="row">${docAv(d)}<div class="grow"><b>${E(d.n)} <small>· ${E(SPI[d.sp].n)}</small></b><small>${E(a.when)} · ${E(a.type)} · ${E(a.why)}${a.share?' · records shared':''}</small></div><button class="btn s sm" data-act="spec:${d.sp}">On body</button>${a.type==='Video call'?'<button class="btn p sm" data-toast="Joining video call… (demo)">Join</button>':''}<button class="btn s sm" data-sx="acancel:${a.id}" aria-label="Cancel appointment">✕</button></div>`}).join(''):'<div class="sx-empty">No visits booked.</div>'}</div>
  <div class="card wide"><h3>Book a visit for ${E(m.name)}</h3><div class="form"><label>Specialty<select data-sxc="bsp">${SP.filter(s=>DOCS.some(d=>d.sp===s.id)).map(s=>`<option value="${s.id}" ${s.id===sp?'selected':''}>${s.e} ${E(s.n)}</option>`).join('')}</select></label>
   <label>Doctor<select data-sxc="bdoc">${docs.map(d=>`<option value="${d.id}" ${d===doc?'selected':''}>${E(d.n)} · ${d.r}★</option>`).join('')}</select></label>
   <label>Date<input type="date" id="bdate" value="${E(bookPre.date||tm)}" min="${tm}"></label>
   <label>Visit type<span class="seg">${['In person','Video call'].map(t=>`<button type="button" class="${bk.type===t?'on':''}" data-sx="btype:${t}">${t==='Video call'?'Video':t}</button>`).join('')}</span></label>
   <label class="full">Time slot<span class="slots">${TIMES.map((s,k)=>`<button type="button" class="${bk.slot===k?'on':''}" data-sx="bslot:${k}">${s}</button>`).join('')}</span></label>
   <label class="full">Reason<input id="bwhy" maxlength="120" placeholder="e.g. Discuss my cholesterol result" value="${E(bookPre.why||'')}"></label>
   <label class="full sx-shr"><input type="checkbox" id="bshare" ${shareOn?'checked':''}><span><b>Share ${E(m.name)}'s latest reports with ${E(doc.n)} for this visit</b><small>${shareOn?'On, because sharing with doctors is allowed in Consent.':'Off unless you tick this. Your doctor sees only what you share, for this visit.'}</small></span></label></div>
   <p class="mute sm">${E(doc.n)} · ${E(doc.h)} · ${doc.x} yrs experience · sample doctor</p>
   <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn p" data-sx="dobook">Confirm booking</button><button class="btn s" data-act="spec:${sp}">See ${E(SPI[sp].n)} on the body</button></div></div>`},
 after:()=>{}});
SX.chg.bsp=(a,el)=>{keepForm();bookPre={sp:el.value,date:bookPre.date,why:bookPre.why};render()};
SX.chg.bdoc=(a,el)=>{keepForm();bookPre.doc=el.value;render()};
SX.act.btype=([t])=>{keepForm();bk.type=t;render()};
SX.act.bslot=([k])=>{keepForm();bk.slot=+k;render()};
SX.act.acancel=([id])=>{const m=SX.me();S.appts[m.id]=appts(m).filter(a=>a.id!==id);SX.save();render();toast('Visit cancelled')};
SX.act.dobook=()=>{const m=SX.me(),sp=bookPre.sp||'cardio',docs=DOCS.filter(d=>d.sp===sp),doc=docs.find(d=>d.id===bookPre.doc)||docs[0],dt=($('#bdate')||{}).value,why=(($('#bwhy')||{}).value||'').trim(),share=!!($('#bshare')||{}).checked;
 if(!dt){toast('Choose a date');return}
 const when=new Date(dt+'T00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short'})+' · '+TIMES[bk.slot];
 appts(m).unshift({id:uid('a'),doc:doc.id,when,type:bk.type,why:why||'Consultation',share});
 if(share&&!S.consent.doctor_share)SX.ledger('doctor_share',true,`Latest reports shared with ${doc.n} for the visit on ${when}`,m.id);
 SX.save();bookPre={};bk={slot:1,type:'In person'};render();toast('Booked with '+doc.n)};

// ---------------------------------------------------------------- demo tour for the six sections
{const a=(sel,t,b,act)=>[sel,t,b,act],mem=id=>SX.setActive(id);
 const T=[
 a('#stage','Your body, in context','Home keeps the 3D body beside what matters today. Drag to rotate, scroll to zoom, hover any structure for its real anatomical name. It appears only where it helps: Home, Anatomy Lab, Heart Lab and Pregnancy.',async()=>{window.__tm0=S.active;mem('m1');go('dash');A.clearFocus()}),
 a('#nav','Six sections, nothing hidden','Home, Records & Labs, Medicines, Care, Safety and Family & Privacy. Each has its own tabs, so there is one place for everything.',async()=>{go('dash')}),
 a('#page','Today at a glance','Doses to tick off, results worth discussing, the next visit, and findings pinned on the body. Everything is for the person chosen at the top.',async()=>{go('dash')}),
 a('#sxWho','One household, many people','Switch to a parent, partner or sibling. Their records, medicines and visits stay separate, and a family member sees them only if they have shared them.',async()=>{go('family')}),
 a('#page','Vault','Keep reports, prescriptions and scans. Photos and PDFs are stored privately in this browser, not on a server.',async()=>{go('vault')}),
 a('#page','Results in plain words','Each result shows where it sits against the usual range, what it can mean, and questions to ask your doctor. It never diagnoses.',async()=>{go('tests');const d=document.querySelector('.sx-res.high summary,.sx-res.low summary');if(d)d.click()}),
 a('#page','Insights and suggested checks','Results outside the usual range, trends, and checks that may be due for age, sex, BMI and pregnancy. Always framed as: discuss with your doctor.',async()=>{go('insights')}),
 a('#page','My medicines','Doses by time of day, stock left, a reorder button when it runs low, and optional reminders.',async()=>{go('rx')}),
 a('#page','Find and order, safely','Search by name or symptom word. Prescription medicines need a prescription from the Vault. Allergies from Medical ID, pregnancy and age are checked before anything goes in the basket. Here: amoxicillin is blocked because of a recorded penicillin allergy.',async()=>{SX.fsearch('amox')}),
 a('#page','Visits and sharing','Book by specialty. Reports go to the doctor only if you tick share for that visit, and each share is written to your consent history.',async()=>{bookPre={sp:'cardio'};go('appts')}),
 a('#page','SOS','One press to call 112. Hold the red button to message your emergency contacts with your location and Medical ID. Phone, SMS and your own contacts do the work.',async()=>{go('sos')}),
 a('#page','First aid, offline','Step-by-step guides for 19 emergencies, including CPR with a 110 beats-per-minute metronome.',async()=>{SX.act.aid(['cpr'])}),
 a('#page','Medical ID','Blood group, allergies, conditions and medicines. Save it as a lock-screen picture so responders can see it without unlocking your phone.',async()=>{go('mid')}),
 a('#page','Consent, always visible','Four switches control location in SOS, Medical ID in SOS, sharing with doctors and sharing prescriptions with pharmacies. Every change is logged.',async()=>{go('consent')}),
 a('#page','Export or delete everything','Download all your data as a file, or erase it from this device with one typed confirmation.',async()=>{go('data')}),
 a('#stage','Anatomy Lab','18 specialty views for patient education and learning. Only the chosen system stays solid. Here: cardiology.',async()=>{go('lab');A.setSpec('cardio');render()}),
 a('#page','Pregnancy is opt-in','The Pregnancy tab appears only after someone turns it on. Then: weekly guide, tracker, and a 3D mother and baby. DoKKo never shows or guesses the baby’s sex.',async()=>{mem('m2');if(SX.pregOn(SX.me())){go('preg');for(let k=0;k<40&&!PV.ready;k++)await wait(150);if(PS.view!=='mother')setPView('mother');setW(24)}else go('pregopt')}),
 a('#hstage','Heart Lab','A living heart: chambers squeeze in sequence, valves open and close, blood flows, and the electrical signal travels from the SA node.',async()=>{mem('m1');go('heart');for(let k=0;k<40&&!HL.UI.ready;k++)await wait(150);HL.setCut('4ch');HL.cam('4ch')}),
 a('#tourBtn','That is the tour','Everything here runs on sample data for a fictional family. Press Demo tour any time to replay it.',async()=>{if(typeof PS!=='undefined'&&PS.on)PG.exit();mem(window.__tm0||'m1');go('dash');A.clearFocus()})];
 TOUR.length=0;T.forEach(x=>TOUR.push(x))}

SX.boot();
})();
