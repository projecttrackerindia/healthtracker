// ===================== six · Medicines: my medicines, finder, orders =====================
(()=>{
'use strict';
const SX=window.SX,S=SX.S,E=SX.E,uid=SX.uid;

// ---------------------------------------------------------------- catalogue (generic names, no dosing advice)
// [id, name, strength/form, category, price(demo ₹), rx, use, preg, kid, allergy-keys, note, generic]
// preg/kid: ''=no special flag, 'ask'=talk to doctor/pharmacist first, 'no'=not advised without a doctor
const CAT=[
['Pain & fever','🌡️'],['Cold & allergy','🤧'],['Stomach','🫃'],['Vitamins & minerals','🍊'],['Skin & first aid','🩹'],['Heart & BP','❤️'],['Diabetes','🩸'],['Thyroid','🦋'],['Antibiotics','🧫'],['Breathing','🫁'],['Devices','📟']];
const NS='ibuprofen,diclofenac,nsaid,aspirin,naproxen';
const C=[
['para500','Paracetamol','500 mg tablets · strip of 15','Pain & fever',28,0,'Fever, headache, body ache','ask','ask','paracetamol,acetaminophen','Many cold and flu medicines already contain paracetamol, so check labels to avoid doubling up.','paracetamol'],
['parasyr','Paracetamol syrup','125 mg/5 mL · 60 mL','Pain & fever',34,0,'Fever and pain in children','','','paracetamol,acetaminophen','Dose depends on the child’s weight. Use the measuring cup in the pack and ask your doctor or pharmacist.','paracetamol'],
['ibu400','Ibuprofen','400 mg tablets · strip of 15','Pain & fever',32,0,'Pain, fever, inflammation','no','ask',NS,'Take with food. Not advised with stomach ulcers, kidney problems, or if you take blood thinners, unless your doctor says so.','ibuprofen'],
['diclogel','Diclofenac gel','1% · 30 g tube','Pain & fever',78,0,'Joint and muscle pain (applied on skin)','ask','ask',NS,'For skin that is intact only. Wash hands after use.','diclofenac'],
['ors','ORS powder','WHO formula · 5 sachets','Pain & fever',38,0,'Replaces fluids and salts after diarrhoea, vomiting or heat','','','','Mix with clean water exactly as the pack says. Seek care for blood in stool, high fever or if a child cannot drink.','ors'],
['cet10','Cetirizine','10 mg tablets · strip of 10','Cold & allergy',22,0,'Sneezing, runny nose, itchy eyes, hives','ask','ask','cetirizine,antihistamine','Can cause drowsiness. Do not drive after taking it until you know how it affects you.','cetirizine'],
['lor10','Loratadine','10 mg tablets · strip of 10','Cold & allergy',45,0,'Allergy symptoms, less drowsy','ask','ask','loratadine,antihistamine','Check with your doctor if you have liver problems.','loratadine'],
['saline','Saline nasal spray','0.65% · 30 mL','Cold & allergy',68,0,'Blocked or dry nose','','','','Safe to use as often as needed; do not share the bottle.','saline'],
['dxm','Cough syrup (dextromethorphan)','15 mg/5 mL · 100 mL','Cold & allergy',92,0,'Dry cough','ask','no','dextromethorphan','Not for young children. See a doctor if a cough lasts more than 2 weeks or you cough blood.','dextromethorphan'],
['antacid','Antacid gel','Aluminium + magnesium hydroxide · 170 mL','Stomach',85,0,'Heartburn and acidity','ask','ask','','Do not take at the same time as other medicines; leave about 2 hours.','antacid'],
['simeth','Simethicone drops','40 mg/mL · 15 mL','Stomach',74,0,'Gas and colic discomfort','','','','Safe for most people. See a doctor for severe or constant stomach pain.','simethicone'],
['probio','Probiotic sachets','Lactobacillus · 10 sachets','Stomach',140,0,'Gut support during or after antibiotics','','ask','','Ask your doctor if you have a weak immune system.','probiotic'],
['pan40','Pantoprazole','40 mg tablets · strip of 15','Stomach',115,1,'Acid reflux, stomach ulcers','ask','ask','pantoprazole','Usually taken before breakfast. Long-term use should be reviewed by your doctor.','pantoprazole'],
['onda4','Ondansetron','4 mg tablets · strip of 10','Stomach',48,1,'Nausea and vomiting','ask','ask','ondansetron','Can affect heart rhythm in some people; your doctor will check.','ondansetron'],
['ursod','Ursodeoxycholic acid','300 mg tablets · strip of 10','Stomach',320,1,'Gallstones, some liver conditions','ask','ask','ursodeoxycholic','Prescribed for a specific condition, with follow-up scans or blood tests.','ursodeoxycholic acid'],
['mv','Multivitamin','Daily tablets · 30','Vitamins & minerals',210,0,'General nutrition support','ask','ask','','A balanced diet comes first. Do not combine several vitamin products without asking.','multivitamin'],
['vitc','Vitamin C','500 mg chewable · 20','Vitamins & minerals',55,0,'Dietary supplement','','','','High doses can upset the stomach.','vitamin c'],
['d3soft','Vitamin D3','1000 IU softgel · 30','Vitamins & minerals',190,0,'Supports bones; low vitamin D','','','','If your vitamin D is low, ask your doctor what dose you need.','vitamin d'],
['d3sach','Vitamin D3','60,000 IU sachet · pack of 4','Vitamins & minerals',90,1,'Doctor-directed correction of low vitamin D','ask','ask','','This is a high weekly dose. Take only as your doctor directs.','vitamin d'],
['cald3','Calcium + Vitamin D3','500 mg + 250 IU tablets · 15','Vitamins & minerals',130,0,'Bone health','','ask','','Take after food. Space it from iron tablets by a few hours.','calcium'],
['b12','Vitamin B12 (methylcobalamin)','1500 mcg tablets · 10','Vitamins & minerals',108,0,'Low B12; vegetarian diets','','','','Ask your doctor to recheck B12 after a few weeks.','vitamin b12'],
['ifa','Iron + folic acid','100 mg + 500 mcg tablets · 20','Vitamins & minerals',72,0,'Low haemoglobin, pregnancy supplement','','ask','iron','Can darken stools and cause constipation. Keep away from children; iron overdose is dangerous.','iron'],
['fol5','Folic acid','5 mg tablets · strip of 10','Vitamins & minerals',32,1,'Before and during pregnancy as advised','','','folic','Your doctor chooses the dose that suits you.','folic acid'],
['omega','Omega-3','1000 mg capsules · 30','Vitamins & minerals',250,0,'Dietary supplement','ask','ask','fish,omega','Ask first if you take blood thinners.','omega-3'],
['zinc','Zinc','20 mg dispersible tablets · 10','Vitamins & minerals',24,0,'Zinc supplement; diarrhoea in children (as advised)','','','zinc','Follow the pack or your doctor.','zinc'],
['betad','Povidone-iodine solution','5% · 100 mL','Skin & first aid',64,0,'Cleaning cuts and scrapes','ask','ask','iodine,povidone','Do not use if you have a thyroid condition or iodine allergy without asking. Not for deep wounds.','povidone-iodine'],
['calam','Calamine lotion','Soothing · 100 mL','Skin & first aid',58,0,'Itching, prickly heat, mild rashes','','','','Do not apply to broken skin.','calamine'],
['clot','Clotrimazole cream','1% · 15 g','Skin & first aid',52,0,'Fungal skin infections, ring-worm','ask','ask','clotrimazole','Keep using it for the full time on the pack, even if the skin looks better.','clotrimazole'],
['band','Adhesive bandages','Assorted · 40 strips','Skin & first aid',70,0,'Small cuts and blisters','','','latex','Check for latex if you are allergic.','bandage'],
['gauze','Sterile gauze and crepe bandage','Combo pack','Skin & first aid',120,0,'Dressings and sprains','','','','Do not wrap tightly.','gauze'],
['ator10','Atorvastatin','10 mg tablets · strip of 15','Heart & BP',95,1,'High cholesterol','no','no','atorvastatin,statin','Needs regular blood tests. Tell your doctor about unexplained muscle pain.','atorvastatin'],
['rosu10','Rosuvastatin','10 mg tablets · strip of 15','Heart & BP',140,1,'High cholesterol','no','no','rosuvastatin,statin','Needs regular blood tests.','rosuvastatin'],
['amlo5','Amlodipine','5 mg tablets · strip of 15','Heart & BP',32,1,'High blood pressure, angina','ask','no','amlodipine','Can cause ankle swelling. Do not stop suddenly.','amlodipine'],
['telmi40','Telmisartan','40 mg tablets · strip of 15','Heart & BP',88,1,'High blood pressure','no','no','telmisartan,sartan','Not for use in pregnancy. Kidney function and potassium are checked.','telmisartan'],
['metf500','Metformin','500 mg tablets · strip of 20','Diabetes',26,1,'Type 2 diabetes','ask','no','metformin','Take with food. Kidney function is checked regularly.','metformin'],
['levo50','Levothyroxine','50 mcg tablets · strip of 100','Thyroid',185,1,'Underactive thyroid','','ask','levothyroxine','Take on an empty stomach, same time daily. Dose is adjusted by blood tests.','levothyroxine'],
['amoxclav','Amoxicillin + clavulanic acid','625 mg tablets · strip of 6','Antibiotics',198,1,'Bacterial infections','ask','ask','penicillin,amoxicillin,clavulan,beta-lactam','Antibiotics work only on bacteria. Take them only if prescribed, and finish the course as directed.','amoxicillin'],
['azith500','Azithromycin','500 mg tablets · strip of 3','Antibiotics',118,1,'Bacterial infections','ask','ask','azithromycin,macrolide','Take only if prescribed, and finish the course as directed.','azithromycin'],
['cotri','Sulfamethoxazole + trimethoprim','800 mg + 160 mg tablets · strip of 10','Antibiotics',68,1,'Bacterial infections, such as some urine infections','no','ask','sulfa,sulfamethoxazole,trimethoprim','Not for people with a sulfa allergy. Drink plenty of water.','sulfamethoxazole'],
['montel','Montelukast','10 mg tablets · strip of 10','Breathing',165,1,'Asthma, allergic rhinitis','ask','ask','montelukast','Tell your doctor about any mood or sleep changes.','montelukast'],
['salb','Salbutamol inhaler','100 mcg · 200 doses','Breathing',160,1,'Relieves wheeze and breathlessness in asthma','','','salbutamol,albuterol','If you need it more often than usual, or it stops working, get medical help. Carry it with you.','salbutamol'],
['thermo','Digital thermometer','Under-arm / oral','Devices',140,0,'Check body temperature','','','','A fever in a baby under 3 months needs urgent medical care.',''],
['oximeter','Pulse oximeter','Fingertip','Devices',899,0,'Check oxygen saturation and pulse','','','','Nail polish and cold fingers can give wrong readings. A normal reading does not rule out illness.',''],
['bpmon','Digital BP monitor','Upper arm','Devices',1499,0,'Check blood pressure at home','','','','Sit quietly for 5 minutes before measuring. Bring your readings to your doctor.',''],
['sanit','Hand sanitiser','70% alcohol · 500 mL','Devices',135,0,'Clean hands when soap is not available','','','','Keep away from children and flames.','']
].map(a=>({id:a[0],n:a[1],f:a[2],cat:a[3],p:a[4],rx:!!a[5],use:a[6],preg:a[7],kid:a[8],alg:a[9]?a[9].split(','):[],note:a[10],gen:a[11]}));
SX.CATALOG=C;const CI=Object.fromEntries(C.map(x=>[x.id,x]));
const catIc=n=>(CAT.find(c=>c[0]===n)||[0,'💊'])[1];

const PHARM=[{id:'gc',n:'GreenCross Pharmacy',d:'1.2 km',eta:'45–60 min',fee:30,free:499},{id:'cc',n:'CityCare Chemist',d:'2.8 km',eta:'About 2 hours',fee:40,free:499},{id:'wn',n:'Wellnest Pharmacy',d:'4.1 km',eta:'Tomorrow morning',fee:0,free:0}];
const STEPS=['Order placed','Pharmacist checks prescription','Packed','Out for delivery','Delivered'];
const STEPS_OTC=['Order placed','Packed','Out for delivery','Delivered'];
const DEMO_AT=[0,12,30,55,85]; // seconds; demo-speed, so you can watch the tracker move

// ---------------------------------------------------------------- store
SX.init(s=>{
 const mk=(n,dose,when,why,sp,by,left,extra)=>Object.assign({id:uid('md'),n,dose,when,for:why,sp,by:by||'',left,src:by?'rx':'self',gen:(C.find(c=>c.n.toLowerCase()===n.toLowerCase())||{}).gen||n.toLowerCase()},extra||{});
 s.meds=s.meds||{m1:[mk('Atorvastatin','10 mg tablet',['Night'],'Cholesterol','cardio','Dr. Sarah Wilson',18),mk('Ursodeoxycholic acid','300 mg tablet',['Morning','Night'],'Gallstones','hepato','Dr. Kiran Rao',24),mk('Vitamin D3','60,000 IU sachet',['Sunday'],'Low vitamin D','ortho','Dr. Arjun Mehta',3)],
  m2:[mk('Iron + folic acid','1 tablet',['Morning'],'Low haemoglobin','hemato','',20),mk('Vitamin D3','1000 IU softgel',['Morning'],'Low vitamin D','ortho','',24)],
  m3:[mk('Atorvastatin','20 mg tablet',['Night'],'Heart health','cardio','Dr. Sarah Wilson',26),mk('Amlodipine','5 mg tablet',['Morning'],'Blood pressure','cardio','Dr. Sarah Wilson',9)],
  m4:[mk('Calcium + Vitamin D3','1 tablet',['Morning'],'Bone health','ortho','',12),mk('Vitamin B12','1500 mcg tablet',['Morning'],'Low B12','hemato','',8)],m5:[]};
 s.taken=s.taken||{};s.cart=s.cart||[];s.orders=s.orders||[];s.addr=s.addr||'';s.rem=s.rem||{on:false,sent:{}};
 s.vault=s.vault||[];if(!s.vault.some(v=>v.id==='v7'))s.vault.push({id:'v7',m:'m1',name:'Prescription: Dr. Arjun Mehta',kind:'Prescription',date:'2026-10-08',size:0,mime:'application/pdf',file:false,demo:true,rx:'am'});
 if(!s.vault.some(v=>v.id==='v8'))s.vault.push({id:'v8',m:'m3',name:'Prescription: Dr. Sarah Wilson',kind:'Prescription',date:'2026-09-30',size:0,mime:'application/pdf',file:false,demo:true,rx:'sw'});
});

const meds=m=>(S.meds[m.id]=S.meds[m.id]||[]);
SX.medList=m=>meds(m);
const WD=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const SLOTS=['Morning','Afternoon','Evening','Night'];const SLOT_AT={Morning:8,Afternoon:14,Evening:18,Night:21};
const SLOT_IC={Morning:'🌅',Afternoon:'☀️',Evening:'🌆',Night:'🌙'};
const dueToday=w=>SLOTS.includes(w)||w===WD[new Date().getDay()];
const takenSet=m=>{const t=S.taken[m.id];const d=SX.today();if(!t||t.d!==d)S.taken[m.id]={d,s:{}};return S.taken[m.id].s};
SX.dosePlan=m=>{const t=takenSet(m),out=[];meds(m).forEach(x=>x.when.forEach((w,j)=>{if(dueToday(w))out.push({x,w,j,k:x.id+':'+j,done:!!t[x.id+':'+j]})}));return out};
SX.adherence=m=>{const p=SX.dosePlan(m);return{done:p.filter(d=>d.done).length,total:p.length,pct:p.length?Math.round(p.filter(d=>d.done).length/p.length*100):0}};
SX.nextDoses=m=>SX.dosePlan(m).filter(d=>!d.done).sort((a,b)=>(SLOT_AT[a.w]||12)-(SLOT_AT[b.w]||12));
SX.badge=SX.badge||{};SX.badge.meds=()=>{const m=SX.me();return m?SX.nextDoses(m).length:0};

// ---------------------------------------------------------------- safety checks for a (person, medicine)
SX.medWarn=(m,it)=>{const out=[],al=(SX.midOf(m.id).allergies||[]).map(a=>a.toLowerCase()),have=meds(m);
 const hit=it.alg.filter(k=>al.some(a=>a.includes(k)||k.includes(a)&&a.length>3));
 if(hit.length)out.push({lv:'stop',t:`${m.name} has a recorded allergy that matches this medicine (${al.filter(a=>it.alg.some(k=>a.includes(k)||k.includes(a))).join(', ')||hit[0]}). Do not take it. Ask your doctor for an alternative.`});
 if(m.age<12&&it.kid==='no')out.push({lv:'stop',t:`Not advised for a child of ${m.age}. Ask a paediatrician.`});
 else if(m.age<12&&it.kid==='ask')out.push({lv:'warn',t:`For a child of ${m.age}, the dose depends on weight. Ask a paediatrician or pharmacist first.`});
 if(m.age>=65&&['ibu400','diclogel','cet10','dxm'].includes(it.id))out.push({lv:'warn',t:'Older adults are more sensitive to this type of medicine. Ask your doctor or pharmacist first.'});
 if(SX.pregOn(m)){if(it.preg==='no')out.push({lv:'stop',t:'Not advised in pregnancy. Talk to your doctor before taking it.'});else if(it.preg==='ask')out.push({lv:'warn',t:'In pregnancy, check with your doctor before taking this.'})}
 else if(m.sex==='female'&&m.age>=14&&m.age<=49&&it.preg==='no')out.push({lv:'warn',t:'Not safe in pregnancy. Tell your doctor if you are pregnant or planning a pregnancy.'});
 const dup=have.find(h=>h.gen&&it.gen&&h.gen===it.gen);if(dup)out.push({lv:'warn',t:`${m.name} already has ${dup.n} in My medicines. Taking both can double the dose.`});
 if(it.alg.some(k=>NS.split(',').includes(k))){const cr=(S.results[m.id]||[]).filter(r=>r.k==='lab'&&r.key==='creat').sort((a,b)=>b.date.localeCompare(a.date))[0];const flagged=cr&&SX.labFlags&&SX.labFlags(m).some(f=>f.x.key==='creat');if(flagged)out.push({lv:'warn',t:'A recent kidney result was outside the usual range. Pain-killers of this type can affect the kidneys. Ask your doctor first.'})}
 return out};
const hasStop=ws=>ws.some(w=>w.lv==='stop');

const keepScroll=fn=>{const els=[window],a=$('#page');for(let e=a;e;e=e.parentElement)els.push(e);const pos=els.map(e=>e===window?scrollY:e.scrollTop);fn();els.forEach((e,i)=>{if(e===window)scrollTo(0,pos[i]);else e.scrollTop=pos[i]})};
// ---------------------------------------------------------------- My medicines
SX.reg('rx',{head:()=>['My medicines','Doses for today, stock left, and reminders.'],
 render:()=>{const m=SX.me(),list=meds(m),ad=SX.adherence(m),plan=SX.dosePlan(m);
  const by=SLOTS.concat(WD).map(s=>[s,plan.filter(p=>p.w===s)]).filter(([,a])=>a.length);
  return `<div class="card wide"><div class="hd"><h3>${E(m.name)}'s day</h3><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn p sm" data-sx="medadd">＋ Add medicine</button><button class="btn s sm" data-sx="tab:finder">Find & order</button></div></div>
   <div class="sx-adh"><div class="ring" style="--p:${ad.pct}" role="img" aria-label="${ad.pct}% of today's doses taken"><b>${ad.pct}%</b></div><div><b>${ad.total?`${ad.done} of ${ad.total} doses taken today`:'No doses due today'}</b><small class="mute" style="display:block;margin-top:2px">${ad.total&&ad.done<ad.total?'Next: '+SX.nextDoses(m).slice(0,3).map(d=>`${d.x.n} (${d.w.toLowerCase()})`).join(', '):ad.total?'All done. Nice work.':'Add your medicines to track doses.'}</small></div></div>
   ${by.length?`<div class="sx-slots">${by.map(([s,a])=>`<div class="sx-slot"><h4>${SLOT_IC[s]||'📅'} ${s}${SLOT_AT[s]?` <small>${SLOT_AT[s]>12?SLOT_AT[s]-12:SLOT_AT[s]} ${SLOT_AT[s]>=12?'PM':'AM'}</small>`:''}</h4>${a.map(p=>`<label class="sx-dose ${p.done?'on':''}"><input type="checkbox" data-sxc="dose:${p.x.id}:${p.j}" ${p.done?'checked':''}><span><b>${E(p.x.n)}</b><small>${E(p.x.dose)}</small></span></label>`).join('')}</div>`).join('')}</div>`:''}</div>
  <div class="card wide"><h3>All medicines <small class="mute" style="font-weight:500">${list.length}</small></h3>${list.length?list.map(x=>{const low=x.left!=null&&x.left<=7;return `<div class="row sx-med"><div class="sx-dk">💊</div><div class="grow"><b>${E(x.n)} <small>${E(x.dose)}</small></b><small>For ${E(x.for||'—')}${x.by?' · prescribed by '+E(x.by):' · self-selected'} · ${x.when.map(E).join(', ')}${x.left!=null?` · <span class="${low?'sx-low':''}">${x.left} left${low?', running low':''}</span>`:''}</small></div>
   ${x.sp?`<button class="btn s sm" data-act="spec:${x.sp}">Target organ</button>`:''}<button class="btn ${low?'p':'s'} sm" data-sx="refill:${x.id}">${low?'Reorder':'Refill'}</button><button class="btn s sm" data-sx="mededit:${x.id}" aria-label="Edit ${E(x.n)}">Edit</button></div>`}).join(''):'<div class="sx-empty">No medicines yet. Add one to track doses.</div>'}
   <p class="sx-disc">Take medicines exactly as your doctor or the label says. DoKKo tracks doses; it does not tell you what to take or change a dose.</p></div>
  <div class="card wide"><div class="hd"><h3>Reminders</h3><label class="sx-sw"><input type="checkbox" data-sxc="remtog" ${S.rem.on?'checked':''} aria-label="Remind me while DoKKo is open"><i></i></label></div>
   <p class="mute sm" style="margin:0">Morning 8 AM · Afternoon 2 PM · Evening 6 PM · Night 9 PM. Reminders appear while DoKKo is open in a tab or installed app. Phone notifications when the app is closed need the push service, which is not part of this demo.</p></div>`},
 after:()=>{}});
SX.chg.dose=([id,j],el)=>{const m=SX.me(),t=takenSet(m),k=id+':'+j,x=meds(m).find(a=>a.id===id);if(!x)return;
 if(el.checked&&!t[k]){t[k]=1;if(x.left!=null&&x.left>0)x.left--}else if(!el.checked&&t[k]){delete t[k];if(x.left!=null)x.left++}
 SX.save();keepScroll(render);SX.paintNav();};
SX.chg.remtog=(a,el)=>{S.rem.on=el.checked;if(el.checked&&'Notification' in window&&Notification.permission==='default')try{Notification.requestPermission()}catch(e){}SX.save();toast(el.checked?'Reminders on while DoKKo is open':'Reminders off')};
function remTick(){if(!S.rem.on)return;const now=new Date(),d=SX.today(),m=SX.me();if(!m)return;
 Object.keys(SLOT_AT).forEach(sl=>{const key=m.id+d+sl;if(now.getHours()===SLOT_AT[sl]&&now.getMinutes()<30&&!S.rem.sent[key]){const due=SX.dosePlan(m).filter(p=>p.w===sl&&!p.done);if(!due.length)return;S.rem.sent[key]=1;
  const msg=`${sl} medicines: ${due.map(p=>p.x.n).join(', ')}`;toast('⏰ '+msg);try{if('Notification' in window&&Notification.permission==='granted')new Notification('DoKKo',{body:msg})}catch(e){}SX.save()}})}
setInterval(remTick,30000);

// add / edit
function medForm(x){const f=x||{n:'',dose:'',when:['Morning'],for:'',by:'',left:''};
 return `<h2>${x?'Edit':'Add'} medicine</h2><form class="form" data-sxf="medsave:${x?x.id:''}"><label class="full">Name<input name="n" required maxlength="60" list="mdl" value="${E(f.n)}" autofocus autocomplete="off"><datalist id="mdl">${C.map(c=>`<option value="${E(c.n)}">`).join('')}</datalist></label>
  <label>Strength / how much<input name="dose" required maxlength="50" placeholder="e.g. 10 mg tablet" value="${E(f.dose)}"></label><label>What it is for<input name="for" maxlength="60" placeholder="e.g. Cholesterol" value="${E(f.for)}"></label>
  <div class="full"><small class="mute" style="display:block;margin-bottom:6px">When do you take it?</small><div class="chips">${SLOTS.concat(WD).map(s=>`<label class="chip ${f.when.includes(s)?'on':''}" style="cursor:pointer"><input type="checkbox" name="w" value="${s}" ${f.when.includes(s)?'checked':''} hidden onchange="this.parentNode.classList.toggle('on',this.checked)">${s}</label>`).join('')}</div></div>
  <label>Prescribed by <small>optional</small><input name="by" maxlength="60" value="${E(f.by)}"></label><label>Tablets / doses left <small>optional</small><input name="left" type="number" min="0" max="999" value="${f.left==null?'':f.left}"></label>
  <div class="full" style="display:flex;gap:8px;justify-content:space-between;flex-wrap:wrap">${x?`<button class="btn s" type="button" data-sx="meddel:${x.id}" style="color:var(--red)">Remove</button>`:'<span></span>'}<span style="display:flex;gap:8px"><button class="btn s" type="button" data-sx="closeModal">Cancel</button><button class="btn p" type="submit">Save</button></span></div></form>`}
SX.act.medadd=()=>SX.modal(medForm(null),{label:'Add medicine'});
SX.act.mededit=([id])=>{const x=meds(SX.me()).find(a=>a.id===id);if(x)SX.modal(medForm(x),{label:'Edit medicine'})};
SX.chg.medsave=([id],f)=>{const m=SX.me(),fd=new FormData(f),n=String(fd.get('n')||'').trim(),when=fd.getAll('w').filter(w=>SLOTS.includes(w)||WD.includes(w));if(!n||!when.length){toast('Add a name and at least one time');return}
 const lf=fd.get('left'),cat=C.find(c=>c.n.toLowerCase()===n.toLowerCase()),o={n:n.slice(0,60),dose:String(fd.get('dose')||'').slice(0,50),for:String(fd.get('for')||'').slice(0,60),when,by:String(fd.get('by')||'').slice(0,60),left:lf===''||lf==null?null:Math.max(0,+lf),gen:cat?cat.gen:n.toLowerCase()};
 if(id){const x=meds(m).find(a=>a.id===id);if(x){Object.assign(x,o,{src:o.by?'rx':'self'})}}else meds(m).push(Object.assign({id:uid('md'),sp:cat?({'Heart & BP':'cardio','Diabetes':'endo','Thyroid':'endo','Stomach':'gastro'}[cat.cat]||''):'',src:o.by?'rx':'self'},o));
 SX.save();SX.closeModal();render();SX.paintNav();
 const w=cat?SX.medWarn(m,cat):[];if(w.length&&!id)toast('Saved. '+w[0].t.slice(0,110))};
SX.act.meddel=([id])=>{const m=SX.me();S.meds[m.id]=meds(m).filter(a=>a.id!==id);SX.save();SX.closeModal();render();SX.paintNav();toast('Removed')};
SX.act.refill=([id])=>{const x=meds(SX.me()).find(a=>a.id===id);if(!x)return;fQ=x.n;fCat='All';go('finder')};

// ---------------------------------------------------------------- Finder
let fQ='',fCat='All',fRx='all';
const money=n=>'₹'+Math.round(n).toLocaleString('en-IN');
const cartFor=m=>S.cart.filter(c=>c.m===m.id);
function filt(){const q=fQ.trim().toLowerCase();return C.filter(c=>(fCat==='All'||c.cat===fCat)&&(fRx==='all'||(fRx==='rx')===c.rx)&&(!q||(c.n+' '+c.f+' '+c.use+' '+c.cat+' '+c.gen).toLowerCase().includes(q)))}
function tile(c,m){const w=SX.medWarn(m,c),stop=hasStop(w),inCart=S.cart.find(x=>x.id===c.id&&x.m===m.id);
 return `<div class="sx-it ${stop?'stop':''}"><div class="sx-it1"><i>${catIc(c.cat)}</i><div class="grow"><b>${E(c.n)}</b><small>${E(c.f)}</small></div>${c.rx?'<span class="badge b-mid" title="Prescription required">℞ Prescription</span>':'<span class="badge b-ok">No prescription</span>'}</div>
  <p class="sx-it2">${E(c.use)}</p>${w.length?`<div class="sx-warn ${stop?'stop':''}">${w.slice(0,2).map(x=>`<p>${stop&&x.lv==='stop'?'⛔':'⚠️'} ${E(x.t)}</p>`).join('')}</div>`:''}
  <div class="sx-it3"><b>${money(c.p)}</b><span><button class="btn s sm" data-sx="mdet:${c.id}">Details</button>${stop?'<button class="btn s sm" disabled>Not advised</button>':`<button class="btn ${inCart?'s':'p'} sm" data-sx="cartadd:${c.id}">${inCart?'In basket ✓':c.rx?'Add (needs ℞)':'Add'}</button>`}</span></div></div>`}
SX.reg('finder',{head:()=>['Find & order','Search medicines, check them against your details, and order.'],
 render:()=>{const m=SX.me(),n=cartFor(m).reduce((a,c)=>a+c.q,0),all=S.cart.reduce((a,c)=>a+c.q,0),list=filt();
  return `<div class="card wide"><div class="hd"><h3>For ${E(m.name)}</h3><button class="btn ${all?'p':'s'} sm" data-sx="cart">🛒 Basket${all?` (${all})`:''}</button></div>
   <input id="fq" type="search" placeholder="Search by name or use, e.g. fever, acidity, vitamin D" value="${E(fQ)}" aria-label="Search medicines" autocomplete="off">
   <div class="chips" style="margin-top:10px">${[['all','All'],['otc','No prescription'],['rx','Prescription (℞)']].map(([k,t])=>`<button class="chip ${fRx===k?'on':''}" data-sx="frx:${k}">${t}</button>`).join('')}</div>
   <div class="chips" style="margin-top:8px">${['All',...CAT.map(c=>c[0])].map(k=>`<button class="chip ${fCat===k?'on':''}" data-sx="fcat:${E(k)}">${k==='All'?'All':catIc(k)+' '+k}</button>`).join('')}</div>
   <p class="mute sm" style="margin:12px 0 0">Prescription (℞) medicines are supplied only against a valid prescription, checked by the pharmacist. Checks use ${E(m.name)}'s allergies${SX.pregOn(m)?', pregnancy':''}, age and current medicines. Sample catalogue and demo prices.</p></div>
  <div class="card wide" style="padding-top:12px"><div class="sx-grid" id="fgrid">${fgrid(list,m)}</div></div>
  <div class="card wide"><p class="sx-disc" style="margin:0"><b>If this is an emergency</b> (trouble breathing, chest pain, fainting, severe bleeding, suspected poisoning, a swallowed overdose), call 112 now instead of ordering. DoKKo cannot diagnose illness or recommend a dose.</p></div>`},
 after:()=>{const q=$('#fq');if(q){q.oninput=()=>{fQ=q.value;const m=SX.me();$('#fgrid').innerHTML=fgrid(filt(),m)}}}});
const fgrid=(list,m)=>list.length?list.map(c=>tile(c,m)).join(''):'<div class="sx-empty">No match. Try a symptom word like "cough", or a medicine name.</div>';
SX.fsearch=q=>{fQ=q;fCat='All';fRx='all';go('finder')};
SX.act.fcat=([k])=>{fCat=k;render()};SX.act.frx=([k])=>{fRx=k;render()};

SX.act.mdet=([id])=>{const c=CI[id],m=SX.me();if(!c)return;const w=SX.medWarn(m,c),stop=hasStop(w);
 SX.modal(`<div class="sx-it1" style="margin-bottom:8px"><i style="width:44px;height:44px;font-size:22px">${catIc(c.cat)}</i><div class="grow"><h2 style="margin:0">${E(c.n)}</h2><small class="mute">${E(c.f)} · ${E(c.cat)}</small></div></div>
  <p style="margin:8px 0"><span class="badge ${c.rx?'b-mid':'b-ok'}">${c.rx?'℞ Prescription required':'No prescription needed'}</span> <b style="margin-left:6px">${money(c.p)}</b> <small class="mute">(demo price)</small></p>
  <p><b>Used for.</b> ${E(c.use)}</p>${c.note?`<p><b>Good to know.</b> ${E(c.note)}</p>`:''}
  ${w.length?`<div class="sx-warn ${stop?'stop':''}"><b style="display:block;margin-bottom:4px">For ${E(m.name)}</b>${w.map(x=>`<p>${x.lv==='stop'?'⛔':'⚠️'} ${E(x.t)}</p>`).join('')}</div>`:`<p class="mute sm">No conflict found with ${E(m.name)}'s allergies, age or current medicines. This check is limited. Tell your doctor or pharmacist about everything you take.</p>`}
  <p class="sx-disc">Use it exactly as the pack or your doctor says. DoKKo does not give doses. In an emergency call 112.</p>
  <div style="display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap"><button class="btn s" data-sx="closeModal">Close</button>${stop?'':`<button class="btn p" data-sx="cartadd:${c.id}:x">Add to basket</button>`}</div>`,{label:c.n})};

// ---------------------------------------------------------------- basket + checkout
SX.act.cartadd=([id,fromModal])=>{const c=CI[id],m=SX.me();if(!c)return;const w=SX.medWarn(m,c);if(hasStop(w)){toast('Not advised for '+m.name);return}
 const ex=S.cart.find(x=>x.id===id&&x.m===m.id);
 if(ex){if(fromModal)SX.closeModal();SX.act.cart();return}
 const commit=()=>{S.cart.push({id,m:m.id,q:1});SX.save();SX.closeModal();render();toast(c.n+' added to basket')};
 if(w.length){SX.modal(`<h2>Check before adding</h2><p><b>${E(c.n)}</b> for <b>${E(m.name)}</b></p><div class="sx-warn">${w.map(x=>`<p>⚠️ ${E(x.t)}</p>`).join('')}</div><p class="mute sm">If you add it, discuss it with your doctor or pharmacist before taking it.</p><div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" data-sx="closeModal">Cancel</button><button class="btn p" data-sx="cartok:${id}">I understand, add it</button></div>`,{label:'Check before adding'});return}
 commit()};
SX.act.cartok=([id])=>{const m=SX.me();if(!S.cart.find(x=>x.id===id&&x.m===m.id))S.cart.push({id,m:m.id,q:1});SX.save();SX.closeModal();render();toast('Added to basket')};
SX.act.cartq=([k,d])=>{const x=S.cart[+k];if(!x)return;x.q+=+d;if(x.q<=0)S.cart.splice(+k,1);else if(x.q>10)x.q=10;SX.save();SX.act.cart(true)};
let chosen={ph:'gc',rxsel:{}};
const rxDocs=m=>S.vault.filter(v=>v.m===m.id&&v.kind==='Prescription');
const subtotal=()=>S.cart.reduce((a,c)=>a+(CI[c.id]?CI[c.id].p*c.q:0),0);
const feeOf=ph=>subtotal()>=ph.free&&ph.free?0:ph.fee;
SX.act.cart=keep=>{
 if(!S.cart.length){SX.modal(`<h2>Basket</h2><div class="sx-empty">Your basket is empty.</div><div style="display:flex;justify-content:flex-end"><button class="btn s" data-sx="closeModal">Close</button></div>`,{label:'Basket'});return}
 const ph=PHARM.find(p=>p.id===chosen.ph)||PHARM[0],sub=subtotal(),fee=feeOf(ph),needs=S.cart.map((c,i)=>({c,i,it:CI[c.id],m:SX.member(c.m)})).filter(o=>o.it&&o.it.rx);
 needs.forEach(o=>{if(!chosen.rxsel[o.i]||!S.vault.find(v=>v.id===chosen.rxsel[o.i])){const d=rxDocs(o.m)[0];chosen.rxsel[o.i]=d?d.id:''}});
 const missing=needs.some(o=>!chosen.rxsel[o.i]),consentOff=needs.length&&!S.consent.pharmacy_rx;
 const html=`<h2>Basket</h2><div class="sx-bk">${S.cart.map((c,i)=>{const it=CI[c.id],m=SX.member(c.m);if(!it||!m)return'';const w=SX.medWarn(m,it);return `<div class="sx-bi"><div class="grow"><b>${E(it.n)}</b><small>${E(it.f)} · for ${E(m.name)}</small>${it.rx?`<label class="sx-rxp">℞ Prescription<select data-sxc="cartrx:${i}">${rxDocs(m).map(v=>`<option value="${v.id}" ${chosen.rxsel[i]===v.id?'selected':''}>${E(v.name)} · ${E(SX.fmt(v.date+'T00:00'))}</option>`).join('')||'<option value="">None in Vault</option>'}</select></label>`:''}${w.length?`<small class="sx-bw">⚠️ ${E(w[0].t)}</small>`:''}</div><div class="sx-q"><button aria-label="Fewer" data-sx="cartq:${i}:-1">−</button><b>${c.q}</b><button aria-label="More" data-sx="cartq:${i}:1">+</button></div><b class="sx-pr">${money(it.p*c.q)}</b></div>`}).join('')}</div>
  ${needs.length?`<div class="sx-warn ${missing||consentOff?'stop':''}" style="margin:10px 0"><p>℞ ${needs.length>1?needs.length+' items need':'1 item needs'} a prescription. The pharmacist checks it before packing.</p>${missing?'<p>⛔ Add the prescription to the Vault (Records & Labs), then come back.</p>':''}${consentOff?`<p>⛔ Sharing prescriptions with a pharmacy is switched off. <button class="btn s sm" data-sx="rxconsent">Allow for this order</button></p>`:''}</div>`:''}
  <h4 class="sx-h4">Pharmacy <small class="mute">sample</small></h4><div class="sx-ph">${PHARM.map(p=>`<label class="${p.id===ph.id?'on':''}"><input type="radio" name="ph" ${p.id===ph.id?'checked':''} data-sxc="phsel:${p.id}"><span><b>${E(p.n)}</b><small>${p.d} · ${p.eta} · ${feeOf(p)?money(feeOf(p))+' delivery':'free delivery'}</small></span></label>`).join('')}</div>
  <label class="full sx-h4" style="display:block">Delivery address<input id="caddr" maxlength="160" placeholder="House, street, area, PIN" value="${E(S.addr)}" style="margin-top:6px;width:100%"></label>
  <div class="sx-tot"><span>Items</span><b>${money(sub)}</b><span>Delivery</span><b>${fee?money(fee):'Free'}</b><span><b>Total</b></span><b style="font-size:17px">${money(sub+fee)}</b></div>
  <p class="sx-disc">Demo checkout. No real order is placed and no money is taken. Pay on delivery.</p>
  <div style="display:flex;gap:8px;justify-content:space-between;flex-wrap:wrap"><button class="btn s" data-sx="cartclr">Empty basket</button><span style="display:flex;gap:8px"><button class="btn s" data-sx="closeModal">Keep shopping</button><button class="btn p" data-sx="place" ${missing||consentOff?'disabled':''}>Place order · ${money(sub+fee)}</button></span></div>`;
 SX.modal(html,{label:'Basket',cls:'sx-wide'})};
SX.chg.cartrx=([i],el)=>{chosen.rxsel[i]=el.value};
SX.chg.phsel=([id])=>{chosen.ph=id;const a=$('#caddr');if(a)S.addr=a.value;SX.act.cart(true)};
SX.act.cartclr=()=>{S.cart=[];chosen.rxsel={};SX.save();SX.closeModal();render();toast('Basket emptied')};
SX.act.rxconsent=()=>{S.consent.pharmacy_rx=true;SX.ledger('pharmacy_rx',true,'Allowed while placing an order',SX.me().id);SX.save();SX.act.cart(true)};
SX.act.place=()=>{const a=$('#caddr'),addr=a?a.value.trim():S.addr;if(addr.length<6){toast('Please enter a delivery address');if(a)a.focus();return}S.addr=addr;
 const ph=PHARM.find(p=>p.id===chosen.ph)||PHARM[0],items=S.cart.map((c,i)=>{const it=CI[c.id];return it?{id:c.id,n:it.n,f:it.f,q:c.q,p:it.p,rx:it.rx,m:c.m,rxdoc:it.rx?chosen.rxsel[i]:''}:null}).filter(Boolean);
 if(items.some(i=>i.rx&&!i.rxdoc)||(items.some(i=>i.rx)&&!S.consent.pharmacy_rx))return;
 const sub=items.reduce((s,i)=>s+i.p*i.q,0),fee=feeOf(ph),o={id:uid('o').toUpperCase().slice(0,8),t:Date.now(),ph:ph.n,addr,items,sub,fee,total:sub+fee,rx:items.some(i=>i.rx),for:[...new Set(items.map(i=>i.m))]};
 S.orders.unshift(o);
 if(o.rx)SX.ledger('pharmacy_rx',true,`Prescription shared with ${ph.n} for order ${o.id}`,o.for[0]);
 S.cart=[];chosen.rxsel={};SX.save();SX.closeModal();ordOpen=o.id;go('orders');toast('Order placed (demo)')};

// ---------------------------------------------------------------- Orders
let ordOpen='',ordTimer=0;
const stage=o=>{const steps=o.rx?STEPS:STEPS_OTC,el=(Date.now()-o.t)/1e3;if(o.cancel)return{i:-1,steps};const at=o.rx?DEMO_AT:[0,12,35,70];let i=0;at.forEach((s,k)=>{if(el>=s)i=k});return{i,steps}};
SX.reg('orders',{head:()=>['Orders','Track what you ordered. Sample pharmacies.'],
 render:()=>{const list=S.orders.filter(o=>o.for.some(id=>SX.viewable(SX.member(id))));
  return `<div class="card wide"><div class="hd"><h3>Your orders</h3><button class="btn p sm" data-sx="tab:finder">＋ New order</button></div>${list.length?'':'<div class="sx-empty">No orders yet. Find a medicine and add it to your basket.</div>'}</div>
  ${list.map(o=>{const{i,steps}=stage(o),done=i===steps.length-1,names=o.for.map(id=>(SX.member(id)||{}).name).filter(Boolean).join(', ');
   return `<div class="card wide sx-ord"><div class="hd"><div><h3 style="margin:0">Order ${E(o.id)}</h3><small class="mute">${E(SX.fmtT(o.t))} · ${E(o.ph)} · for ${E(names)}</small></div><span class="badge ${o.cancel?'b-hi':done?'b-ok':'b-due'}">${o.cancel?'Cancelled':done?'Delivered':steps[i]}</span></div>
   ${o.cancel?'':`<ol class="sx-tl">${steps.map((s,k)=>`<li class="${k<i?'done':k===i?(done?'done':'now'):''}"><i></i><span>${E(s)}</span></li>`).join('')}</ol>`}
   <details ${ordOpen===o.id?'open':''}><summary class="sx-more" style="cursor:pointer;font-size:12.5px;font-weight:600;color:var(--mute)">${o.items.length} item${o.items.length>1?'s':''} · ${money(o.total)}</summary>${o.items.map(x=>`<div class="row"><div class="grow"><b>${E(x.n)} <small>× ${x.q}</small></b><small>${E(x.f)}${x.rx?' · ℞ prescription attached':''}</small></div><b>${money(x.p*x.q)}</b></div>`).join('')}<p class="mute sm" style="margin:8px 0 0">Delivering to ${E(o.addr)}${o.fee?` · delivery ${money(o.fee)}`:' · free delivery'}</p></details>
   <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap"><button class="btn s sm" data-sx="reorder:${o.id}">Reorder</button>${!o.cancel&&i<2?`<button class="btn s sm" data-sx="ordcancel:${o.id}">Cancel order</button>`:''}</div></div>`}).join('')}
  ${list.length?'<p class="sx-disc" style="padding:0 4px">Demo tracker: it moves in seconds so you can see the steps. A real pharmacy would update it as they work.</p>':''}`},
 after:()=>{clearInterval(ordTimer);ordTimer=setInterval(()=>{if(page!=='orders'){clearInterval(ordTimer);return}if(S.orders.some(o=>!o.cancel&&stage(o).i<stage(o).steps.length-1)&&!document.querySelector('.sx-modal'))render();else if(!S.orders.some(o=>!o.cancel&&stage(o).i<stage(o).steps.length-1))clearInterval(ordTimer)},4000)}});
SX.act.ordcancel=([id])=>{const o=S.orders.find(x=>x.id===id);if(o){o.cancel=true;SX.save();render();toast('Order cancelled')}};
SX.act.reorder=([id])=>{const o=S.orders.find(x=>x.id===id);if(!o)return;let n=0;o.items.forEach(i=>{const m=SX.member(i.m);if(!m||!CI[i.id]||hasStop(SX.medWarn(m,CI[i.id])))return;if(!S.cart.find(c=>c.id===i.id&&c.m===i.m)){S.cart.push({id:i.id,m:i.m,q:i.q});n++}});SX.save();fRx='all';go('finder');setTimeout(()=>SX.act.cart(),50)};
})();
