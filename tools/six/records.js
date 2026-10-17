// ===================== six · Records & Labs: vault, results, insights, suggested checks =====================
(()=>{
'use strict';
const SX=window.SX,S=SX.S,E=SX.E,uid=SX.uid;

// ---------------------------------------------------------------- private file store (IndexedDB)
let dbp=null;
const db=()=>dbp||(dbp=new Promise((res,rej)=>{try{const r=indexedDB.open('dk6files',1);r.onupgradeneeded=()=>r.result.createObjectStore('f');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)}catch(e){rej(e)}}));
const tx=async(mode,fn)=>{const d=await db();return new Promise((res,rej)=>{const t=d.transaction('f',mode),r=fn(t.objectStore('f'));t.oncomplete=()=>res(r&&r.result);t.onerror=()=>rej(t.error);t.onabort=()=>rej(t.error)})};
SX.files={put:(id,blob)=>tx('readwrite',s=>s.put(blob,id)),get:id=>tx('readonly',s=>s.get(id)),del:id=>tx('readwrite',s=>s.delete(id)),clear:()=>tx('readwrite',s=>s.clear()),
 all:async()=>{const d=await db();return new Promise((res,rej)=>{const out=[],r=d.transaction('f','readonly').objectStore('f').openCursor();r.onsuccess=()=>{const c=r.result;if(c){out.push({id:c.key,blob:c.value});c.continue()}else res(out)};r.onerror=()=>rej(r.error)})}};

// ---------------------------------------------------------------- lab catalogue (plain-language, no diagnosis)
// r: [low,high] by sex (m/f) or both; null = no bound on that side
const R=(lo,hi)=>[lo,hi];
const LABS={
 hb:{n:'Haemoglobin',u:'g/dL',g:'Blood count',sp:'hemato',m:R(13,17),f:R(12,15),d:1,what:'The protein in red blood cells that carries oxygen.',
  hi:'Above the usual range. Dehydration, smoking and living at altitude can raise it. Sometimes it needs checking.',lo:'Below the usual range. It can happen with low iron, low vitamin B12 or folate, blood loss and some long-term conditions. Your doctor may suggest more tests to find out why.',ask:['What could be causing this, and do I need more tests?','Do I need to change my food or take supplements?']},
 wbc:{n:'White blood cells',u:'×10³/µL',g:'Blood count',sp:'hemato',m:R(4,11),f:R(4,11),d:1,what:'Cells that fight infection.',hi:'Above the usual range. Infection, inflammation, stress and some medicines can raise it.',lo:'Below the usual range. Some infections, medicines and bone-marrow conditions can lower it.',ask:['Is this related to a recent illness or medicine?','Should this be repeated?']},
 plt:{n:'Platelets',u:'×10³/µL',g:'Blood count',sp:'hemato',m:R(150,410),f:R(150,410),d:0,what:'Cells that help blood clot.',hi:'Above the usual range. It can follow infection, inflammation or iron deficiency.',lo:'Below the usual range. Infections such as dengue, some medicines and other conditions can lower it. Bleeding or easy bruising needs prompt medical review.',ask:['Do I need a repeat count soon?','Are there symptoms I should watch for?']},
 glu_f:{n:'Fasting glucose',u:'mg/dL',g:'Sugar',sp:'endo',m:R(70,99),f:R(70,99),d:0,what:'Sugar in the blood after 8 to 10 hours without food.',hi:'Above the usual fasting range. One reading is not a diagnosis; doctors repeat it and often check HbA1c.',lo:'Below the usual range. Skipped meals or some medicines can cause it. If you feel shaky, sweaty or faint, treat it as low blood sugar and see a doctor.',ask:['Should I repeat this or check HbA1c?','What can I change in food and activity?']},
 hba1c:{n:'HbA1c',u:'%',g:'Sugar',sp:'endo',m:R(4,5.6),f:R(4,5.6),d:1,what:'Average blood sugar over about the last 3 months.',hi:'Above the usual range (5.7% or more). Doctors read it together with other tests to decide what it means for you.',lo:'Below the usual range. It can follow recent blood loss or some blood conditions.',ask:['What does this number mean for me?','How often should I repeat it?']},
 tc:{n:'Total cholesterol',u:'mg/dL',g:'Cholesterol',sp:'cardio',m:R(null,199),f:R(null,199),d:0,what:'All the cholesterol in your blood.',hi:'Above the usual range. Doctors look at it together with LDL, HDL, blood pressure, sugar, smoking and family history.',lo:'',ask:['What is my overall heart risk?','Can food and activity bring this down?']},
 ldl:{n:'LDL cholesterol',u:'mg/dL',g:'Cholesterol',sp:'cardio',m:R(null,129),f:R(null,129),d:0,what:'The “bad” cholesterol that can build up in artery walls.',hi:'Above the usual range. Higher LDL goes with a higher chance of heart and blood-vessel problems over time. The right target depends on your other risks, so your doctor decides.',lo:'',ask:['Do I need medicine, or can I try food and activity changes first?','When should I repeat this test?']},
 hdl:{n:'HDL cholesterol',u:'mg/dL',g:'Cholesterol',sp:'cardio',m:R(40,null),f:R(50,null),d:0,what:'The “good” cholesterol that helps clear fat from the blood.',hi:'',lo:'Below the usual range. Low HDL goes with a higher chance of heart problems. Regular activity and stopping smoking can help.',ask:['What can I do to raise it?','What is my overall heart risk?']},
 tg:{n:'Triglycerides',u:'mg/dL',g:'Cholesterol',sp:'cardio',m:R(null,149),f:R(null,149),d:0,what:'A type of fat in the blood, affected by food, alcohol and sugar.',hi:'Above the usual range. Sugary food, refined carbohydrates, alcohol and weight can raise it. Very high levels need prompt medical review.',lo:'',ask:['Which foods should I cut down on?','Do I need to repeat this after fasting?']},
 alt:{n:'ALT (liver enzyme)',u:'U/L',g:'Liver',sp:'hepato',m:R(7,56),f:R(7,56),d:0,what:'An enzyme that leaks from liver cells when they are stressed.',hi:'Above the usual range. Fatty liver, alcohol, some medicines and infections can raise it. Doctors look at the trend and other tests.',lo:'',ask:['Could a medicine I take be raising this?','Do I need a liver scan or repeat test?']},
 ast:{n:'AST (liver enzyme)',u:'U/L',g:'Liver',sp:'hepato',m:R(10,40),f:R(10,40),d:0,what:'An enzyme found in the liver and muscles.',hi:'Above the usual range. Liver conditions, alcohol and hard exercise can raise it.',lo:'',ask:['Is this related to my liver, or to exercise or a medicine?']},
 creat:{n:'Creatinine',u:'mg/dL',g:'Kidney',sp:'nephro',m:R(.7,1.3),f:R(.6,1.1),d:2,what:'A waste product that healthy kidneys filter out.',hi:'Above the usual range. It can reflect how well the kidneys filter, but also muscle mass, dehydration and some medicines. A doctor interprets it with eGFR and a urine test.',lo:'Below the usual range. It is often just low muscle mass.',ask:['Do I need an eGFR or a urine test?','Could a medicine I take affect this?']},
 uric:{n:'Uric acid',u:'mg/dL',g:'Kidney',sp:'nephro',m:R(3.5,7.2),f:R(2.6,6),d:1,what:'A waste product that can form crystals in joints and kidneys when high.',hi:'Above the usual range. Some foods, alcohol, weight and some medicines raise it. Many people with high levels have no symptoms.',lo:'',ask:['Do I need to change my food?','Is any treatment needed?']},
 na:{n:'Sodium',u:'mmol/L',g:'Kidney',sp:'nephro',m:R(135,145),f:R(135,145),d:0,what:'A salt that balances water in the body.',hi:'Above the usual range. Often linked to not drinking enough fluid.',lo:'Below the usual range. Some medicines, illnesses and drinking a lot of water can cause it. Confusion or fits need urgent care.',ask:['Is this related to a medicine?','Should it be repeated soon?']},
 k:{n:'Potassium',u:'mmol/L',g:'Kidney',sp:'nephro',m:R(3.5,5.1),f:R(3.5,5.1),d:1,what:'A mineral that keeps the heart rhythm and muscles working.',hi:'Above the usual range. Kidney conditions and some medicines can raise it. A very high value needs prompt care.',lo:'Below the usual range. Vomiting, diarrhoea and some water tablets can lower it.',ask:['Should I repeat this soon?','Is any medicine affecting it?']},
 tsh:{n:'TSH (thyroid)',u:'mIU/L',g:'Thyroid',sp:'endo',m:R(.4,4),f:R(.4,4),d:2,what:'A hormone from the brain that tells the thyroid how hard to work.',hi:'Above the usual range. It can go with an underactive thyroid. Doctors confirm it with T4 and your symptoms. Pregnancy has its own ranges.',lo:'Below the usual range. It can go with an overactive thyroid or with some medicines. Doctors confirm with T3 and T4.',ask:['Do I need T3 and T4 tests?','Do I need treatment or just a repeat in a few weeks?']},
 vitd:{n:'Vitamin D (25-OH)',u:'ng/mL',g:'Vitamins & minerals',sp:'ortho',m:R(30,100),f:R(30,100),d:0,what:'Vitamin D from sun and food that keeps bones strong.',hi:'Above the usual range. This is most often from supplements taken in high amounts.',lo:'Below the usual range. Low vitamin D is common in India. Your doctor may advise sun time, food or a supplement at a dose that suits you.',ask:['What dose and for how long, if any?','When should I retest?']},
 b12:{n:'Vitamin B12',u:'pg/mL',g:'Vitamins & minerals',sp:'hemato',m:R(200,900),f:R(200,900),d:0,what:'A vitamin for nerves and red blood cells.',hi:'Above the usual range. Usually from supplements.',lo:'Below the usual range. It is more common with little or no animal food, some stomach conditions and some medicines. Tingling or numbness needs a doctor.',ask:['Do I need supplements or injections?','Could a medicine be lowering it?']},
 ca:{n:'Calcium',u:'mg/dL',g:'Vitamins & minerals',sp:'endo',m:R(8.6,10.2),f:R(8.6,10.2),d:1,what:'A mineral for bones, nerves and muscles.',hi:'Above the usual range. It can come from supplements, dehydration or gland problems.',lo:'Below the usual range. Low vitamin D or low albumin can lower it.',ask:['Is this related to vitamin D or my medicines?','Should it be repeated?']}};
SX.LABS=LABS;
const GROUPS=['Blood count','Sugar','Cholesterol','Liver','Kidney','Thyroid','Vitamins & minerals'];

// ---------------------------------------------------------------- seed data
SX.init(s=>{
 const d=(y,m,dd)=>`${y}-${String(m).padStart(2,'0')}-${String(dd).padStart(2,'0')}`;
 const L=(key,val,date,extra)=>Object.assign({id:uid('r'),k:'lab',key,val,date},extra||{});
 const F=(n,v,st,date,sp,t)=>({id:uid('r'),k:'find',n,v,st,date,sp,t});
 s.checks=s.checks||{};
 s.results=s.results||{
  m1:[L('ldl',162,d(2026,10,12),{t:0}),L('tc',231,d(2026,10,12)),L('hdl',38,d(2026,10,12)),L('tg',168,d(2026,10,12)),F('Ultrasound abdomen','2 small gallstones','Finding',d(2026,10,10),'hepato',1),L('alt',58,d(2026,10,12),{t:2}),F('ECG','Sinus rhythm, 72 bpm','Normal',d(2026,10,12),'cardio',3),
   L('hba1c',5.6,d(2026,9,28),{t:4}),L('glu_f',95,d(2026,9,28)),L('creat',.9,d(2026,9,28),{t:5}),L('hb',14.6,d(2026,9,28)),L('tsh',2.1,d(2026,9,28)),L('vitd',18,d(2026,9,28)),F('Chest X-ray','Clear lung fields','Normal',d(2026,8,30),'pulmo',6),F('Blood test (CBC)','Scheduled for tomorrow, 10:00 AM. Fasting 10 to 12 hours.','Scheduled',d(2026,10,18),'hemato',7),
   L('ldl',171,d(2026,4,9)),L('vitd',22,d(2026,4,9))],
  m2:[L('hb',11.4,d(2026,10,2)),L('tsh',4.6,d(2026,10,2)),L('vitd',16,d(2026,10,2)),L('glu_f',104,d(2026,10,2)),L('hba1c',5.5,d(2026,10,2)),L('b12',310,d(2026,10,2))],
  m3:[L('hba1c',6.8,d(2026,10,5)),L('glu_f',138,d(2026,10,5)),L('creat',1.4,d(2026,10,5)),L('ldl',118,d(2026,10,5)),L('tg',190,d(2026,10,5)),L('uric',7.9,d(2026,10,5)),L('hba1c',7.1,d(2026,6,20)),L('creat',1.3,d(2026,6,20))],
  m4:[L('hb',12.6,d(2026,9,20)),L('vitd',22,d(2026,9,20)),L('alt',62,d(2026,9,20)),L('tc',224,d(2026,9,20)),L('b12',180,d(2026,9,20)),L('ca',9.4,d(2026,9,20))],
  m5:[L('hb',15.2,d(2026,8,14)),L('wbc',6.4,d(2026,8,14)),L('vitd',24,d(2026,8,14)),L('glu_f',88,d(2026,8,14))]};
 s.vault=s.vault||[
  {id:'v1',m:'m1',name:'Lipid profile and LFT',kind:'Lab report',date:d(2026,10,12),size:0,mime:'application/pdf',file:false,demo:true},
  {id:'v2',m:'m1',name:'Ultrasound abdomen report',kind:'Scan / imaging',date:d(2026,10,10),size:0,mime:'application/pdf',file:false,demo:true},
  {id:'v3',m:'m1',name:'Prescription: Dr. Sarah Wilson',kind:'Prescription',date:d(2026,10,12),size:0,mime:'application/pdf',file:false,demo:true,rx:'sw'},
  {id:'v4',m:'m1',name:'Prescription: Dr. Kiran Rao',kind:'Prescription',date:d(2026,10,10),size:0,mime:'application/pdf',file:false,demo:true,rx:'kr'},
  {id:'v5',m:'m2',name:'Blood tests, October',kind:'Lab report',date:d(2026,10,2),size:0,mime:'application/pdf',file:false,demo:true},
  {id:'v6',m:'m3',name:'Diabetes and kidney check',kind:'Lab report',date:d(2026,10,5),size:0,mime:'application/pdf',file:false,demo:true}];
});

// ---------------------------------------------------------------- lab logic
const sexOf=m=>m.sex==='female'?'f':'m';
SX.labRange=(key,m)=>{const L=LABS[key];if(!L)return [null,null];let r=(L[sexOf(m)]||L.m).slice();
 if(key==='hb'&&SX.pregOn(m))r[0]=11;return r};
const fmtNum=(v,d)=>{const n=+v;return Number.isFinite(n)?(d!=null?n.toFixed(d):String(n)):String(v)};
const rangeText=(r,u)=>r[0]!=null&&r[1]!=null?`${r[0]}–${r[1]} ${u}`:r[1]!=null?`up to ${r[1]} ${u}`:`${r[0]} ${u} or more`;
SX.labStatus=(res,m)=>{const L=LABS[res.key],r=SX.labRange(res.key,m),v=+res.val;let s='in';if(r[0]!=null&&v<r[0])s='low';else if(r[1]!=null&&v>r[1])s='high';
 const a=r[0]!=null?r[0]:r[1]*.4,b=r[1]!=null?r[1]:r[0]*1.6,span=b-a,mn=a-span*.7,mx=b+span*.7,pos=Math.max(.02,Math.min(.98,(v-mn)/(mx-mn))),z0=(a-mn)/(mx-mn),z1=(b-mn)/(mx-mn);
 // how far outside the range, as a fraction of the range width, to sort the most out-of-range first
 const off=s==='high'&&r[1]!=null?(v-r[1])/(span||1):s==='low'&&r[0]!=null?(r[0]-v)/(span||1):0;
 return{s,r,pos,z0:r[0]==null?0:z0,z1:r[1]==null?1:z1,off,L,mild:s!=='in'&&off<.4}};
const memberResults=m=>(S.results[m.id]=S.results[m.id]||[]);
SX.latestLabs=m=>{const seen={},out=[];memberResults(m).filter(x=>x.k==='lab'&&LABS[x.key]).sort((a,b)=>b.date.localeCompare(a.date)).forEach(x=>{if(!seen[x.key]){seen[x.key]=1;out.push(x)}});return out};
SX.labFlags=m=>SX.latestLabs(m).map(x=>({x,st:SX.labStatus(x,m)})).filter(o=>o.st.s!=='in').sort((a,b)=>b.st.off-a.st.off);
const monthsSince=date=>(Date.now()-new Date(date+'T00:00'))/(864e5*30.44);
const lastOf=(m,keys)=>memberResults(m).filter(x=>x.k==='lab'&&keys.includes(x.key)).sort((a,b)=>b.date.localeCompare(a.date))[0];
const fmtD=d=>new Date(d+'T00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
const badge=(s,st)=>s==='in'?['b-ok','In range']:[st&&!st.mild?'b-hi':'b-mid',s==='high'?'Above range':'Below range'];
const sevCol=st=>st.s==='in'?'var(--green)':st.mild?'var(--amber)':'var(--red)';
const SPN=id=>SPI[id]?SPI[id].e+' '+SPI[id].n:'';

// ---------------------------------------------------------------- Vault
let vQ='',vKind='All',vDrag=0;
const KINDS=['Lab report','Prescription','Scan / imaging','Discharge summary','Vaccination','Insurance','Other'];
const KI={'Lab report':'🧪','Prescription':'℞','Scan / imaging':'🩻','Discharge summary':'🏥','Vaccination':'💉','Insurance':'🛡️','Other':'📄'};
const guessKind=n=>{n=n.toLowerCase();return /\brx\b|prescri/.test(n)?'Prescription':/xray|x-ray|mri|\bct\b|usg|ultrasound|scan|echo|ecg/.test(n)?'Scan / imaging':/discharge/.test(n)?'Discharge summary':/vaccin|immuni/.test(n)?'Vaccination':/insur|policy|claim/.test(n)?'Insurance':/lab|report|blood|cbc|lipid|hba1c|thyroid|lft|kft|sugar|glucose/.test(n)?'Lab report':'Other'};
const sizeText=b=>!b?'':b<1024*1024?Math.max(1,Math.round(b/1024))+' KB':(b/1048576).toFixed(1)+' MB';
const MAXB=15*1048576;
SX.reg('vault',{head:()=>['Vault','Reports, prescriptions and scans for the whole family.'],
 render:()=>{const m=SX.me(),all=S.vault.filter(v=>v.m===m.id),q=vQ.trim().toLowerCase(),list=all.filter(v=>(vKind==='All'||v.kind===vKind)&&(!q||(v.name+' '+v.kind).toLowerCase().includes(q))).sort((a,b)=>b.date.localeCompare(a.date));
  return `<div class="card wide"><div class="hd"><h3>${E(m.name)}'s documents <small class="mute" style="font-weight:500">${all.length}</small></h3><span class="demo">ON THIS DEVICE</span></div>
   <div class="sx-drop ${vDrag?'over':''}" id="vdrop" tabindex="0" role="button" aria-label="Add documents: choose files or drop them here"><div class="sx-dropi">⬆</div><div><b>Add reports, prescriptions or scans</b><small>PDF or photo, up to 15 MB each. Choose files or drop them here.</small></div><button class="btn p" data-sx="vpick">Choose files</button><input id="vfile" type="file" multiple accept="application/pdf,image/*" hidden></div>
   <div class="sx-vtop"><input id="vq" type="search" placeholder="Search documents…" value="${E(vQ)}" aria-label="Search documents" autocomplete="off"><div class="chips">${['All',...KINDS].map(k=>`<button class="chip ${k===vKind?'on':''}" data-sx="vkind:${E(k)}">${k==='All'?'All':KI[k]+' '+k}</button>`).join('')}</div></div>
   <div id="vlist">${vList(list,all.length)}</div>
   <p class="mute sm" style="margin:12px 0 0">Files are stored in a private area of this browser, not on a server. Clearing site data removes them, so keep your originals.</p></div>`},
 after:()=>{const z=$('#vdrop'),f=$('#vfile');if(!z)return;f.onchange=()=>{addFiles([...f.files]);f.value=''};
  z.addEventListener('dragover',e=>{e.preventDefault();z.classList.add('over')});z.addEventListener('dragleave',()=>z.classList.remove('over'));
  z.addEventListener('drop',e=>{e.preventDefault();z.classList.remove('over');addFiles([...(e.dataTransfer?e.dataTransfer.files:[])])});
  z.addEventListener('keydown',e=>{if(e.target===z&&(e.key==='Enter'||e.key===' ')){e.preventDefault();f.click()}});
  const q=$('#vq');q.oninput=()=>{vQ=q.value;const m=SX.me(),all=S.vault.filter(v=>v.m===m.id),qq=vQ.trim().toLowerCase();$('#vlist').innerHTML=vList(all.filter(v=>(vKind==='All'||v.kind===vKind)&&(!qq||(v.name+' '+v.kind).toLowerCase().includes(qq))).sort((a,b)=>b.date.localeCompare(a.date)),all.length)}}});
function vList(list,total){if(!list.length)return `<div class="sx-empty">${total?'No document matches.':'No documents yet. Add your first report above.'}</div>`;
 return list.map(v=>{const isImg=/^image\//.test(v.mime||'');return `<div class="row sx-doc"><div class="sx-dk">${KI[v.kind]||'📄'}</div><div class="grow"><b>${E(v.name)}${v.demo?' <span class="demo">Sample</span>':''}</b><small>${E(v.kind)} · ${E(fmtD(v.date))}${v.size?' · '+sizeText(v.size):''}</small></div>
  ${v.kind==='Lab report'?`<button class="btn s sm" data-sx="vvals:${v.id}">Add values</button>`:''}${v.file&&isImg?`<button class="btn s sm" data-sx="vview:${v.id}">View</button>`:''}${v.file?`<button class="btn s sm" data-sx="vdl:${v.id}">Download</button>`:''}<button class="btn s sm" data-sx="vedit:${v.id}" aria-label="Edit ${E(v.name)}">Edit</button><button class="btn s sm" data-sx="vdel:${v.id}" aria-label="Delete ${E(v.name)}">✕</button></div>`}).join('')}
SX.act.vpick=()=>{const f=$('#vfile');if(f)f.click()};
SX.act.vkind=([k])=>{vKind=k;render()};
async function addFiles(files){const m=SX.me();let ok=0,bad=0;
 for(const f of files){const okType=/^(image\/|application\/pdf)/.test(f.type)||/\.(pdf|jpe?g|png|webp|heic)$/i.test(f.name);
  if(!okType||f.size>MAXB||f.size===0||S.vault.length>=300){bad++;continue}
  const id=uid('v');try{await SX.files.put(id,f)}catch(e){toast('This browser could not store the file (storage full or private mode).');bad++;continue}
  const dt=f.lastModified?new Date(f.lastModified).toISOString().slice(0,10):SX.today();
  S.vault.push({id,m:m.id,name:f.name.replace(/\.[a-z0-9]+$/i,'').slice(0,80),kind:guessKind(f.name),date:dt,size:f.size,mime:f.type||(/\.pdf$/i.test(f.name)?'application/pdf':'image/jpeg'),file:true});ok++}
 SX.save();if(ok)toast(`Added ${ok} document${ok>1?'s':''}`+(bad?`, ${bad} skipped (PDF or image under 15 MB only)`:''));else if(bad)toast('Only PDF or image files under 15 MB can be added');render()}
SX.act.vdel=([id])=>{const v=S.vault.find(x=>x.id===id);if(!v)return;SX.modal(`<h2>Delete this document?</h2><p class="mute"><b>${E(v.name)}</b> will be removed from this device. This cannot be undone.</p><div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" data-sx="closeModal">Keep</button><button class="btn red" data-sx="vdel2:${id}">Delete</button></div>`,{label:'Delete document'})};
SX.act.vdel2=async([id])=>{const v=S.vault.find(x=>x.id===id);if(!v)return;try{if(v.file)await SX.files.del(id)}catch(e){}S.vault=S.vault.filter(x=>x.id!==id);SX.save();SX.closeModal();render();toast('Deleted')};
SX.act.vdl=async([id])=>{const v=S.vault.find(x=>x.id===id);if(!v)return;try{const b=await SX.files.get(id);if(!b){toast('The file is not on this device any more');return}const u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=(v.name||'document')+(/pdf/.test(v.mime)?'.pdf':/png/.test(v.mime)?'.png':/webp/.test(v.mime)?'.webp':'.jpg');document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),8000)}catch(e){toast('Could not read the file')}};
SX.act.vview=async([id])=>{const v=S.vault.find(x=>x.id===id);if(!v)return;try{const b=await SX.files.get(id);if(!b){toast('The file is not on this device any more');return}const u=URL.createObjectURL(b);SX.modal(`<h2 style="font-size:16px">${E(v.name)}</h2><img src="${u}" alt="${E(v.name)}" class="sx-prev"><div style="display:flex;justify-content:flex-end;margin-top:12px"><button class="btn s" data-sx="closeModal">Close</button></div>`,{label:v.name,cls:'sx-wide',onclose:()=>URL.revokeObjectURL(u)})}catch(e){toast('Could not open the file')}};
SX.act.vedit=([id])=>{const v=S.vault.find(x=>x.id===id);if(!v)return;SX.modal(`<h2>Edit document</h2><form class="form" data-sxf="vsave:${id}"><label class="full">Name<input name="n" required maxlength="80" value="${E(v.name)}" autofocus></label><label>Type<select name="k">${KINDS.map(k=>`<option ${k===v.kind?'selected':''}>${k}</option>`).join('')}</select></label><label>Date<input type="date" name="d" value="${E(v.date)}" max="${SX.today()}" required></label><div class="full" style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" type="button" data-sx="closeModal">Cancel</button><button class="btn p" type="submit">Save</button></div></form>`,{label:'Edit document'})};
SX.chg.vsave=([id],f)=>{const v=S.vault.find(x=>x.id===id);if(!v)return;const fd=new FormData(f);v.name=String(fd.get('n')||v.name).trim().slice(0,80)||v.name;v.kind=KINDS.includes(fd.get('k'))?fd.get('k'):v.kind;v.date=String(fd.get('d')||v.date);SX.save();SX.closeModal();render()};

// add values from a lab report
SX.act.vvals=([id])=>{const v=S.vault.find(x=>x.id===id);if(!v)return;labForm(v.date,id,v.name)};
SX.act.addres=()=>labForm(SX.today(),'','');
function labForm(date,doc,docName){SX.modal(`<h2>Add a result</h2><p class="mute" style="margin:0 0 12px">${docName?`From <b>${E(docName)}</b>. `:''}Type the value exactly as printed on your report. DoKKo compares it with the usual range; use the range printed on your own report if it differs.</p>
 <form class="form" data-sxf="ressave:${doc}"><label class="full">Test<select name="key" id="rkey">${GROUPS.map(g=>`<optgroup label="${g}">${Object.entries(LABS).filter(([,l])=>l.g===g).map(([k,l])=>`<option value="${k}">${l.n} (${l.u})</option>`).join('')}</optgroup>`).join('')}</select></label>
 <label>Value<input name="val" type="number" step="any" min="0" required inputmode="decimal" autofocus></label><label>Date of test<input type="date" name="d" value="${E(date)}" max="${SX.today()}" required></label>
 <div class="full" style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" type="button" data-sx="closeModal">Cancel</button><button class="btn p" type="submit">Save result</button></div></form>`,{label:'Add a result'})}
SX.chg.ressave=([doc],f)=>{const m=SX.me(),fd=new FormData(f),key=String(fd.get('key')),val=+fd.get('val'),date=String(fd.get('d'));if(!LABS[key]||!(val>=0)||!date||val>1e5){toast('Please check the value');return}
 memberResults(m).push({id:uid('r'),k:'lab',key,val,date,doc:doc||undefined});SX.save();SX.closeModal();const st=SX.labStatus({key,val},m);toast(`${LABS[key].n}: ${badge(st.s,st)[1].toLowerCase()}`);if(page==='vault')go('tests');else render()};

// ---------------------------------------------------------------- Lab results
let tFilter='all',tOpen='';
function rangeBar(st){return `<div class="sx-rng" aria-hidden="true"><i class="z" style="left:${(st.z0*100).toFixed(1)}%;width:${((st.z1-st.z0)*100).toFixed(1)}%"></i><i class="p ${st.s}" style="left:${(st.pos*100).toFixed(1)}%"></i></div>`}
function labRow(x,m){const st=SX.labStatus(x,m),L=st.L,[bc,bt]=badge(st.s,st),prev=memberResults(m).filter(y=>y.k==='lab'&&y.key===x.key&&y.id!==x.id&&y.date<x.date).sort((a,b)=>b.date.localeCompare(a.date))[0];
 const delta=prev?(+x.val-+prev.val):null,dir=delta==null||Math.abs(delta)<1e-9?'':delta>0?'up':'down';
 const body=st.s==='high'?L.hi:st.s==='low'?L.lo:'This is within the usual range for this test. A normal result does not rule out a problem if you feel unwell.';
 return `<details class="sx-res ${st.s}${st.mild?' mild':''}" ${tOpen===x.id?'open':''}><summary><div class="sx-r1"><b>${E(L.n)}</b><small>${E(fmtD(x.date))} · ${E(SPN(L.sp))}</small></div><div class="sx-r2"><b>${E(fmtNum(x.val,L.d))} <small>${E(L.u)}</small></b><small>Usual: ${E(rangeText(st.r,L.u))}</small></div><div class="sx-r3">${rangeBar(st)}</div><span class="badge ${bc}">${bt}</span></summary>
  <div class="sx-resb"><p><b>What it is.</b> ${E(L.what)}</p><p><b>${st.s==='in'?'In range.':'What this can mean.'}</b> ${E(body)}</p>${prev?`<p class="mute sm">Last time (${E(fmtD(prev.date))}): ${E(fmtNum(prev.val,L.d))} ${E(L.u)} ${dir?`· ${dir} ${E(fmtNum(Math.abs(delta),L.d))} since then`:'· no change'}</p>`:''}
  ${st.s!=='in'?`<h4>Questions to ask your doctor</h4><ul class="sx-ul">${L.ask.map(q=>`<li>${E(q)}</li>`).join('')}</ul>`:''}
  <p class="sx-disc">This is general information, not a diagnosis. Ranges differ between labs. Talk to your doctor about what your result means for you.</p>
  <div style="display:flex;gap:8px;flex-wrap:wrap">${x.t!=null?`<button class="btn s sm" data-act="test:${x.t}">View on body</button>`:`<button class="btn s sm" data-act="spec:${L.sp}">View on body</button>`}${st.s!=='in'?`<button class="btn p sm" data-sx="askdoc:${x.id}">Book a visit about this</button>`:''}<button class="btn s sm" data-sx="resdel:${x.id}" aria-label="Delete result">Delete</button></div></div></details>`}
function findRow(x,m){const cls=ST[x.st]||'b-ok';return `<div class="sx-res fnd"><div class="sx-r1"><b>${E(x.n)}</b><small>${E(fmtD(x.date))} · ${E(SPN(x.sp))}</small></div><div class="sx-r2 w"><b style="font-size:13.5px">${E(x.v)}</b></div><span class="badge ${cls}">${E(x.st)}</span><button class="btn s sm" data-act="${x.t!=null?'test:'+x.t:'spec:'+x.sp}">View on body</button></div>`}
SX.reg('tests',{head:()=>['Lab results','Every result explained in plain words.'],
 render:()=>{const m=SX.me(),all=memberResults(m).slice().sort((a,b)=>b.date.localeCompare(a.date)),flags=SX.labFlags(m);
  const shown=all.filter(x=>x.k==='find'?tFilter!=='out'&&tFilter!=='in':(tFilter==='all'||(tFilter==='out')===(SX.labStatus(x,m).s!=='in')));
  const latest=SX.latestLabs(m),outN=flags.length,inN=latest.length-outN;
  return `<div class="card wide"><div class="hd" style="margin-bottom:12px;flex-wrap:wrap;gap:8px"><h3>${E(m.name)}'s results</h3><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn p sm" data-sx="addres">＋ Add a result</button><button class="btn s sm" data-sx="tab:vault">⬆ Upload a report</button></div></div>
   <div class="stat"><div><small>Latest tests</small><b>${latest.length}</b></div><div><small>In range</small><b style="color:var(--green)">${inN}</b></div><div><small>Outside range</small><b style="color:${outN?'var(--amber)':'var(--green)'}">${outN}</b></div></div>
   <div class="chips" style="margin-top:12px">${[['all','All'],['out','Outside range'],['in','In range']].map(([k,t])=>`<button class="chip ${tFilter===k?'on':''}" data-sx="tfilt:${k}">${t}</button>`).join('')}</div></div>
  <div class="wide">${shown.length?shown.map(x=>x.k==='find'?findRow(x,m):labRow(x,m)).join(''):'<div class="card"><p class="mute" style="margin:0">Nothing here yet. Add a result from a report to see what it means.</p></div>'}</div>
  <div class="card wide"><p class="sx-disc" style="margin:0">DoKKo explains numbers in plain language. It does not diagnose anything or replace your doctor. If you feel very unwell, do not wait for a test result: call 112.</p></div>`}});
SX.act.tfilt=([k])=>{tFilter=k;render()};
SX.act.resdel=([id])=>{const m=SX.me();S.results[m.id]=memberResults(m).filter(x=>x.id!==id);SX.save();render();toast('Result deleted')};
SX.act.askdoc=([id])=>{const m=SX.me(),x=memberResults(m).find(r=>r.id===id);if(!x)return;const L=LABS[x.key];const sp=L.sp;bookPre={sp,why:`Discuss ${L.n} ${fmtNum(x.val,L.d)} ${L.u} (${fmtD(x.date)})`};go('appts')};

// ---------------------------------------------------------------- Insights + suggested checks
const hasCond=(m,re)=>{const p=SX.pat(m),d=SX.midOf?SX.midOf(m.id):null;return !!((p&&p.f.some(f=>re.test(f.t)))||(d&&d.conditions.some(c=>re.test(c))))};
function suggestions(m){const out=[],a=m.age,fem=m.sex==='female',bmi=SX.bmi(m)||0,preg=SX.pregOn(m),w=preg?Math.max(0,Math.floor((Date.now()-new Date(S.preg[m.id].lmp+'T00:00'))/864e5/7)):0;
 const flags=SX.labFlags(m),flagged=k=>flags.some(f=>f.x.key===k),done=id=>(S.checks[m.id]||{})[id];
 const add=(id,t,why,every,tag,sp,keys,months)=>{let last=null,st='due';if(keys){const r=lastOf(m,keys);if(r){last=r.date;if(months&&monthsSince(r.date)<months)st='ok'}}const d=done(id);if(d&&months&&(Date.now()-d)/(864e5*30.44)<months){st='ok';last=new Date(d).toISOString().slice(0,10)}else if(d&&!months){st='ok';last=new Date(d).toISOString().slice(0,10)}
  out.push({id,t,why,every,tag,sp,st,last})};
 if(a<18){add('child',`Growth and vaccination check`,`Children are measured and their vaccine record is reviewed at regular visits. Ask your paediatrician which vaccines are due under the national schedule.`,'Every year','Prevention','hepato',null,12);out[out.length-1].sp='endo';return out}
 if(a>=18)add('bp','Blood pressure check','High blood pressure often has no symptoms, so it is found by measuring.',a>=40||bmi>=25?'At least every year':'Every 1–2 years','Screening','cardio',null,a>=40||bmi>=25?12:18);
 if(a>=30||flagged('ldl')||flagged('tc'))add('lipid',flagged('ldl')?'Repeat lipid profile':'Lipid profile',flagged('ldl')||flagged('tc')?'Your last cholesterol result was outside the usual range. Doctors usually repeat it after a few months of treatment or lifestyle changes.':'Cholesterol is a common, silent heart risk, and it often starts earlier in Indians.',flagged('ldl')||flagged('tc')?'Often every 3–6 months until settled':'Every 1–3 years',flagged('ldl')||flagged('tc')?'Follow-up':'Screening','cardio',['ldl','tc','hdl','tg'],flagged('ldl')||flagged('tc')?4:24);
 if(a>=30){const hi=flagged('hba1c')||flagged('glu_f')||bmi>=23;add('sugar',hi&&(flagged('hba1c')||flagged('glu_f'))?'Repeat blood sugar check':'Diabetes check (HbA1c or fasting sugar)',flagged('hba1c')||flagged('glu_f')?'A recent sugar result was above the usual range. One reading is not a diagnosis; your doctor will decide what to repeat.':bmi>=23?'Your BMI is above the healthy range for Asians, which raises the chance of diabetes.':'Diabetes is common in India and often has no symptoms in the early years.',hi?'Every year':'Every 3 years',hi?'Follow-up':'Screening','endo',['hba1c','glu_f'],hi?12:36)}
 if(fem&&a>=14&&a<=49&&!preg)add('hb','Haemoglobin (blood count)','Iron deficiency anaemia is very common in women of reproductive age.','Every year','Screening','hemato',['hb'],12);
 if(flagged('hb')&&(!fem||preg||a>49))add('hb2','Follow-up for low haemoglobin','Your last haemoglobin was outside the usual range.','Your doctor will advise','Follow-up','hemato',['hb'],3);
 if((fem&&(hasCond(m,/polycystic|pcos/i)||preg))||flagged('tsh'))add('tsh',flagged('tsh')?'Repeat thyroid test (TSH)':'Thyroid test (TSH)',flagged('tsh')?'Your last TSH was outside the usual range. Doctors usually repeat it and may add T3 and T4.':preg?'A thyroid check is usually offered early in pregnancy. Pregnancy has its own TSH ranges.':'Thyroid problems are more common with irregular cycles.',flagged('tsh')?'In 6–8 weeks, or as advised':'When your doctor advises',flagged('tsh')?'Follow-up':'Screening','endo',['tsh'],flagged('tsh')?2:12);
 if(flagged('vitd'))add('vitd','Recheck vitamin D','Your vitamin D was below the usual range. Doctors usually recheck about 3 months after starting treatment.','After about 3 months','Follow-up','ortho',['vitd'],3);
 if(a>=60||flagged('creat')||flagged('hba1c')&&hasCond(m,/diabet/i)||hasCond(m,/diabet|hypertension|kidney/i))add('kidney','Kidney check (creatinine, eGFR and urine albumin)',flagged('creat')?'Your last creatinine was outside the usual range.':'Kidney checks are recommended every year for people over 60 or with diabetes or high blood pressure.','Every year',flagged('creat')?'Follow-up':'Screening','nephro',['creat'],flagged('creat')?3:12);
 if(flagged('alt')||flagged('ast')||hasCond(m,/fatty liver/i))add('liver','Liver check (LFT and ultrasound)',flagged('alt')||flagged('ast')?'A liver enzyme was above the usual range.':'Fatty liver should be followed up.','Every 6–12 months','Follow-up','hepato',['alt','ast'],6);
 if(fem&&a>=30&&a<=65&&!preg)add('cervix','Cervical screening (Pap smear, HPV test or VIA)','Regular screening can find early changes. Ask your doctor which test and how often is right for you.','Every 3–5 years, as advised','Screening','obgyn',null,36);
 if(fem&&a>=30)add('breast',a>=40?'Breast check and mammography discussion':'Clinical breast examination',a>=40?'From about 40 to 45, doctors discuss mammography. Guidelines differ, so ask what suits your risk.':'A clinician can check your breasts at routine visits, and you should know what is normal for you.',a>=40?'As advised, often every 1–2 years':'At routine check-ups','Screening','breast',null,a>=40?24:12);
 if(!fem&&a>=50)add('psa','Prostate health discussion (PSA)','Whether to test is a personal decision. A urologist can explain benefits and limits for you.','Discuss with your doctor','Discuss','uro',null,24);
 if(a>=45)add('colon','Bowel cancer screening discussion','From about 45 to 50, doctors discuss a stool test or colonoscopy. Ask which is right for you.','As advised','Discuss','gastro',null,36);
 if(fem&&a>=50)add('bone','Bone density discussion (DEXA)','Bone thinning becomes more common after menopause. Ask whether a bone-density scan makes sense for you.','As advised','Discuss','ortho',null,36);
 if(a>=40)add('eyes','Eye check',hasCond(m,/diabet/i)||flagged('hba1c')?'Diabetes can affect the eyes, so a yearly dilated eye exam is advised.':'Eye pressure and other changes are more common after 40.',hasCond(m,/diabet/i)?'Every year':'Every 1–2 years','Screening','eye',null,hasCond(m,/diabet/i)?12:18);
 add('vax','Vaccines: ask what is due','A tetanus booster is usually needed every 10 years, and a yearly flu shot is advised for many adults. Older adults can ask about pneumonia and shingles vaccines.','Review once a year','Prevention','pulmo',null,12);
 if(preg){const P=(id,t,why,every,from,to)=>{if(w>=from&&w<=to)add('p-'+id,t,why,every,'Pregnancy','obgyn',null,0)};
  P('visits','Antenatal visits','Regular visits with your doctor check blood pressure, weight and growth. Go earlier if anything worries you.','As your doctor schedules',3,40);
  P('early','First-visit blood tests','These usually include blood group and Rh, haemoglobin, thyroid, blood sugar and infection screening. Your doctor decides which.','Once, early',3,13);
  P('nt','Early scans (dating and nuchal)','Scans around 6 to 9 weeks and 11 to 14 weeks check dates and early development.','As your doctor advises',6,14);
  P('anom','Detailed mid-pregnancy scan','A detailed scan, usually at 18 to 22 weeks, checks how the baby is growing and developing.','Once',17,23);
  P('ogtt','Glucose tolerance test','Checks for sugar problems in pregnancy, usually between 24 and 28 weeks.','Once, 24–28 weeks',23,29);
  P('tdap','Tetanus and whooping cough vaccine','Ask your doctor about vaccines advised in pregnancy, usually between 27 and 36 weeks.','Each pregnancy',26,37);
  P('hb3','Haemoglobin check','Iron needs rise in pregnancy, so haemoglobin is checked again in later months.','Each trimester',3,40);
  P('growth','Growth scan and position check','Often done around 32 to 36 weeks to see growth, position and fluid.','As your doctor advises',31,37);
  P('rh','Rh blood group follow-up','If your blood group is Rh-negative, ask your doctor about the antibody test and anti-D.','If Rh-negative',27,40)}
 return out}
SX.suggestions=suggestions;
function sugRow(s){const ok=s.st==='ok';return `<div class="row sx-sug ${ok?'ok':''}"><div class="sx-sugi">${ok?'✓':SPI[s.sp]?SPI[s.sp].e:'🩺'}</div><div class="grow"><b>${E(s.t)} <span class="demo">${E(s.tag)}</span></b><small>${E(s.why)}</small><small class="sx-ev">${E(s.every)}${s.last?` · last: ${E(fmtD(s.last))}`:''}</small></div>
 <div class="sx-sugb">${ok?'<span class="badge b-ok">Up to date</span>':`<button class="btn p sm" data-sx="sugbook:${s.id}">Book</button><button class="btn s sm" data-sx="sugdone:${s.id}">I did this</button>`}</div></div>`}
SX.reg('insights',{head:()=>['Insights','What changed, what to ask, and which checks may be due.'],
 render:()=>{const m=SX.me(),flags=SX.labFlags(m),sug=suggestions(m),due=sug.filter(s=>s.st!=='ok'),okk=sug.filter(s=>s.st==='ok');
  const trend=Object.keys(LABS).map(k=>{const xs=memberResults(m).filter(x=>x.k==='lab'&&x.key===k).sort((a,b)=>a.date.localeCompare(b.date));return xs.length>=2?xs:null}).filter(Boolean);
  return `<div class="card wide"><div class="hd"><h3>For ${E(m.name)}</h3><span class="demo">NOT A DIAGNOSIS</span></div>
   <p style="margin:0 0 4px">${flags.length?`<b>${flags.length} recent result${flags.length>1?'s are':' is'} outside the usual range.</b> That is a reason to talk to your doctor, not a reason to worry on your own.`:`<b>Your latest results are all in the usual range.</b> Keep up your routine checks.`}</p></div>
  ${flags.length?`<div class="card wide"><h3>Worth a conversation</h3>${flags.slice(0,6).map(({x,st})=>{const L=st.L,[bc,bt]=badge(st.s,st);return `<div class="row sx-flag"><i class="sev" style="background:${sevCol(st)}"></i><div class="grow"><b>${E(L.n)}: ${E(fmtNum(x.val,L.d))} ${E(L.u)} <span class="badge ${bc}">${bt}</span></b><small>${E(st.s==='high'?L.hi:L.lo)}</small></div><div class="sx-sugb"><button class="btn p sm" data-sx="askdoc:${x.id}">Book a visit</button><button class="btn s sm" data-sx="seeres:${x.id}">Details</button></div></div>`}).join('')}</div>`:''}
  ${trend.length?`<div class="card"><h3>Trends</h3>${trend.slice(0,5).map(xs=>{const L=LABS[xs[0].key],vals=xs.map(x=>+x.val),mn=Math.min(...vals),mx=Math.max(...vals),span=(mx-mn)||1,pts=vals.map((v,i)=>`${(i/(vals.length-1)*100).toFixed(1)},${(24-((v-mn)/span)*20).toFixed(1)}`).join(' '),last=xs[xs.length-1],prev=xs[xs.length-2],st=SX.labStatus(last,m);return `<div class="row"><div class="grow"><b>${E(L.n)}</b><small>${E(fmtD(prev.date))} → ${E(fmtD(last.date))}</small></div><svg class="sx-spark" viewBox="0 0 100 26" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${st.s==='in'?'var(--green)':'var(--amber)'}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg><div style="text-align:right"><b>${E(fmtNum(last.val,L.d))}</b><small>${E(L.u)}</small></div></div>`}).join('')}</div>`:''}
  <div class="card wide"><div class="hd"><h3>Suggested checks</h3><span class="demo">DISCUSS WITH YOUR DOCTOR</span></div><p class="mute sm" style="margin-top:-6px">Based on ${E(m.name)}'s age${m.sex==='female'?', sex':''}${SX.bmi(m)?', BMI':''}${SX.pregOn(m)?', pregnancy':''} and past results. These are common prompts, not instructions: your doctor knows your full history.</p>
   ${due.length?due.map(sugRow).join(''):'<div class="sx-empty">Nothing is due right now.</div>'}${okk.length?`<details class="sx-more"><summary>Up to date (${okk.length})</summary>${okk.map(sugRow).join('')}</details>`:''}</div>`}});
SX.act.seeres=([id])=>{tOpen=id;tFilter='all';go('tests')};
SX.act.sugdone=([id])=>{const m=SX.me();S.checks[m.id]=S.checks[m.id]||{};S.checks[m.id][id]=Date.now();SX.save();render();toast('Marked as done')};
SX.act.sugbook=([id])=>{const m=SX.me(),s=suggestions(m).find(x=>x.id===id);if(!s)return;bookPre={sp:s.sp,why:s.t};go('appts')};
})();
