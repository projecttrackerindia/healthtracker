// ===================== live layer: health card, real vitals, honest Care pages, verified badges =====================
// Inserted by tools/live/p0.py inside the last six IIFE, just before SX.boot(). Uses SX, S, E, uid, go, render, toast.
{
const P=SX.p;
const AUTH_H={'content-type':'application/json','x-tht':'1'};
const authApi=async(path,body)=>{const r=await fetch('/api/v1/auth'+path,{method:body===undefined?'GET':'POST',headers:AUTH_H,credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)});
 let j={};try{j=await r.json()}catch(e){}if(!r.ok){const m=j&&j.detail;throw Object.assign(new Error(typeof m==='string'?m:'Something went wrong. Please try again.'),{status:r.status})}return j};

// ---------------------------------------------------------------- small helpers
const ageFrom=dob=>{if(!dob)return 0;const d=new Date(dob+'T00:00'),n=new Date();if(isNaN(d))return 0;let a=n.getFullYear()-d.getFullYear();const mm=n.getMonth()-d.getMonth();if(mm<0||(mm===0&&n.getDate()<d.getDate()))a--;return Math.max(0,Math.min(120,a))};
SX.ageFrom=ageFrom;
const poss=n=>n==='You'?'Your':n+"'s";
SX.poss=poss;
const phShow=p=>{if(!p)return '';const m=/^\+91(\d{5})(\d{5})$/.exec(p);return m?`+91 ${m[1]} ${m[2]}`:p};
const BLOOD=['A+','A-','B+','B-','AB+','AB-','O+','O-'];
const htid=()=>{const a='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';let s='';const r=new Uint32Array(12);try{crypto.getRandomValues(r)}catch(e){for(let i=0;i<12;i++)r[i]=Math.random()*1e9}for(let i=0;i<12;i++)s+=a[r[i]%a.length];return 'THT-'+s.slice(0,4)+'-'+s.slice(4,8)+'-'+s.slice(8)};
const fmtDate=d=>{try{return new Date(d+'T00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}catch(e){return d}};
const you=()=>S.members.find(m=>m.rel==='You')||S.members[0];
S.members.forEach(m=>{if(m.dob)m.age=ageFrom(m.dob);if(!m.htid)m.htid=htid()});
S.vitals=S.vitals||{};

// ---------------------------------------------------------------- account state (filled by SX.loadUser)
let AUTHCFG=null;
const userPhoneVerified=m=>!!(SX.user&&SX.user.phoneVerified&&SX.user.phone&&m&&m.rel==='You'&&m.ph===SX.user.phone);
const userEmailVerified=()=>!!(SX.user&&SX.user.emailVerified&&SX.user.email);
SX.verified={phone:userPhoneVerified,email:userEmailVerified};
const vbadge=(on,label)=>on?`<span class="lv-ver" title="${E(label)} verified"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l2.4 2.1 3.2-.3.9 3.1 2.8 1.6-1.1 3 1.1 3-2.8 1.6-.9 3.1-3.2-.3L12 22l-2.4-2.1-3.2.3-.9-3.1L2.7 15.5l1.1-3-1.1-3 2.8-1.6.9-3.1 3.2.3z"/><path d="M8.3 12.2l2.5 2.5 5-5" fill="none"/></svg><span>${P('Verified')}</span></span>`:`<span class="lv-unver">${P('Not verified')}</span>`;

// ---------------------------------------------------------------- health card: mandatory first step
const cardDone=m=>!!(m&&m.name&&m.name!=='You'&&m.dob&&m.sexOk&&m.ph&&(SX.midOf(m.id).blood||m.bloodUnknown));
SX.cardDone=cardDone;
let cardOpen=false;
function cardForm(){const m=you(),mid=SX.midOf(m.id),u=SX.user,tm=SX.today();
 const name=m.name&&m.name!=='You'?m.name:(u&&u.name)||'';const ph=m.ph||(u&&u.phone)||'';
 return `<div class="lv-ob"><div class="lv-ob-hd"><div class="lv-ob-ic" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="11" r="2.2"/><path d="M5.8 16c.7-1.6 1.9-2.4 3.2-2.4s2.5.8 3.2 2.4M14.5 10h4M14.5 13.5h3"/></svg></div>
  <div><h2>${P('Create your health card')}</h2><p class="mute">${P('A few details so the app can show the right 3D body, use the right healthy ranges and help responders in an emergency. It takes about a minute.')}</p></div></div>
  <form class="form lv-form" data-sxf="lvcard" novalidate>
   <label class="full">${P('Full name')}<input name="name" required maxlength="60" autocomplete="name" value="${E(name)}" placeholder="${E(P('As on your ID'))}"></label>
   <label>${P('Date of birth')}<input name="dob" type="date" required max="${tm}" min="1900-01-01" value="${E(m.dob||'')}"></label>
   <label>${P('Blood group')}<select name="blood" required><option value="">${P('Choose')}</option>${BLOOD.map(b=>`<option ${mid.blood===b?'selected':''}>${b}</option>`).join('')}<option value="?" ${m.bloodUnknown?'selected':''}>${P("I don't know yet")}</option></select></label>
   <fieldset class="full lv-sex"><legend>${P('Sex')} <small class="mute">${P('sets the 3D body and the healthy ranges for lab results')}</small></legend>
    <label class="lv-opt"><input type="radio" name="sex" value="female" ${m.sexOk&&m.sex==='female'?'checked':''} required><span><b>♀ ${P('Female')}</b></span></label>
    <label class="lv-opt"><input type="radio" name="sex" value="male" ${m.sexOk&&m.sex==='male'?'checked':''}><span><b>♂ ${P('Male')}</b></span></label></fieldset>
   <label class="full">${P('Mobile number')}<span class="lv-ph"><i>+91</i><input name="ph" required inputmode="tel" autocomplete="tel-national" maxlength="16" value="${E(ph.replace(/^\+91/,''))}" placeholder="98765 43210"></span>
    <small class="mute">${P('Used for SOS alerts and to verify your account. We never show it to anyone else.')}</small></label>
   <p class="full lv-err" role="alert" hidden></p>
   <div class="full lv-ob-ft"><small class="mute">🔒 ${P('Stored on this device.')} <a href="/privacy" target="_blank" rel="noopener">${P('Privacy policy')}</a></small><button class="btn p" type="submit">${P('Create health card')}</button></div>
  </form></div>`}
function openCard(){if(cardOpen)return;cardOpen=true;SX.modal(cardForm(),{label:P('Create your health card'),sticky:true,cls:'lv-wide',onclose:()=>{cardOpen=false;if(!cardDone(you()))setTimeout(openCard,400)}});
 const w=document.querySelector('.sx-modal');if(w){w.addEventListener('keydown',e=>{if(e.key==='Escape')e.stopPropagation()},true)}}
SX.openCard=openCard;
SX.chg.lvcard=(a,f)=>{const fd=new FormData(f),err=f.querySelector('.lv-err'),say=t=>{err.textContent=t;err.hidden=false};
 const name=String(fd.get('name')||'').replace(/\s+/g,' ').trim().slice(0,60),dob=String(fd.get('dob')||''),blood=String(fd.get('blood')||''),sex=String(fd.get('sex')||''),ph=SX.phoneNorm(String(fd.get('ph')||''));
 if(name.length<2)return say(P('Please enter your full name.'));
 if(!dob)return say(P('Please enter your date of birth.'));
 if(new Date(dob+'T00:00')>new Date()||ageFrom(dob)>120)return say(P('Please check the date of birth.'));
 if(!blood)return say(P('Please choose your blood group, or "I don\'t know yet".'));
 if(sex!=='female'&&sex!=='male')return say(P('Please choose the body model.'));
 if(!ph||!/^\+\d{10,15}$/.test(ph))return say(P('Please enter a valid mobile number.'));
 const m=you(),oldSex=m.sex,mid=SX.midOf(m.id);
 Object.assign(m,{name,dob,age:ageFrom(dob),sex,sexOk:true,ph,av:name.split(' ').map(x=>x[0]).join('').slice(0,2).toUpperCase(),htid:m.htid||htid()});
 if(blood==='?'){m.bloodUnknown=true;mid.blood=''}else{m.bloodUnknown=false;mid.blood=blood}
 S.cardAt=S.cardAt||Date.now();SX.ledger('member',true,'Health card created',m.id);SX.save(true);
 if(oldSex!==sex||A.sex!==sex)SX.pendingModel=true;
 cardOpen=false;SX.closeModal(true);if(SX.pendingModel)SX.applyModel();go(page==='dash'?'dash':page,{keep:true});SX.paintWho();
 // keep the account name in step with the card (signed-in users)
 if(SX.user&&SX.user.name!==name)authApi('/profile',{name}).then(r=>{SX.user=r.user}).catch(()=>{});
 showCard(m,true)};
// the card itself (also opened from Home and Family)
function cardHTML(m){const mid=SX.midOf(m.id),blood=mid.blood||(m.bloodUnknown?P('Not known'):'—'),pv=userPhoneVerified(m);
 return `<div class="lv-card" role="group" aria-label="${E(P('Health card'))}"><div class="lv-card-top"><span class="lv-card-brand"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-5 3 10 2-5h7"/></svg>thehealthtracker</span><span class="lv-card-k">${P('HEALTH CARD')}</span></div>
  <div class="lv-card-name">${E(m.name)}</div>
  <div class="lv-card-grid"><div><small>${P('Age')}</small><b>${m.age||'—'}</b></div><div><small>${P('Sex')}</small><b>${m.sex==='female'?P('Female'):P('Male')}</b></div><div><small>${P('Blood')}</small><b class="lv-blood">${E(blood)}</b></div></div>
  <div class="lv-card-ph"><small>${P('Mobile')}</small><b>${E(phShow(m.ph)||'—')}</b>${m.ph?vbadge(pv,'Mobile'):''}</div>
  <div class="lv-card-id"><small>${P('Health tracker ID')}</small><b>${E(m.htid||'')}</b></div></div>`}
SX.cardHTML=cardHTML;
function showCard(m,fresh){const canVerify=m.rel==='You'&&m.ph&&!userPhoneVerified(m);
 SX.modal(`<div class="lv-reveal ${fresh?'fresh':''}">${fresh?`<h2>${P('Your health card is ready')}</h2><p class="mute">${P('You can change these details any time in Family & Privacy.')}</p>`:`<h2>${P('Health card')}</h2>`}${cardHTML(m)}
  ${canVerify?`<div class="lv-vbox"><div><b>${P('Verify your mobile number')}</b><small class="mute">${SX.user?P('Get the verified badge and receive SOS confirmations.'):P('Sign in to verify your number and keep your card on every device.')}</small></div>${SX.user?`<button class="btn p sm" data-sx="lvverify:phone">${P('Verify now')}</button>`:`<a class="btn p sm" href="/signin?next=/app">${P('Sign in')}</a>`}</div>`:''}
  <div class="lv-row-end"><button class="btn s" data-sx="closeModal">${fresh?P('Continue'):P('Close')}</button></div></div>`,{label:P('Health card'),cls:'lv-mid'})}
SX.act.lvcardshow=([id])=>showCard(SX.member(id)||SX.me(),false);
SX.act.lvcardedit=()=>{SX.closeModal(true);cardOpen=false;openCard()};

// ---------------------------------------------------------------- verify mobile or email (badge)
let vflow=null;
SX.act.lvverify=async([kind])=>{const m=you();if(!SX.user){location.href='/signin?next=/app';return}
 const value=kind==='email'?SX.user.email:m.ph;if(!value){toast(P('Add the number to your health card first'));return}
 if(AUTHCFG&&kind==='phone'&&!AUTHCFG.sms&&!AUTHCFG.demo){SX.modal(`<h2>${P('Verify your mobile number')}</h2><p class="mute">${P('Text-message codes are being switched on. Your number is saved; we will ask you to verify it as soon as they are ready.')}</p><div class="lv-row-end"><button class="btn p" data-sx="closeModal">${P('OK')}</button></div>`,{label:'Verify'});return}
 try{const r=await authApi('/contact/start',{value});vflow={flow:r.flow,kind};
  SX.modal(`<h2>${P('Enter the 6-digit code')}</h2><p class="mute">${P('We sent it to')} ${E(r.sentTo)}.</p>${r.demo?`<p class="lv-demo">${P('Test code')}: <b>${E(r.demo)}</b></p>`:''}
   <form data-sxf="lvcode" class="lv-code"><input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="\\d{6}" required autofocus aria-label="${E(P('Code'))}"><button class="btn p" type="submit">${P('Verify')}</button></form><p class="lv-err" role="alert" hidden></p>`,{label:'Verify'})}
 catch(e){toast(e.message)}};
SX.chg.lvcode=async(a,f)=>{const code=String(new FormData(f).get('code')||'').trim(),err=f.parentElement.querySelector('.lv-err');if(!vflow)return;
 try{const r=await authApi('/contact/verify',{flow:vflow.flow,code});SX.user=r.user;vflow=null;SX.closeModal(true);paintBadge();toast(P('Verified'));render();showCard(you(),false)}
 catch(e){err.textContent=e.message;err.hidden=false}};

// ---------------------------------------------------------------- account: name sync, badge, re-check when the tab comes back
function paintBadge(){const a=document.getElementById('sxAcct');if(!a||!SX.user)return;const v=SX.user.phoneVerified||SX.user.emailVerified;a.classList.toggle('lv-v',!!v);a.title=P('Account & security')+(v?' · '+P('Verified'):'')}
const lu0=SX.loadUser;
SX.loadUser=async()=>{await lu0();if(!AUTHCFG)authApi('/config').then(c=>{AUTHCFG=c}).catch(()=>{});
 const m=you();
 if(SX.user){if((!m.name||m.name==='You')&&SX.user.name){m.name=SX.user.name;m.av=SX.user.name.split(' ').map(x=>x[0]).join('').slice(0,2).toUpperCase();SX.save();SX.paintWho();if(page==='dash')render()}
  if(!m.ph&&SX.user.phone){m.ph=SX.user.phone;SX.save()}}
 paintBadge();
 if(!cardDone(m))openCard()};
let lastCheck=0;
const recheck=()=>{if(Date.now()-lastCheck<4000)return;lastCheck=Date.now();SX.loadUser()};
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')recheck()});
addEventListener('pageshow',e=>{if(e.persisted)recheck()});
addEventListener('focus',recheck);

// ---------------------------------------------------------------- 3D body follows the person (wait for the engine instead of dropping the request)
SX.applyModel=async()=>{const m=SX.me();if(typeof A==='undefined'||!A.ready){SX.pendingModel=true;clearTimeout(SX._amT);SX._amT=setTimeout(SX.applyModel,400);return}
 SX.pendingModel=false;try{if(A.focus||A.patient)A.clearFocus();if(A.sex!==m.sex)await A.setSex(m.sex)}catch(e){console.warn(e)}if(page==='dash'||page==='lab')render()};

// ---------------------------------------------------------------- vitals the person enters (no made-up numbers anywhere)
const vit=m=>(S.vitals[m.id]=S.vitals[m.id]||[]);
const latest=(m,k)=>{const l=vit(m);for(let i=l.length-1;i>=0;i--)if(l[i][k]!=null)return l[i];return null};
SX.latest=latest;
SX.latestVital=k=>{const m=SX.me();if(!m)return null;if(k==='hr'){const r=latest(m,'hr');return r?r.hr+' bpm':null}
 if(k==='bp'){const r=latest(m,'sys');return r?r.sys+'/'+r.dia:null}if(k==='glu'){const r=latest(m,'glu');return r?r.glu+' mg/dL':null}return null};
const ago=t=>{const d=Math.round((Date.now()-t)/864e5);return d<1?P('today'):d===1?P('yesterday'):d+' '+P('days ago')};
const alarm=r=>{const o=[];if(r.sys>=180||r.dia>=120)o.push(P('Blood pressure this high needs medical attention now.'));if(r.sys&&r.sys<90&&r.dia<60)o.push(P('Blood pressure is low. If you feel faint, dizzy or confused, get medical help.'));
 if(r.hr>=130||(r.hr&&r.hr<45))o.push(P('This heart rate is outside the usual resting range.'));if(r.glu&&r.glu<70)o.push(P('Blood sugar is low. Take sugar or juice now if you can swallow safely.'));if(r.glu>=300)o.push(P('Blood sugar is very high.'));return o};
SX.lvVitalsHero=m=>{const h=latest(m,'hr'),b=latest(m,'sys'),g=latest(m,'glu'),bmi=SX.bmi(m);
 if(!h&&!b&&!g)return `<div class="card sx-hero lv-hero0"><div class="sx-hero-t"><div><small>${E(m.name)} · ${E(P('Health snapshot'))}</small><b class="lv-h0">${P('No readings yet')}</b><p class="mute sm" style="margin:4px 0 0">${P('Add a heart rate, blood pressure or sugar reading to see it here and on the body.')}</p></div>
  <div class="sx-hero-v">${bmi?vTile('BMI',bmi.toFixed(1)):''}</div></div><div style="padding:6px 0 12px"><button class="btn p sm" data-sx="vlog">＋ ${P('Add a reading')}</button></div></div>`;
 const bpm=h?h.hr:null,beat=bpm?Math.max(.35,Math.min(1.6,60/bpm)).toFixed(2):'1',when=Math.max(h?h.t:0,b?b.t:0,g?g.t:0);
 return `<div class="card sx-hero ${bpm?'':'lv-noecg'}" style="--beat:${beat}s"><div class="sx-hero-t"><div><small>${E(m.name)} · ${E(P('Health snapshot'))} · ${E(ago(when))}</small>${bpm?`<b class="sx-hero-hr"><i></i>${bpm}<span>bpm</span></b>`:`<b class="lv-h0">${P('Heart rate not added')}</b>`}</div>
  <div class="sx-hero-v">${b?vTile('BP',b.sys+'/'+b.dia):''}${g?vTile('Sugar',g.glu+' mg/dL'):''}${bmi?vTile('BMI',bmi.toFixed(1)):''}</div></div>
  ${bpm?`<div class="sx-ecg" aria-hidden="true"><svg viewBox="0 0 960 64" preserveAspectRatio="none"><path d="${ECGP}"/></svg></div>`:''}<div class="lv-hero-a"><button class="btn s sm" data-sx="vlog">＋ ${P('Add a reading')}</button></div></div>`};
SX.lvVitalsCard=m=>{const l=vit(m).slice(-5).reverse(),bmi=SX.bmi(m);
 return `<div class="card"><div class="hd"><h3>${P('Vitals')}</h3><button class="btn s sm" data-sx="vlog">＋ ${P('Add')}</button></div>${l.length?`<div class="lv-vlist">${l.map(r=>`<div class="row"><div class="grow"><b>${[r.hr!=null?r.hr+' bpm':'',r.sys!=null?r.sys+'/'+r.dia+' mmHg':'',r.glu!=null?r.glu+' mg/dL '+(r.gt==='fasting'?P('fasting'):r.gt==='pp'?P('after food'):''):''].filter(Boolean).join(' · ')}</b><small>${E(SX.fmtT(r.t))}</small></div><button class="btn g sm" data-sx="vdel:${r.id}" aria-label="${E(P('Delete reading'))}">✕</button></div>`).join('')}</div>`:`<p class="mute sm" style="margin:0">${P('No readings yet.')}</p>`}
  ${bmi?`<p class="mute sm" style="margin:10px 0 0">BMI ${bmi.toFixed(1)} · ${E(SX.bmiCat(bmi))}</p>`:''}</div>`};
SX.act.vlog=()=>{const m=SX.me();SX.modal(`<h2>${P('Add a reading for')} ${E(m.name)}</h2><p class="mute">${P('Fill in what you measured. Leave the rest empty.')}</p>
 <form class="form" data-sxf="vsave"><label>${P('Heart rate')} <small>bpm</small><input name="hr" type="number" min="25" max="250" inputmode="numeric"></label><label>${P('Weight')} <small>kg</small><input name="w" type="number" min="2" max="300" step="0.1" inputmode="decimal" value="${E(m.w||'')}"></label>
  <label>${P('Blood pressure')} <small>${P('upper')}</small><input name="sys" type="number" min="50" max="280" inputmode="numeric"></label><label>${P('Blood pressure')} <small>${P('lower')}</small><input name="dia" type="number" min="30" max="180" inputmode="numeric"></label>
  <label>${P('Blood sugar')} <small>mg/dL</small><input name="glu" type="number" min="20" max="700" inputmode="numeric"></label><label>${P('When')}<select name="gt"><option value="fasting">${P('Fasting')}</option><option value="pp">${P('After food')}</option><option value="random" selected>${P('Any time')}</option></select></label>
  <p class="full lv-err" role="alert" hidden></p><div class="full lv-row-end"><button class="btn s" type="button" data-sx="closeModal">${P('Cancel')}</button><button class="btn p" type="submit">${P('Save')}</button></div></form>`,{label:P('Add a reading')})};
SX.chg.vsave=(a,f)=>{const m=SX.me(),fd=new FormData(f),n=k=>{const v=String(fd.get(k)||'').trim();return v===''?null:+v},err=f.querySelector('.lv-err'),say=t=>{err.textContent=t;err.hidden=false};
 const r={id:uid('v'),t:Date.now()},hr=n('hr'),sys=n('sys'),dia=n('dia'),glu=n('glu'),w=n('w');
 if(hr!=null){if(!(hr>=25&&hr<=250))return say(P('Heart rate should be between 25 and 250.'));r.hr=Math.round(hr)}
 if(sys!=null||dia!=null){if(sys==null||dia==null)return say(P('Enter both blood pressure numbers.'));if(!(sys>=50&&sys<=280&&dia>=30&&dia<=180&&sys>dia))return say(P('Please check the blood pressure numbers.'));r.sys=Math.round(sys);r.dia=Math.round(dia)}
 if(glu!=null){if(!(glu>=20&&glu<=700))return say(P('Please check the blood sugar value.'));r.glu=Math.round(glu);r.gt=String(fd.get('gt')||'random')}
 const wChanged=w!=null&&w!==m.w;if(w!=null&&!(w>=2&&w<=300))return say(P('Please check the weight.'));
 if(r.hr==null&&r.sys==null&&r.glu==null&&!wChanged)return say(P('Enter at least one value.'));
 if(wChanged)m.w=w;if(r.hr!=null||r.sys!=null||r.glu!=null)vit(m).push(r);SX.save();SX.closeModal();render();
 const al=alarm(r);if(al.length)SX.modal(`<h2>⚠️ ${P('Please check this reading')}</h2>${al.map(x=>`<p>${E(x)}</p>`).join('')}<p class="mute">${P('If you feel unwell — chest pain, breathlessness, fainting, confusion — call 112 now. Otherwise, measure again after resting for 5 minutes and talk to your doctor.')}</p><div class="lv-row-end"><a class="btn red" href="tel:112">${P('Call 112')}</a><button class="btn s" data-sx="closeModal">${P('OK')}</button></div>`,{label:'Check reading'});
 else toast(P('Reading saved'))};
SX.act.vdel=([id])=>{const m=SX.me();S.vitals[m.id]=vit(m).filter(r=>r.id!==id);SX.save();render()};

// ---------------------------------------------------------------- Care: honest pages until verified doctors are live
const visits=m=>SX.apptsOf(m);
const upcoming=m=>visits(m).filter(v=>v.date&&v.date>=SX.today()).sort((a,b)=>(a.date+(a.time||'')).localeCompare(b.date+(b.time||'')));
SX.lvVisitCard=m=>{const a=upcoming(m)[0];
 return `<div class="card"><div class="hd"><h3>${P('Next visit')}</h3><button class="btn s sm" data-sx="tab:appts">${P('All')}</button></div>${a?`<div class="lv-visit"><div class="lv-vd"><b>${E(new Date(a.date+'T00:00').getDate())}</b><small>${E(new Date(a.date+'T00:00').toLocaleDateString('en-IN',{month:'short'}))}</small></div><div class="grow"><b>${E(a.dn||P('Doctor visit'))}</b><small class="mute">${E([a.dh,a.time,a.why].filter(Boolean).join(' · '))}</small></div></div>`:`<p class="mute" style="margin:0 0 10px">${P('No upcoming visits for')} ${E(m.name)}.</p><button class="btn p sm" data-sx="tab:appts">＋ ${P('Add a visit')}</button>`}</div>`};
let vEdit=false;
SX.reg('appts',{head:()=>[P('Visits'),P('Keep track of doctor visits for the whole family.')],after:()=>{},
 render:()=>{const m=SX.me(),up=upcoming(m),past=visits(m).filter(v=>!up.includes(v)).sort((a,b)=>(b.date||'').localeCompare(a.date||'')),tm=SX.today();
  const row=a=>`<div class="row"><div class="lv-vd"><b>${E(a.date?new Date(a.date+'T00:00').getDate():'—')}</b><small>${E(a.date?new Date(a.date+'T00:00').toLocaleDateString('en-IN',{month:'short'}):'')}</small></div><div class="grow"><b>${E(a.dn||P('Doctor visit'))}</b><small>${E([a.dh,a.date?fmtDate(a.date):'',a.time,a.type,a.why].filter(Boolean).join(' · '))}</small></div><button class="btn g sm" data-sx="vrm:${a.id}" aria-label="${E(P('Remove visit'))}">✕</button></div>`;
  return `<div class="card wide"><div class="hd"><h3>${E(poss(m.name))} ${P('visits')}</h3><button class="btn p sm" data-sx="vadd">＋ ${P('Add a visit')}</button></div>
   ${vEdit?`<form class="form lv-vform" data-sxf="vsavev"><label>${P('Doctor')}<input name="dn" required maxlength="60" placeholder="${E(P('e.g. Dr. Rao'))}"></label><label>${P('Hospital or clinic')}<input name="dh" maxlength="80"></label>
    <label>${P('Date')}<input name="date" type="date" required value="${tm}"></label><label>${P('Time')}<input name="time" type="time"></label>
    <label>${P('Type')}<select name="type"><option>${P('In person')}</option><option>${P('Video call')}</option></select></label><label>${P('Reason')}<input name="why" maxlength="120"></label>
    <div class="full lv-row-end"><button class="btn s" type="button" data-sx="vadd">${P('Cancel')}</button><button class="btn p" type="submit">${P('Save visit')}</button></div></form>`:''}
   ${up.length?`<h4 class="sx-h4">${P('Upcoming')}</h4>${up.map(row).join('')}`:''}${past.length?`<h4 class="sx-h4">${P('Earlier')}</h4>${past.map(row).join('')}`:''}${!up.length&&!past.length&&!vEdit?`<div class="sx-empty">${P('No visits yet. Add one to get it on Home.')}</div>`:''}</div>
   ${soon(P('Online booking'),P('Booking with verified doctors and hospitals is on the way. When it opens, you will choose what to share for each visit, and every share is recorded in your consent history.'))}`}});
SX.act.vadd=()=>{vEdit=!vEdit;render()};
SX.chg.vsavev=(a,f)=>{const fd=new FormData(f),g=k=>String(fd.get(k)||'').trim();if(!g('dn')||!g('date')){toast(P('Add the doctor and date'));return}
 visits(SX.me()).push({id:uid('a'),dn:g('dn').slice(0,60),dh:g('dh').slice(0,80),date:g('date'),time:g('time'),type:g('type'),why:g('why').slice(0,120)});vEdit=false;SX.save();render();toast(P('Visit saved'))};
SX.act.vrm=([id])=>{const m=SX.me();S.appts[m.id]=visits(m).filter(v=>v.id!==id);SX.save();render()};
function soon(t,b,ic){return `<div class="card wide lv-soon"><div class="lv-soon-ic" aria-hidden="true">${ic||'✦'}</div><div><h3>${E(t)} <span class="lv-tag">${P('Coming soon')}</span></h3><p class="mute">${E(b)}</p></div></div>`}
SX.lvSoon=soon;
SX.reg('docs',{head:()=>[P('Doctors'),P('Verified doctors you can talk to.')],after:()=>{},
 render:()=>soon(P('Verified doctors'),P('Doctors join after we check their registration with the National Medical Commission. Once your doctor is verified, you will find them here and can share reports with them for a visit.'),'🩺')+
  `<div class="card wide"><h3>${P('Your doctors so far')}</h3>${[...new Set(S.members.flatMap(m=>visits(m).map(v=>v.dn)).filter(Boolean))].map(n=>`<div class="row"><div class="grow"><b>${E(n)}</b><small>${P('From your visits')}</small></div></div>`).join('')||`<p class="mute sm">${P('Doctors you add to visits appear here.')}</p>`}</div>`});
SX.reg('msgs',{head:()=>[P('Messages'),P('Secure messages with your doctor.')],after:()=>{},
 render:()=>soon(P('Secure messages'),P('Messaging opens only between verified members and verified doctors. Conversations will be private to you and your doctor, and you can share a report or a 3D view in a message.'),'💬')});
SX.reg('bill',{head:()=>[P('Bills'),P('Medical bills and receipts.')],after:()=>{},
 render:()=>soon(P('Bills and claims'),P('Keep hospital bills and pharmacy receipts together and see what your insurance covers. Until then, save bills in Records & Labs → Vault under "Other".'),'🧾')});

// ---------------------------------------------------------------- medicine ordering: no simulated orders for real people
SX.act.place=()=>{SX.modal(`<h2>${P('Online ordering is not available yet')}</h2><p class="mute">${P('We are onboarding licensed pharmacies. Your basket is saved: you can show it at any pharmacy, or order here as soon as a pharmacy near you joins.')}</p><div class="lv-row-end"><button class="btn p" data-sx="closeModal">${P('OK')}</button></div>`,{label:'Ordering'})};

// ---------------------------------------------------------------- Home tile + Family notices
SX.lvCardTile=m=>{if(m.rel!=='You')return '';if(!cardDone(m))return `<div class="card lv-review"><div class="hd"><h3>${P('Finish your health card')}</h3></div><p class="mute sm" style="margin:0 0 10px">${P('Name, date of birth, sex, blood group and mobile number.')}</p><button class="btn p sm" data-sx="lvcardedit">${P('Complete now')}</button></div>`;
 return `<button class="card lv-hc" data-sx="lvcardshow:${m.id}" aria-label="${E(P('Open health card'))}"><div class="hd"><h3>${P('Health card')}</h3><span class="mute sm">${P('Tap to open')}</span></div>${cardHTML(m)}</button>`};
SX.extend('family',{before(){const r=S.members.filter(m=>m.review);return r.length?`<div class="card wide lv-review"><h3>${P('Please check these profiles')}</h3><p class="mute sm" style="margin:0">${P('An earlier version added sample people. We removed the sample data and kept what you entered for')} ${r.map(m=>'<b>'+E(m.name)+'</b>').join(', ')}. ${P('Check the name and details, or remove the profile if it is not someone in your family.')}</p></div>`:''}});

// ---------------------------------------------------------------- delete account (right to erasure)
SX.extend('set',{after(){if(!SX.user)return '';return `<div class="card wide"><div class="hd"><h3>${P('Delete account')}</h3></div><p class="mute sm" style="margin:-4px 0 12px">${P('Removes your account, sign-in methods and contact details from our servers. Health records on this device are separate: delete them in My data.')}</p><button class="btn s" data-sx="acctdel" style="color:var(--red)">${P('Delete my account…')}</button></div>`}});
SX.act.acctdel=()=>{SX.modal(`<h2>${P('Delete your account?')}</h2><p class="mute">${P('This cannot be undone. Your plan ends and you are signed out on every device.')}</p><form data-sxf="acctdel2" class="form"><label class="full">${P('Type DELETE to confirm')}<input name="c" autocomplete="off" required></label><p class="full lv-err" role="alert" hidden></p><div class="full lv-row-end"><button class="btn s" type="button" data-sx="closeModal">${P('Keep my account')}</button><button class="btn red" type="submit">${P('Delete account')}</button></div></form>`,{label:'Delete account'})};
SX.chg.acctdel2=async(a,f)=>{const c=String(new FormData(f).get('c')||''),err=f.querySelector('.lv-err');try{await authApi('/account/delete',{confirm:c});SX.user=null;location.href='/?deleted=1'}catch(e){err.textContent=e.message;err.hidden=false}};

// ---------------------------------------------------------------- one-time notice after old sample data was removed
if(S.purged&&!S.purged.seen){setTimeout(()=>{if(cardDone(you())){toast(P('We removed sample data from an earlier version. Anything you added yourself is kept.'));S.purged.seen=1;SX.save()}},2500)}
}
