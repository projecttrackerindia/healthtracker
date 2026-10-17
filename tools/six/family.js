// ===================== six · Family & Privacy: household, consent, your data, settings =====================
(()=>{
'use strict';
const SX=window.SX,S=SX.S,E=SX.E,uid=SX.uid,D=SX.D;

SX.init(s=>{s.preg=s.preg||{};s.checks=s.checks||{}});

// ---------------------------------------------------------------- pregnancy opt-in
SX.syncPreg=()=>{const m=SX.me(),p=S.preg[m.id];SX.paintGates();if(!p||!p.on)return;
 try{PROF.name=m.name;PROF.lmp=p.lmp;if(m.w)PROF.wt=m.w;if(m.h)PROF.ht=m.h;saveProf()}catch(e){console.warn('preg sync',e)}};
const pregHolder=()=>S.members.find(x=>SX.pregOn(x));
const weeksFrom=lmp=>Math.floor((Date.now()-new Date(lmp+'T00:00'))/864e5/7);
SX.pregOptHTML=m=>{
 if(!SX.canPreg(m))return `<div class="card"><h3>Pregnancy tracking</h3><p class="mute">Pregnancy tracking is only offered for female profiles aged 14 to 55. You can change ${E(m.name)}'s details in Family &amp; Privacy → Family.</p><button class="btn s" data-sx="tab:family">Open Family</button></div>`;
 const other=pregHolder();
 if(other&&other.id!==m.id)return `<div class="card"><h3>Pregnancy tracking</h3><p class="mute">Pregnancy tracking is on for <b>${E(other.name)}</b>. This build tracks one pregnancy per device. Switch to ${E(other.name)} to see it, or turn it off there first.</p><button class="btn p" data-sx="who:${other.id}">Switch to ${E(other.name)}</button></div>`;
 return `<div class="card sx-pregopt"><div class="sx-pg-i">🤰</div><h3>Pregnancy tracking for ${E(m.name)}</h3><p class="mute" style="margin-top:-6px">Optional. Turn it on only if it is useful to you.</p>
 <ul class="sx-ul"><li>A week-by-week guide with a 3D mother and baby, food, water, symptoms and warning signs.</li><li>Kick counter, contraction timer, birth plan and simple trackers.</li><li>It never shows or guesses the baby's sex.</li><li>It is information, not a diagnosis. Discuss everything with your doctor.</li><li>Everything stays on this device. You can turn it off or delete it any time.</li></ul>
 <button class="btn p" data-sx="pregon">Turn on pregnancy tracking</button></div>`};
SX.reg('pregopt',{head:()=>[SX.t('tab.preg'),'Optional tracking for pregnancy.'],render:()=>SX.pregOptHTML(SX.me())});
SX.act.pregon=()=>{const m=SX.me();if(!SX.canPreg(m))return;const tm=SX.today();
 SX.modal(`<h2>Turn on pregnancy tracking</h2><p class="mute" style="margin:0 0 12px">For ${E(m.name)}. The dates are used only to work out the week of pregnancy.</p>
 <form data-sxf="pregsave" class="form"><label class="full">I know my…<span class="seg"><button type="button" class="on" data-sx="pregmode:lmp" id="pm-lmp">Last period date</button><button type="button" data-sx="pregmode:edd" id="pm-edd">Due date</button></span></label>
 <label class="full"><span id="pdl">First day of last period</span><input type="date" name="d" required max="${tm}" value=""></label>
 <label class="full" style="display:flex;gap:10px;align-items:flex-start;font-size:13px;color:var(--ink);font-weight:500"><input type="checkbox" name="ok" required style="width:auto;margin-top:3px"><span>I understand this is for information and is not medical advice, and I want to turn pregnancy tracking on.</span></label>
 <div class="full" style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" type="button" data-sx="closeModal">Cancel</button><button class="btn p" type="submit">Turn on</button></div></form>`,{label:'Pregnancy tracking'});
 pregMode='lmp'};
let pregMode='lmp';
SX.act.pregmode=([k])=>{pregMode=k;$('#pm-lmp').classList.toggle('on',k==='lmp');$('#pm-edd').classList.toggle('on',k==='edd');$('#pdl').textContent=k==='lmp'?'First day of last period':'Expected due date';
 const i=$('.sx-sheet input[name=d]');const tm=new Date(),f=n=>new Date(tm.getTime()+n*864e5).toISOString().slice(0,10);if(k==='lmp'){i.max=SX.today();i.min=f(-293);}else{i.min=SX.today();i.max=f(280)}i.value=''};
SX.chg.pregsave=(a,f)=>{const m=SX.me(),fd=new FormData(f),d=String(fd.get('d')||'');if(!d||!fd.get('ok'))return;
 let lmp=d;if(pregMode==='edd')lmp=new Date(new Date(d+'T00:00').getTime()-280*864e5).toISOString().slice(0,10);
 const w=weeksFrom(lmp);if(w<0||w>42){toast('That date gives '+(w<0?'a date in the future':'more than 42 weeks')+'. Please check it.');return}
 S.preg[m.id]={on:true,lmp,t:Date.now()};SX.ledger('pregnancy',true,'Pregnancy tracking turned on for '+m.name,m.id);SX.save();SX.closeModal();SX.syncPreg();toast('Pregnancy tracking is on');
 go('preg')};
SX.act.pregoff=()=>{const m=SX.me();SX.modal(`<h2>Turn off pregnancy tracking?</h2><p class="mute">The Pregnancy tab will be hidden. Your logs (kicks, water, readings) stay on this device until you delete them in Family &amp; Privacy → My data.</p><div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" data-sx="closeModal">Keep it on</button><button class="btn red" data-sx="pregoff2">Turn off</button></div>`,{label:'Turn off pregnancy tracking'})};
SX.act.pregoff2=()=>{const m=SX.me();if(S.preg[m.id])S.preg[m.id].on=false;SX.ledger('pregnancy',false,'Pregnancy tracking turned off for '+m.name,m.id);SX.save();SX.closeModal();SX.paintGates();if(page==='preg')go('dash');else render()};

// ---------------------------------------------------------------- Family page
let famEdit=null;
const sexIc=s=>s==='female'?'♀':'♂';
function memberRow(m){const on=m.id===S.active,p=SX.pat(m),b=SX.bmi(m);
 return `<div class="row sx-mem ${on?'on':''}">${SX.avatar(m,46)}<div class="grow"><b>${E(m.name)} ${on?'<span class="demo">Viewing</span>':''}${SX.viewable(m)?'':' <span class="demo">Private</span>'}${SX.pregOn(m)?' <span class="demo" style="color:#e0457f">🤰 Pregnancy</span>':''}</b><small>${E(m.rel)} · ${m.age} yrs · ${sexIc(m.sex)}${b?` · BMI ${b.toFixed(1)}`:''}${p?` · ${p.f.length} findings`:''}</small></div>
 ${on?'':`<button class="btn s sm" data-sx="who:${m.id}">View</button>`}<button class="btn s sm" data-sx="fedit:${m.id}">Edit</button></div>`}
const RELS=['You','Spouse','Mother','Father','Son','Daughter','Brother','Sister','Grandmother','Grandfather','Other'];
function memberForm(m){const nw=!m;m=m||{name:'',rel:'Other',age:'',sex:'female',w:'',h:''};
 return `<div class="card wide"><div class="hd"><h3>${nw?'Add a family member':'Edit '+E(m.name)}</h3>${nw?'':`<button class="btn s sm" data-sx="fedit:">Cancel</button>`}</div>
 <form class="form" data-sxf="fsave:${nw?'':m.id}"><label>Name<input name="name" required maxlength="40" value="${E(m.name)}" autocomplete="off"></label>
 <label>Relation<select name="rel">${RELS.filter(r=>r!=='You'||m.rel==='You').map(r=>`<option ${m.rel===r?'selected':''}>${r}</option>`).join('')}</select></label>
 <label>Age (years)<input name="age" type="number" min="0" max="120" step="1" required value="${E(m.age)}" inputmode="numeric"></label>
 <label>Body model to show<select name="sex"><option value="female" ${m.sex==='female'?'selected':''}>Female anatomy</option><option value="male" ${m.sex==='male'?'selected':''}>Male anatomy</option></select></label>
 <label>Weight (kg) <small>optional</small><input name="w" type="number" min="2" max="300" step="0.1" value="${E(m.w||'')}" inputmode="decimal"></label>
 <label>Height (cm) <small>optional</small><input name="h" type="number" min="30" max="250" step="1" value="${E(m.h||'')}" inputmode="numeric"></label>
 <div class="full" style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn p" type="submit">${nw?'Add member':'Save changes'}</button>${!nw&&m.rel!=='You'?`<button class="btn s" type="button" data-sx="fdel:${m.id}" style="color:var(--red)">Remove member…</button>`:''}</div></form>
 <p class="mute sm" style="margin:10px 0 0">Used for age-aware suggestions and the right 3D body. For a child, you manage their records as a guardian.</p></div>`}
SX.reg('family',{head:()=>['Family','Everyone whose health you look after.'],
 render:()=>{const m=SX.me(),p=SX.pat(m),b=SX.bmi(m);
  const adding=famEdit==='new',ed=famEdit&&famEdit!=='new'?SX.member(famEdit):null;
  const detail=`<div class="card"><div class="hd"><div style="display:flex;gap:12px;align-items:center">${SX.avatar(m,54)}<div><h3 style="margin:0">${E(m.name)}</h3><small class="mute">${E(m.rel)} · ${m.age} years · ${m.sex==='female'?'Female':'Male'} anatomy</small></div></div></div>
   <div class="stat" style="margin-top:12px">${p?p.v.slice(0,3).map(([a,v])=>`<div><small>${E(a)}</small><b>${E(v)}</b></div>`).join(''):''}${m.w?`<div><small>Weight</small><b>${E(m.w)} kg</b></div>`:''}${m.h?`<div><small>Height</small><b>${E(m.h)} cm</b></div>`:''}${b?`<div><small>BMI</small><b>${b.toFixed(1)}</b></div>`:''}</div>
   ${b?`<p class="mute sm" style="margin:8px 0 0">${E(SX.bmiCat(b))} (Asia-Pacific cut-offs). BMI is a rough guide only; talk to your doctor about what is right for you.</p>`:''}
   ${p&&p.f.length?`<h4>Findings on ${E(m.name)}'s body</h4>${p.f.map((f,k)=>`<button class="row" data-act="finding:${p.id}:${k}"><i class="sev" style="background:${SEV[f.sev][0]};width:14px;height:14px"></i><div class="grow"><b>${E(f.t)}</b><small>${E(f.note)}</small></div><span class="badge ${SEV[f.sev][1]}">${SEV[f.sev][2]}</span></button>`).join('')}<p class="mute sm" style="margin:6px 0 0">Sample findings. They are shared for your care team to review, not a diagnosis.</p>`:`<p class="mute sm" style="margin:12px 0 0">No findings recorded for ${E(m.name)} yet.</p>`}
   ${SX.canPreg(m)?`<h4>Pregnancy</h4>${SX.pregOn(m)?`<div class="row"><div style="font-size:22px">🤰</div><div class="grow"><b>Tracking is on</b><small>Week ${Math.max(0,weeksFrom(S.preg[m.id].lmp))} · opt-in, stored on this device</small></div><button class="btn s sm" data-sx="tab:preg">Open</button><button class="btn s sm" data-sx="pregoff">Turn off</button></div>`:`<div class="row"><div style="font-size:22px">🤰</div><div class="grow"><b>Pregnancy tracking is off</b><small>Optional. You choose.</small></div><button class="btn s sm" data-sx="pregon">Turn on…</button></div>`}`:''}</div>`;
  return `<div class="card"><div class="hd"><h3>Household</h3><span class="demo">SAMPLE FAMILY</span></div>${S.members.map(memberRow).join('')}<button class="btn s w" data-sx="fedit:new">＋ Add a family member</button></div>${detail}${adding?memberForm(null):ed?memberForm(ed):''}`}});
SX.act.fedit=([id])=>{famEdit=id||null;render();if(famEdit)setTimeout(()=>{const f=$('#page form');if(f)f.scrollIntoView({behavior:'smooth',block:'center'})},50)};
SX.chg.fsave=([id],f)=>{const fd=new FormData(f),name=String(fd.get('name')||'').trim().slice(0,40),age=Math.round(+fd.get('age')),w=+fd.get('w')||0,h=+fd.get('h')||0;
 if(!name||!(age>=0&&age<=120)){toast('Please check the name and age');return}if(w&&(w<2||w>300)||h&&(h<30||h>250)){toast('Please check weight and height');return}
 const sex=fd.get('sex')==='male'?'male':'female',rel=String(fd.get('rel')||'Other');
 if(id){const m=SX.member(id);Object.assign(m,{name,age,sex,rel:m.rel==='You'?'You':rel,w,h,av:name.slice(0,2).toUpperCase()});const p=SX.pat(m);if(p){p.n=name;p.age=age}toast('Saved '+name);
  if(sex!==m.sex)SX.pendingModel=true}
 else{const n={id:uid('m'),pid:null,name,rel,age,sex,w,h,av:name.slice(0,2).toUpperCase(),c:['','m','g','y'][S.members.length%4],shared:true};S.members.push(n);toast(name+' added')}
 SX.ledger('member',true,(id?'Updated ':'Added ')+name,id||'all');famEdit=null;SX.save();SX.syncPreg();render();SX.paintWho()};
SX.act.fdel=([id])=>{const m=SX.member(id);if(!m||m.rel==='You')return;SX.modal(`<h2>Remove ${E(m.name)}?</h2><p class="mute">This deletes ${E(m.name)}'s documents, results, medicines, contacts and Medical ID from this device. It cannot be undone.</p><div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn s" data-sx="closeModal">Keep</button><button class="btn red" data-sx="fdel2:${id}">Delete ${E(m.name)}'s data</button></div>`,{label:'Remove member'})};
SX.act.fdel2=async([id])=>{const m=SX.member(id);if(!m)return;
 try{const files=(S.vault||[]).filter(v=>v.m===id&&v.file);if(SX.files)for(const v of files)await SX.files.del(v.id)}catch(e){}
 S.vault=(S.vault||[]).filter(v=>v.m!==id);['contacts','mid','results','meds','preg','checks'].forEach(k=>{if(S[k]&&S[k][id]!==undefined)delete S[k][id]});
 S.members=S.members.filter(x=>x.id!==id);if(S.active===id){S.active=S.members[0].id;SX.pendingModel=true}
 SX.ledger('member',false,'Removed '+m.name+' and their data',id);SX.save(true);SX.closeModal();famEdit=null;SX.syncPreg();SX.paintWho();render();toast(m.name+' removed')};

// ---------------------------------------------------------------- Consent
const CONSENTS=[
 ['sos_location','Share my location when I press SOS','Your phone location is added to the SOS message so people can find you. It is never tracked in the background.','Without it, the SOS message asks contacts to call you instead.'],
 ['sos_medid','Include Medical ID in the SOS message','Blood group, allergies, conditions and medicines go into the text, so a family member can tell responders.','Without it, the message has only your name, time and location.'],
 ['doctor_share','Share my records with doctors I book','When you book, the doctor can see the reports you choose. You decide what to attach at booking.','Without it, bookings show only the reason you type.'],
 ['pharmacy_rx','Show my prescription to a pharmacy when I order','A pharmacist must check a valid prescription for Schedule H medicines before delivery.','Without it, prescription-only medicines cannot be ordered here. Over-the-counter items still can.']];
SX.reg('consent',{head:()=>['Consent','You decide what is shared, and you can change it any time.'],
 render:()=>{const others=S.members.filter(m=>m.rel!=='You');
  return `<div class="card wide"><h3>What DoKKo may do</h3>${CONSENTS.map(([k,t,d,off])=>`<div class="row sx-cons"><div class="grow"><b>${E(t)}</b><small>${E(d)}</small><small style="color:var(--mute)"><em>${S.consent[k]?'':'Off now. '}${E(off)}</em></small></div><label class="sx-sw"><input type="checkbox" data-sxc="cons:${k}" ${S.consent[k]?'checked':''} aria-label="${E(t)}"><i></i></label></div>`).join('')}
   <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap"><button class="btn s sm" data-sx="consentoff">Turn all off</button></div></div>
  <div class="card"><div class="hd"><h3>Family access</h3><span class="demo">DEMO</span></div><p class="mute sm" style="margin-top:-6px">In the full product each adult decides this from their own account. Switch a person off to see what happens when they have not shared.</p>
   ${others.map(m=>`<div class="row">${SX.avatar(m,38)}<div class="grow"><b>${E(m.name)}</b><small>${E(m.rel)} · ${m.shared!==false?'Records shared with you':'Not shared with you'}</small></div><label class="sx-sw"><input type="checkbox" data-sxc="share:${m.id}" ${m.shared!==false?'checked':''} aria-label="${E(m.name)} shares records"><i></i></label></div>`).join('')||'<p class="mute">No other members.</p>'}</div>
  <div class="card"><div class="hd"><h3>History</h3><button class="btn s sm" data-sx="ledgerdl">Download</button></div>${S.ledger.slice(0,14).map(l=>`<div class="sx-led"><i class="${l.on?'on':'off'}"></i><div><b>${E(l.x)}</b><small>${E(SX.fmtT(l.t))}</small></div></div>`).join('')}<p class="mute sm" style="margin:8px 0 0">A record of what you turned on or off, kept on this device.</p></div>`}});
SX.chg.cons=([k],el)=>{S.consent[k]=el.checked;const c=CONSENTS.find(x=>x[0]===k);SX.ledger(k,el.checked,(el.checked?'Allowed: ':'Stopped: ')+(c?c[1]:k));SX.save();render()};
SX.chg.share=([id],el)=>{const m=SX.member(id);if(!m)return;m.shared=el.checked;SX.ledger('share',el.checked,(m.name)+(el.checked?' shared records with you':' stopped sharing records with you'),id);SX.save();render()};
SX.act.consentoff=()=>{CONSENTS.forEach(([k])=>{S.consent[k]=false});SX.ledger('all',false,'All optional sharing turned off');SX.save();render();toast('All optional sharing is off')};
const dl=(name,text,type='application/json')=>{const b=new Blob([text],{type}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),5000)};
SX.act.ledgerdl=()=>dl('dokko-consent-history.json',JSON.stringify(S.ledger,null,2));

// ---------------------------------------------------------------- My data (export / delete)
const counts=()=>({members:S.members.length,documents:(S.vault||[]).length,results:Object.values(S.results||{}).reduce((a,x)=>a+x.length,0),medicines:Object.values(S.meds||{}).reduce((a,x)=>a+x.length,0),orders:(S.orders||[]).length,contacts:Object.values(S.contacts||{}).reduce((a,x)=>a+x.length,0),alerts:(S.sos||[]).length});
let usage='';
SX.reg('data',{head:()=>['My data','Take a copy, or delete it. Your choice, any time.'],
 render:()=>{const c=counts();
  return `<div class="card"><h3>Stored on this device</h3><div class="stat">${Object.entries(c).map(([k,v])=>`<div><small>${k}</small><b>${v}</b></div>`).join('')}</div>
   <p class="mute sm" style="margin:10px 0 0">${usage?E(usage)+' used by DoKKo in this browser. ':''}There is no DoKKo server account in this build: nothing here leaves your device unless you export or share it.</p></div>
  <div class="card"><h3>Download a copy</h3><p class="mute sm" style="margin-top:-6px">A JSON file with everyone's profiles, results, medicines, contacts, consent history and pregnancy logs. Documents can be included too.</p>
   <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn p" data-sx="export:0">⬇ Data only</button><button class="btn s" data-sx="export:1">⬇ With document files</button></div></div>
  <div class="card"><h3>Delete</h3><p class="mute sm" style="margin-top:-6px">Remove one family member and their data in Family → Edit → Remove. Or erase everything DoKKo keeps in this browser.</p>
   <button class="btn red" data-sx="wipe">Delete everything on this device…</button></div>
  <div class="card"><h3>Where your data goes</h3><ul class="sx-ul"><li>Stays in this browser (local storage and a private file store).</li><li>Pharmacy orders and doctor bookings in this demo are simulated; nothing is sent.</li><li>When accounts launch, data will be stored in India and you will be asked before anything moves off this device.</li></ul></div>`},
 after:()=>{if(navigator.storage&&navigator.storage.estimate)navigator.storage.estimate().then(e=>{if(page==='data'&&e&&e.usage){const mb=e.usage/1048576;const u=mb<1?'under 1 MB':mb.toFixed(1)+' MB';if(u!==usage){usage=u;render()}}}).catch(()=>{})}});
SX.act.export=async([withFiles])=>{const out={app:'DoKKo',exportedAt:new Date().toISOString(),version:1,data:JSON.parse(JSON.stringify(S))};
 try{out.pregnancy={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&k.startsWith('dk-preg-')){try{out.pregnancy[k.slice(8)]=JSON.parse(localStorage.getItem(k))}catch(e){}}}}catch(e){}
 if(withFiles==='1'&&SX.files){try{const all=await SX.files.all();out.files=[];for(const f of all){const b64=await new Promise(r=>{const fr=new FileReader();fr.onload=()=>r(String(fr.result).split(',')[1]||'');fr.readAsDataURL(f.blob)});out.files.push({id:f.id,type:f.blob.type,base64:b64})}}catch(e){toast('Could not read the document files');return}}
 dl('dokko-my-data-'+SX.today()+'.json',JSON.stringify(out));SX.ledger('export',true,'Downloaded a copy of data'+(withFiles==='1'?' with files':''));toast('Download started')};
SX.act.wipe=()=>SX.modal(`<h2>Delete everything on this device?</h2><p class="mute">This erases all members, documents, results, medicines, contacts, consent history and pregnancy logs from this browser. It cannot be undone. Download a copy first if you may want it.</p>
 <form data-sxf="wipe2"><label style="display:grid;gap:6px;font-size:13px;font-weight:600">Type <b style="color:var(--red)">DELETE</b> to confirm<input name="c" autocomplete="off" autocapitalize="characters" placeholder="DELETE"></label><div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px"><button class="btn s" type="button" data-sx="closeModal">Cancel</button><button class="btn red" type="submit">Delete everything</button></div></form>`,{label:'Delete everything'});
SX.chg.wipe2=async(a,f)=>{if(String(new FormData(f).get('c')).trim().toUpperCase()!=='DELETE'){toast('Type DELETE to confirm');return}
 SX.wiped=true;try{const ks=[];for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&k.startsWith('dk'))ks.push(k)}ks.forEach(k=>localStorage.removeItem(k))}catch(e){}
 try{if(SX.files)await SX.files.clear()}catch(e){}try{indexedDB.deleteDatabase('dk6files')}catch(e){}
 SX.closeModal();document.body.innerHTML='<div style="display:grid;place-items:center;min-height:80vh;text-align:center;font:16px system-ui;padding:20px"><div><h2>Everything has been deleted from this device.</h2><p><a href="/">Start again</a></p></div></div>'};

// ---------------------------------------------------------------- Settings (original model/theme controls + language + credits)
const _set=PAGES.set;
SX.reg('set',{head:()=>['Settings','Language, theme, body model and credits.'],
 render:()=>`<div class="card"><h3>Language</h3><div class="chips">${[['en','English'],['hi','हिन्दी'],['te','తెలుగు']].map(([k,n])=>`<button class="chip ${S.lang===k?'on':''}" data-sx="lang:${k}">${n}</button>`).join('')}</div><p class="mute sm" style="margin:10px 0 0">Menus, SOS and emergency alerts are translated. Medical guidance stays in English until a clinician has reviewed each translation.</p></div>`
  +_set()+`<div class="card"><h3>Credits and licences</h3><p class="mute sm" style="margin:0">3D anatomy: Z-Anatomy (CC BY-SA 4.0, built on BodyParts3D © DBCLS) and the HuBMAP Human Reference Atlas v1.5 (CC BY 4.0). Three.js (MIT). Fonts: Geist and Noto Sans (SIL Open Font Licence). Sample people, results, doctors, pharmacies and prices are fictional. DoKKo gives information, not a diagnosis or treatment.</p></div>`});
})();
