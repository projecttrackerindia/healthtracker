// ===================== live layer 5: one identity, health agent, devices, honest plans =====================
{
const P=SX.p;
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1','x-dokko-key':(S.key||'')},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status});return j});
const WEEK=7*864e5;
const fmtDay=t=>new Date(t).toLocaleDateString('en-IN',{day:'numeric',month:'short'});
S.ask=S.ask||{};S.insight=S.insight||{};S.consent=S.consent||{};

// ---------------------------------------------------------------- A. one account indicator: a tick only when email AND mobile are verified
const bothOk=()=>!!(SX.user&&SX.user.emailVerified&&SX.user.phoneVerified);
function paintOne(){const a=document.getElementById('sxAcct');if(!a)return;const ok=bothOk();if(a.classList.contains('lv5-both')!==ok)a.classList.toggle('lv5-both',ok);if(SX.user){const t=P('Account')+(ok?' · '+P('Verified'):' · '+P('Verification pending'));if(a.title!==t)a.title=t}}
const lu=SX.loadUser;SX.loadUser=async()=>{await lu();paintOne()};
new MutationObserver(paintOne).observe(document.body,{subtree:true,attributes:true,attributeFilter:['class','data-sync']});

// ---------------------------------------------------------------- B. identity: name as on Aadhaar, date of birth, sex, blood group change once a week
const idOf=(m,fd)=>({name:String(fd.get('name')||'').replace(/\s+/g,' ').trim().slice(0,60),dob:String(fd.get('dob')||''),sex:String(fd.get('sex')||''),blood:String(fd.get('blood')||'')});
const idNow=m=>({name:m.name||'',dob:m.dob||'',sex:m.sexOk?m.sex||'':'',blood:SX.midOf(m.id).blood||''});
const idChanged=(a,b)=>a.name!==b.name||a.dob!==b.dob||(b.sex&&a.sex!==b.sex)||a.blood!==b.blood;
const lockedUntil=m=>m&&m.idLock&&Date.now()<m.idLock+WEEK?m.idLock+WEEK:0;
const lockMsg=t=>P('Identity details (name, date of birth, sex, blood group) can be changed once a week, so your health card, Medical ID and doctor summary always match.')+' '+P('Next change:')+' '+fmtDay(t)+'.';
function guard(orig){return async(a,f)=>{const id=a[0];const m=id?SX.member(id):(f.dataset.sxf==='lvcard'?(S.members.find(x=>x.rel==='You')||S.members[0]):null);
 const fd=new FormData(f),want=idOf(m||{},fd),show=t=>{const err=f.querySelector('.lv-err');if(err){err.textContent=t;err.hidden=false}else toast(t)};
 let changed=false;if(m&&m.name&&m.name!=='You'){changed=idChanged(idNow(m),want);const until=lockedUntil(m);if(changed&&until)return show(lockMsg(until))}
 const real=!!(m&&m.name&&m.name!=='You'&&m.dob);
 // the account name is the same identity: the server applies the weekly rule and must agree before anything changes here
 if(real&&m.rel==='You'&&SX.user&&want.name&&want.name!==SX.user.name&&want.name!==m.name&&navigator.onLine){try{const u=await J('/auth/profile','POST',{name:want.name});SX.user=u.user;try{localStorage.setItem('dk6.user',JSON.stringify(SX.user))}catch(e){}}catch(e){return show(e.message)}}
 const before=real?JSON.stringify(idNow(m)):'';const r=orig(a,f);
 const mm=m||(S.members.find(x=>x.rel==='You')||S.members[0]);if(mm&&before&&JSON.stringify(idNow(mm))!==before){mm.idLock=Date.now();SX.save()}
 return r}}
if(SX.chg.fsave)SX.chg.fsave=guard(SX.chg.fsave);
if(SX.chg.lvcard)SX.chg.lvcard=guard(SX.chg.lvcard);
// the edit form shows the rule and locks the fields while the week runs
SX.extend('family',{mounted(){document.querySelectorAll('form[data-sxf^="fsave:"]').forEach(f=>{const id=f.dataset.sxf.split(':')[1];if(!id)return;const m=SX.member(id),until=lockedUntil(m);const note=document.createElement('p');note.className='lv5-lock full';
 note.innerHTML=until?'🔒 '+E(lockMsg(until)):'🪪 '+E(P('Name as on Aadhaar, date of birth, sex and blood group are identity details: they can be changed once a week and appear the same on the health card, Medical ID and doctor summary.'));
 const n=f.querySelector('input[name=name]');if(n)n.placeholder=P('As on Aadhaar');
 f.querySelector('.lv-err').before(note);if(until)['name','dob','sex','blood'].forEach(k=>f.querySelectorAll(`[name=${k}]`).forEach(i=>{i.disabled=true}))})}});

// account card: verification status in one place, sync state in words, the name rule
SX.extend('set',{mounted(){const u=SX.user,c=document.querySelector('#sxAcc .sx-accg');if(!u||!c||document.querySelector('.lv5-id'))return;const a=document.getElementById('sxAcct'),sync=a?a.dataset.sync:'';
 const pend=[!u.emailVerified&&u.email?'email':null,!u.phoneVerified&&u.phone?'phone':null].filter(Boolean);
 const box=document.createElement('div');box.className='lv5-id'+(pend.length?'':' ok');
 box.innerHTML=`<div class="lv5-idl"><b>${pend.length?'⏳ '+P('Verification pending'):'✓ '+P('Verified account')}</b><small>${pend.length?P('One account, one identity: verify both to get the badge on your health card.'):P('Email and mobile verified. Your health card, Medical ID and shares carry the badge.')}</small></div>
  <div class="lv5-ida">${pend.map(k=>`<button class="btn p sm" data-sx="lvverify:${k}">${k==='phone'?P('Verify mobile'):P('Verify email')}</button>`).join('')}</div>
  <div class="lv5-idm"><span>${sync==='ok'?'☁︎ '+P('Synced with your family'):sync==='err'?'⚠︎ '+P('Sync paused — check your connection'):sync==='off'?P('Sync off on this device'):P('Sync')+'…'}</span><span>🪪 ${P('Name as on Aadhaar')}${u.nameNext?' · '+P('next change')+' '+fmtDay(u.nameNext*1000):''}</span></div>`;
 c.before(box);const nm=c.querySelector('div b');if(nm)nm.insertAdjacentHTML('beforeend',bothOk()?' <span class="badge b-ok">✓ '+P('verified')+'</span>':'')}});

// ---------------------------------------------------------------- C. plans: a paid plan is never switched without a verified payment
let PL=null,plT=0;
async function plans(){if(PL&&Date.now()-plT<60e3)return PL;try{PL=await J('/plans');plT=Date.now()}catch(e){}return PL}
SX.extend('plan',{async mounted(){const p=await plans();if(!p||p.provider!=='soon'||page!=='plan')return;document.querySelectorAll('[data-sx^="sub:"]').forEach(b=>{const code=b.dataset.sx.split(':')[1],pl=p.plans.find(x=>x.code===code);if(!pl||!pl.month)return;if(/Yearly/.test(b.textContent)){b.remove();return}b.className='badge';b.removeAttribute('data-sx');b.textContent=P('Opening soon')});
 const d=document.querySelector('#page .sx-disc');if(d)d.textContent=P('Online payment (UPI, cards, net banking) opens soon. Every family is on the Free plan until then; nothing is charged and no plan changes without a payment.')}});
const sub0=SX.act.sub;SX.act.sub=async a=>{const p=await plans();if(p&&p.provider==='soon'){const pl=p.plans.find(x=>x.code===a[0]);if(pl&&pl.month){toast(P('Paid plans open soon'));return}}return sub0(a)};

// ---------------------------------------------------------------- D. the health agent: ask about your own records, a daily insight, what changed
const latestBy=m=>{const o={};((S.results||{})[m.id]||[]).filter(x=>x.k==='lab'&&x.key).sort((a,b)=>a.date.localeCompare(b.date)).forEach(x=>{(o[x.key]=o[x.key]||[]).push(x)});return o};
const LBL=(k,m,x)=>{let L=null;try{L=SX.labStatus(x,m).L}catch(e){}return L?{n:L.n,u:L.u||''}:{n:k.toUpperCase(),u:''}};
SX.agentCtx=m=>{const mid=SX.midOf(m.id),by=latestBy(m),res=[];Object.keys(by).forEach(k=>{const l=by[k],last=l[l.length-1],prev=l.length>1?l[l.length-2]:null,st=SX.labStatus(last,m),LB=LBL(k,m,last);res.push({test:LB.n,unit:LB.u,value:last.val,date:last.date,flag:st.s==='in'?'normal':st.s,previous:prev?{value:prev.val,date:prev.date}:undefined})});
 const vit=((S.vitals||{})[m.id]||[]).slice(-12).map(r=>({d:new Date(r.t).toISOString().slice(0,10),hr:r.hr,sys:r.sys,dia:r.dia,glu:r.glu,when:r.gt,temp:r.temp,spo2:r.spo2,w:r.w,src:r.src}));
 const meds=((S.meds||{})[m.id]||[]).map(x=>({name:x.n,when:x.when,strength:x.s}));const tk=((S.taken||{})[m.id]||{});
 const cyc=(S.cycle||{})[m.id],preg=SX.pregOn(m)?(S.preg[m.id]||{}):null;
 const vax=(S.vax||{})[m.id]||{};const ctx={person:{name:m.name.split(' ')[0],age:m.age,sex:m.sex,blood:mid.blood||'',weight_kg:m.w||undefined,height_cm:m.h||undefined,allergies:mid.allergies||[],conditions:mid.conditions||[],pregnant:!!preg},
  readings:vit,results:res,medicines:meds,taken_today:tk.d===SX.today()?Object.keys(tk.s||{}).length:0,today:SX.today()};
 if(preg&&preg.lmp)ctx.pregnancy={lmp:preg.lmp};if(cyc&&cyc.periods&&cyc.periods.length)ctx.cycle={last_periods:cyc.periods.slice(-3),length:cyc.len||undefined};
 if(m.age<18&&Object.keys(vax).length)ctx.vaccines_given=Object.keys(vax).length;return ctx};
const engineOn=()=>!!(SX.cfg&&SX.cfg.ai&&SX.cfg.ai.engine==='ai');
const changed=m=>{const by=latestBy(m),out=[];Object.keys(by).forEach(k=>{const l=by[k];if(l.length<2)return;const a=l[l.length-2],b=l[l.length-1],L=LBL(k,m,b),st=SX.labStatus(b,m);if(a.val===b.val)return;out.push({k,n:L.n,u:L.u,from:a.val,to:b.val,up:b.val>a.val,good:st.s==='in',date:b.date})});return out.sort((a,b)=>b.date.localeCompare(a.date)).slice(0,4)};
const assistConsent=()=>new Promise(res=>{if(S.consent.ai_assist)return res(true);SX.modal(`<h2>${P('Ask the health assistant?')}</h2><p>${P('Your question goes to the Urban Health server with a short summary of this person’s records (readings, results, medicines) so the answer can refer to them. Documents are never sent, nothing is stored, and the answer is for discussion with your doctor, not a diagnosis.')}</p>
 <label class="lv-opt" style="display:flex;gap:10px;align-items:center;margin:10px 0"><input type="checkbox" id="asok"><span>${P('I understand and allow this')}</span></label><div class="lv-row-end"><button class="btn s" data-sx="closeModal">${P('Not now')}</button><button class="btn p" id="asgo">${P('Continue')}</button></div>`,{label:'Consent'});
 $('#asgo').onclick=()=>{if(!$('#asok').checked){toast(P('Please tick the box first'));return}S.consent.ai_assist=true;SX.ledger('ai_assist',true,'Allowed the health assistant to use record summaries',SX.me().id);SX.save();SX.closeModal();res(true)};const w=document.querySelector('.sx-modal');w._onclose=()=>res(!!S.consent.ai_assist)});
let tab='ask',busy=false;
function agentHTML(m){const asks=(S.ask[m.id]||[]).slice(-3).reverse(),ins=S.insight[m.id],ch=changed(m),flags=SX.labFlags(m).slice(0,4);
 const head=`<div class="hd"><div><h3>✦ ${P('Health assistant')}</h3><small class="mute">${P('Ask about')} ${E(m.name.split(' ')[0])}${P('’s records, read a report, or see today’s insight.')}</small></div></div>
  <div class="lv5-tabs" role="tablist"><button role="tab" aria-selected="${tab==='ask'}" data-sx="agtab:ask">${P('Ask')}</button><button role="tab" aria-selected="${tab==='today'}" data-sx="agtab:today">${P('Today')}</button><button role="tab" aria-selected="${tab==='read'}" data-sx="agtab:read">${P('Read a report')}</button></div>`;
 let body='';
 if(!engineOn())body=`<p class="lv5-off">${P('The health assistant is being switched on for this family. Reports are still read with the basic reader, and you can add readings as usual.')}</p>`;
 else if(tab==='ask')body=`<form class="lv5-ask" data-sxf="agask"><input name="q" maxlength="300" placeholder="${E(P('e.g. Is my sugar trend okay? What should I ask the doctor on Friday?'))}" autocomplete="off" ${busy?'disabled':''}><button class="btn p" ${busy?'disabled':''}>${busy?'<span class="sx-spin sm"></span>':P('Ask')}</button></form>
   <div class="lv5-sugg">${[P('What changed since my last report?'),P('Are my medicines and results consistent?'),P('What should I track this week?')].map(s=>`<button data-sx="agq:${encodeURIComponent(s)}">${E(s)}</button>`).join('')}</div>
   ${asks.map(a=>`<div class="lv5-qa ${a.urgent?'urgent':''}"><small>${E(a.q)} · ${E(fmtDay(a.t))}</small><p>${E(a.a)}</p>${a.src&&a.src.length?`<div class="lv5-src">${a.src.map(s=>`<span>${E(s)}</span>`).join('')}</div>`:''}${a.act&&a.act.length?`<ul>${a.act.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:''}</div>`).join('')}`;
 else if(tab==='today')body=ins&&ins.data?`<div class="lv5-ins ${ins.data.urgent?'urgent':''}"><b>${ins.data.trend==='up'?'↗ ':ins.data.trend==='down'?'↘ ':ins.data.trend==='steady'?'→ ':''}${E(ins.data.headline)}</b><ul>${(ins.data.points||[]).map(p=>`<li>${E(p)}</li>`).join('')}</ul>${ins.data.action?`<p class="lv5-act">→ ${E(ins.data.action)}</p>`:''}<small class="mute">${P('From this person’s records on')} ${E(fmtDay(ins.t))} · ${P('for discussion with your doctor')}</small></div>`:
   `<div class="lv5-ins"><p class="mute sm" style="margin:0">${busy?'<span class="sx-spin sm"></span> '+P('Preparing today’s insight…'):P('A short daily read of this person’s records: what is going well, what changed, one thing to do this week.')}</p>${busy?'':`<div class="row" style="margin-top:8px"><button class="btn p sm" data-sx="aginsight">${P('Prepare today’s insight')}</button></div>`}</div>`;
 else body=`<p class="mute sm" style="margin:0 0 8px">${P('Upload a report or prescription. It is explained in plain words, the values are saved to results, and the findings are shown on the body.')}</p><div class="row"><button class="btn p sm" data-sx="aipick">📄 ${P('Upload & read')}</button><button class="btn s sm" data-sx="tab:vault">${P('Vault')}</button></div>
   ${flags.length?`<div class="lv3-flags" style="margin-top:10px">${flags.map(f=>`<button class="lv3-flag ${f.st.s}" data-sx="onbody:${f.x.key}"><b>${E(f.st.L.n)}</b><small>${E(String(f.x.val))} ${E(f.st.L.u)} · ${f.st.s==='high'?P('High'):P('Low')} · ${P('see on body')}</small></button>`).join('')}</div>`:''}`;
 const trend=ch.length&&tab!=='read'?`<div class="lv5-ch"><small>${P('What changed')}</small>${ch.map(c=>`<span class="${c.good?'ok':'off'}">${E(c.n)} ${E(String(c.from))} → <b>${E(String(c.to))}</b> ${E(c.u)}</span>`).join('')}</div>`:'';
 return `<div class="card lv5-agent">${head}${body}${trend}</div>`}
SX.extend('dash',{before(){return agentHTML(SX.me())}});
SX.act.agtab=([t])=>{tab=t;render();if(t==='today')maybeInsight()};
SX.act.agq=([q])=>{const i=document.querySelector('.lv5-ask input');if(i){i.value=decodeURIComponent(q);i.form.requestSubmit()}};
SX.chg.agask=async(a,f)=>{const m=SX.me(),q=String(new FormData(f).get('q')||'').trim();if(q.length<3){toast(P('Type a question first'));return}if(!(await assistConsent()))return;busy=true;render();
 try{const r=await J('/ai/ask','POST',{question:q,context:SX.agentCtx(m),member:m.id});(S.ask[m.id]=S.ask[m.id]||[]).push({q,a:r.answer,src:r.sources,act:r.actions,urgent:r.urgent,t:Date.now()});S.ask[m.id]=S.ask[m.id].slice(-8);SX.save();
  if(r.urgent)SX.modal(`<h2>⚠️ ${P('Please act now')}</h2><p>${E(r.answer)}</p><div class="lv-row-end"><a class="btn red" href="tel:112">${P('Call 112')}</a><button class="btn s" data-sx="closeModal">${P('OK')}</button></div>`,{label:'Urgent'})}
 catch(e){toast(e.message)}finally{busy=false;render()}};
async function maybeInsight(force){const m=SX.me(),ins=S.insight[m.id];if(!engineOn()||busy)return;if(!force&&ins&&ins.day===SX.today())return;if(!force&&!ins)return;if(!(await assistConsent()))return;busy=true;render();
 try{const r=await J('/ai/insight','POST',{context:SX.agentCtx(m),member:m.id});S.insight[m.id]={t:Date.now(),day:SX.today(),data:{headline:r.headline,points:r.points,action:r.action,trend:r.trend,urgent:r.urgent}};SX.save()}catch(e){toast(e.message)}finally{busy=false;render()}}
SX.act.aginsight=()=>maybeInsight(true);

// ---------------------------------------------------------------- E. readings from a device (Web Bluetooth, standard health profiles)
const SF=(dv,o)=>{const r=dv.getUint16(o,true);let m=r&0x0fff,e=r>>12;if(m>=0x0800)m-=0x1000;if(e>=8)e-=16;if(m===0x07ff||m===0x0800||m===0x07fe||m===0x0802)return null;return m*Math.pow(10,e)};
const F32=(dv,o)=>{const r=dv.getUint32(o,true);let m=r&0x00ffffff,e=r>>24;if(m>=0x800000)m-=0x1000000;if(e>=128)e-=256;return m*Math.pow(10,e)};
const PROFILES={heart_rate:{c:'heart_rate_measurement',label:'Heart rate',parse:dv=>{const f=dv.getUint8(0);return{hr:f&1?dv.getUint16(1,true):dv.getUint8(1)}}},
 blood_pressure:{c:'blood_pressure_measurement',label:'Blood pressure',parse:dv=>{const f=dv.getUint8(0),k=f&1;let s=SF(dv,1),d=SF(dv,3);if(s==null||d==null)return null;if(k){s=s*7.50062;d=d*7.50062}let o=7+(f&2?7:0);const r={sys:Math.round(s),dia:Math.round(d)};if(f&4){const p=SF(dv,o);if(p)r.hr=Math.round(p)}return r}},
 weight_scale:{c:'weight_measurement',label:'Weight',parse:dv=>{const f=dv.getUint8(0),raw=dv.getUint16(1,true);return{w:+(f&1?raw*0.01*0.453592:raw*0.005).toFixed(1)}}},
 pulse_oximeter:{c:'plx_spot_check_measurement',label:'Pulse oximeter',parse:dv=>{const s=SF(dv,1),p=SF(dv,3);if(s==null)return null;const r={spo2:Math.round(s)};if(p)r.hr=Math.round(p);return r}},
 health_thermometer:{c:'temperature_measurement',label:'Thermometer',parse:dv=>{const f=dv.getUint8(0);let t=F32(dv,1);if(f&1)t=(t-32)*5/9;return{temp:+t.toFixed(1)}}}};
const bleOK=()=>!!(navigator.bluetooth&&navigator.bluetooth.requestDevice);
let dev=null,got=null,chr=null;
const show=r=>[r.hr!=null?r.hr+' bpm':'',r.sys!=null?r.sys+'/'+r.dia+' mmHg':'',r.spo2!=null?'SpO₂ '+r.spo2+'%':'',r.temp!=null?r.temp+' °C':'',r.w!=null?r.w+' kg':''].filter(Boolean).join(' · ');
SX.act.bledev=async()=>{const m=SX.me();if(!bleOK()){SX.modal(`<h2>⌚ ${P('Readings from a device')}</h2><p>${P('This browser cannot talk to Bluetooth devices. On Android, Windows and Mac, open Urban Health in Chrome or Edge and tap this again. On iPhone, device readings arrive with the Urban Health app, coming soon.')}</p><p class="mute sm">${P('Works with Bluetooth blood-pressure monitors, pulse oximeters, weighing scales, thermometers and chest-strap or wrist heart-rate monitors that use the standard health profiles (Omron, Beurer, Dr Trust, Polar, Garmin HR broadcast and others).')}</p><div class="lv-row-end"><button class="btn p" data-sx="closeModal">${P('OK')}</button></div>`,{label:'Devices'});return}
 const keys=Object.keys(PROFILES);try{dev=await navigator.bluetooth.requestDevice({filters:keys.map(s=>({services:[s]})),optionalServices:keys})}catch(e){if(!/cancel/i.test(e.message))toast(P('No device chosen'));return}
 got=null;SX.modal(`<h2>⌚ ${E(dev.name||P('Device'))}</h2><p class="mute" id="blest">${P('Connecting… take the measurement on the device now.')}</p><div class="lv5-live" id="bleval">—</div><p class="full lv-err" hidden></p><div class="lv-row-end"><button class="btn s" data-sx="bleoff">${P('Cancel')}</button><button class="btn p" id="blesave" disabled>${P('Save reading')}</button></div>`,{label:'Device',onclose:bleStop});
 try{const srv=await dev.gatt.connect();let used=null;for(const k of keys){try{const s=await srv.getPrimaryService(k);chr=await s.getCharacteristic(PROFILES[k].c);used=k;break}catch(e){}}if(!used)throw new Error(P('This device does not use a standard health profile.'));
  $('#blest').textContent=PROFILES[used].label+' · '+P('waiting for a measurement…');const samples=[];
  chr.addEventListener('characteristicvaluechanged',ev=>{const r=PROFILES[used].parse(ev.target.value);if(!r)return;samples.push(r);got=used==='heart_rate'?{hr:Math.round(samples.slice(-10).reduce((a,x)=>a+x.hr,0)/Math.min(10,samples.length))}:r;$('#bleval').textContent=show(got);$('#blest').textContent=PROFILES[used].label+(used==='heart_rate'?' · '+P('live — tap Save when it settles'):' · '+P('received'));$('#blesave').disabled=false});
  await chr.startNotifications();$('#blesave').onclick=()=>{if(!got)return;const r=Object.assign({id:uid('v'),t:Date.now(),src:'dev',dev:(dev.name||'').slice(0,40)},got);if(r.w!=null){m.w=r.w;delete r.w;if(r.hr==null&&r.sys==null&&r.spo2==null&&r.temp==null){SX.save();bleStop();SX.closeModal();render();toast(P('Weight saved'));return}}
   (S.vitals[m.id]=S.vitals[m.id]||[]).push(r);SX.ledger('reading',true,'Reading from '+(dev.name||'device'),m.id);SX.save();bleStop();SX.closeModal();render();toast(P('Reading saved from')+' '+(dev.name||P('device')))}}
 catch(e){const err=document.querySelector('.sx-modal .lv-err');if(err){err.textContent=e.message||P('Could not connect');err.hidden=false}}};
function bleStop(){try{if(chr)chr.stopNotifications().catch(()=>{})}catch(e){}try{if(dev&&dev.gatt&&dev.gatt.connected)dev.gatt.disconnect()}catch(e){}chr=null;dev=null}
SX.act.bleoff=()=>{bleStop();SX.closeModal()};
// the manual form gets a device button; the list shows where a reading came from
const vlog0=SX.act.vlog;SX.act.vlog=a=>{vlog0(a);const f=document.querySelector('.sx-modal form[data-sxf="vsave"]');if(f&&!f.querySelector('.lv5-dev')){const d=document.createElement('div');d.className='full lv5-dev';d.innerHTML=`<button type="button" class="btn s sm" data-sx="bledev">⌚ ${P('Read from a device')}</button><small class="mute">${P('Bluetooth BP monitor, oximeter, scale, thermometer or heart-rate monitor')}</small>`;f.querySelector('.lv-err').before(d)}};
SX.extend('dash',{mounted(){document.querySelectorAll('.lv-vlist .row').forEach(row=>{const b=row.querySelector('[data-sx^="vdel:"]');if(!b)return;const id=b.dataset.sx.slice(5),m=SX.me(),r=((S.vitals||{})[m.id]||[]).find(x=>x.id===id);if(r&&r.src==='dev'){const s=row.querySelector('small');if(s&&!/⌚/.test(s.textContent))s.textContent+=' · ⌚ '+(r.dev||P('device'))}
 if(r&&(r.spo2!=null||r.temp!=null)){const bb=row.querySelector('b');if(bb&&!/SpO|°C/.test(bb.textContent))bb.textContent=[bb.textContent,r.spo2!=null?'SpO₂ '+r.spo2+'%':'',r.temp!=null?r.temp+' °C':''].filter(x=>x&&x!=='').join(' · ')}})}});
// connected devices: a settings card that says exactly what works today and what is coming
SX.extend('set',{after(){return `<div class="card wide lv5-devs"><div class="hd"><h3>⌚ ${P('Devices & automatic readings')}</h3></div>
 <p class="mute sm" style="margin:-4px 0 10px">${P('Readings come in three ways: typed in, read from a Bluetooth device, or synced from your phone’s health app.')}</p>
 <div class="lv5-devg"><div><b>${P('Bluetooth devices')}</b><small>${bleOK()?P('Ready on this browser.'):P('Use Chrome or Edge on Android, Windows or Mac.')} ${P('BP monitors, pulse oximeters, scales, thermometers, heart-rate straps and watches that broadcast heart rate.')}</small><button class="btn p sm" data-sx="bledev">${P('Connect a device')}</button></div>
 <div><b>${P('Apple Health & Health Connect')}</b><small>${P('Steps, sleep, heart rate and workouts from Apple Watch, Samsung, Noise, boAt and Fitbit arrive through the Urban Health phone app, which reads your phone’s health store with your permission.')}</small><span class="badge">${P('Coming with the app')}</span></div></div></div>`}});
}
