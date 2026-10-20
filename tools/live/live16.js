// ===================== live layer 16: nothing shows without a sign-in · a demo only when someone asks for one =====================
{
const P=SX.p,S=SX.S;
const LSK16=(typeof LSK==='string')?LSK:'dk6';
const ss=(k,v)=>{try{if(v===undefined)return sessionStorage.getItem(k);if(v===null)sessionStorage.removeItem(k);else sessionStorage.setItem(k,v)}catch(e){return null}};
const ls=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){return null}};
const qs=new URLSearchParams(location.search);

// ---------------------------------------------------------------- A. the lock: the record on this device is never painted while nobody is signed in
function lock(){document.body.classList.add('lv16-lock');if(window.__lv16auth)window.__lv16auth()}
function unlock(){document.body.classList.remove('lv16-lock')}
SX.lock=lock;
// a device that has ever seen an account keeps that memory, so even offline it asks for the sign-in
const seen=()=>ls('tht.claimed')==='1';
const u0=SX.loadUser;SX.loadUser=async function(){const r=await u0.apply(this,arguments);if(S.demo){SX.user=null;return r}if(SX.user){ls('tht.claimed','1');unlock()}return r};
// a session that ends while the app is open (expired cookie, signed out elsewhere) locks the screen at once
const api0=SX.api;SX.api=async function(path,o){try{return await api0.call(this,path,o)}catch(e){if(e&&e.status===401&&!S.demo){SX.user=null;lock()}throw e}};
async function decide(){
 if(S.demo)return;                       // the sample family is open on purpose
 if(!navigator.onLine){if(seen()||!SX.user)lock();return}
 let user=null;try{const r=await fetch('/api/v1/auth/me',{credentials:'same-origin',cache:'no-store'});user=(await r.json()).user}catch(e){if(seen())lock();return}
 if(user){ls('tht.claimed','1');unlock();return}
 lock()}
// run early (before the first paint settles) and again after the account fetch, so a signed-out device never flashes the record
if(seen()||!SX.user)document.body.classList.add('lv16-lock');
setTimeout(decide,300);

// ---------------------------------------------------------------- B. demo: a fictional family, in memory only, opened only by asking for it
const DEMO_KEY='demo-'+Math.random().toString(36).slice(2,10)+Math.random().toString(36).slice(2,10);
function sample(){const t=Date.now(),d=864e5,day=n=>new Date(t-n*d).toISOString().slice(0,10);
 const M=[{id:'d1',pid:null,name:'Meera Raghavan',rel:'You',age:36,sex:'female',w:61,h:162,av:'MR',c:'',shared:true},
  {id:'d2',pid:null,name:'Vikram Raghavan',rel:'Husband',age:39,sex:'male',w:78,h:175,av:'VR',c:'',shared:true},
  {id:'d3',pid:null,name:'Kamala Devi',rel:'Mother',age:64,sex:'female',w:66,h:155,av:'KD',c:'',shared:true},
  {id:'d4',pid:'d1',name:'Aarav',rel:'Son',age:7,sex:'male',w:22,h:118,av:'AA',c:'',shared:true}];
 const V={d2:[{id:'v1',t:t-1*d,sys:138,dia:88,hr:76},{id:'v2',t:t-8*d,sys:142,dia:91,hr:79},{id:'v3',t:t-15*d,sys:135,dia:86,hr:74},{id:'v4',t:t-22*d,sys:146,dia:93,hr:81}],
  d3:[{id:'v5',t:t-1*d,glu:128,hr:72},{id:'v6',t:t-3*d,glu:141},{id:'v7',t:t-6*d,sys:131,dia:82,hr:70},{id:'v8',t:t-10*d,glu:119}],
  d1:[{id:'v9',t:t-2*d,sys:112,dia:74,hr:68}]};
 const R={d2:[{id:'r1',k:'lab',key:'ldl',val:158,date:day(12)},{id:'r2',k:'lab',key:'hdl',val:41,date:day(12)},{id:'r3',k:'lab',key:'tg',val:171,date:day(12)},{id:'r4',k:'lab',key:'ldl',val:176,date:day(200)}],
  d3:[{id:'r5',k:'lab',key:'hba1c',val:6.8,date:day(20)},{id:'r6',k:'lab',key:'glu_f',val:124,date:day(20)},{id:'r7',k:'lab',key:'hba1c',val:7.3,date:day(110)},{id:'r8',k:'lab',key:'creat',val:0.9,date:day(20)}],
  d1:[{id:'r9',k:'lab',key:'hb',val:11.9,date:day(30)},{id:'r10',k:'lab',key:'vitd',val:21,date:day(30)},{id:'r11',k:'lab',key:'tsh',val:2.4,date:day(30)}]};
 const MD={d3:[{id:'md1',n:'Metformin 500 mg',s:'500 mg',when:['Morning','Night'],dur:'',note:'After food',by:'Dr Sample',t:t-40*d}],
  d2:[{id:'md2',n:'Amlodipine 5 mg',s:'5 mg',when:['Morning'],dur:'',note:'',by:'Dr Sample',t:t-60*d}]};
 return {v:1,lang:S.lang||'en',active:'d1',created:t-90*d,members:M,vitals:V,results:R,meds:MD,key:DEMO_KEY,demo:true,consent:{},net:{}}}
function enterDemo(){
 if(!S.demo)SX.save(true);                        // the real record is flushed first (a pending save must never carry demo data)
 SX.wiped=true;                                   // nothing the demo does is written to this device
 const keep={};['lang','net'].forEach(k=>{if(S[k]!==undefined)keep[k]=S[k]});
 const shape={};Object.keys(S).forEach(k=>{const v=S[k];shape[k]=Array.isArray(v)?[]:(v&&typeof v==='object')?{}:v});   // every section the app expects exists, empty
 Object.keys(S).forEach(k=>{delete S[k]});Object.assign(S,shape,sample(),{net:keep.net||{},lang:keep.lang||'en'});
 SX.user=null;ss('tht.demo','1');unlock();document.body.classList.add('lv16-demo');
 const el=document.getElementById('lv15auth');if(el)el.remove();document.body.classList.remove('lv15-locked');
 banner();try{go('dash')}catch(e){}try{render()}catch(e){}try{if(SX.pregNav)SX.pregNav()}catch(e){}try{if(SX.paintNav)SX.paintNav()}catch(e){}
 toast(P('Demo family loaded — nothing here is saved'))}
function exitDemo(){ss('tht.demo',null);location.replace('/app')}
SX.demo={enter:enterDemo,exit:exitDemo};
function banner(){if(document.getElementById('lv16demo'))return;const b=document.createElement('div');b.id='lv16demo';b.className='lv16-demo';
 b.innerHTML=`<span>🧪 <b>${P('Demo')}</b> · ${P('a sample family — nothing is saved')}</span><button class="btn p sm">${P('Exit demo & sign in')}</button>`;b.querySelector('button').onclick=exitDemo;document.body.appendChild(b)}
// the server never hears from a demo
const hello0=SX.hello;SX.hello=function(){if(S.demo)return Promise.resolve();return hello0.apply(this,arguments)};
const sync0=SX.sync;if(sync0&&sync0.push){const push0=sync0.push,pull0=sync0.pull;sync0.push=function(){if(S.demo)return;return push0.apply(this,arguments)};sync0.pull=function(){if(S.demo)return;return pull0.apply(this,arguments)}}
// opened on purpose: /app?demo=1 from the website, the "See a demo" link on the sign-in screen, or a reload inside the demo
if(qs.get('demo')==='1'||ss('tht.demo')==='1'||S.demo){try{history.replaceState(null,'',location.pathname)}catch(e){}setTimeout(enterDemo,50)}

// ---------------------------------------------------------------- C. passkeys on the in-app sign-in, and an offer to make one after signing in
const loadAuthJs=()=>window.THT?Promise.resolve():new Promise((res,rej)=>{const sc=document.createElement('script');sc.src='/s/auth.js';sc.onload=res;sc.onerror=rej;document.head.append(sc)});
const pkErr=(f,m)=>{const e=f&&f.querySelector('.lv15-err');if(e){e.textContent=m;e.hidden=false}else toast(m)};
let pkAbort=null;
async function pkSignin(conditional){const f=document.getElementById('lv15f');try{await loadAuthJs();if(!THT.passkey.supported()){if(!conditional)pkErr(f,P('This browser has no passkey support; use your password or a one-time code.'));return}
 if(conditional){if(!(await THT.passkey.conditional()))return;pkAbort=new AbortController();try{await THT.passkey.signin({conditional:true,signal:pkAbort.signal})}catch(e){if(String(e.message)!=='aborted'&&!/cancel/i.test(e.message))return;return}}
 else{if(pkAbort){pkAbort.abort();pkAbort=null}const id=f&&f.id?f.id.value.trim():'';await THT.passkey.signin({id})}
 try{sessionStorage.removeItem('tht.skipauth')}catch(e){}location.reload()}catch(e){if(!conditional)pkErr(f,e.message)}}
document.addEventListener('click',e=>{const b=e.target.closest('#lv15pk');if(b){e.preventDefault();pkSignin(false)}});
// the autofill (conditional) passkey prompt as soon as the sign-in form is on screen
new MutationObserver(()=>{const f=document.getElementById('lv15f');if(f&&f.id&&!f.dataset.pk){f.dataset.pk='1';pkSignin(true)}}).observe(document.body,{childList:true,subtree:true});
// after a sign-in on a device that can hold a passkey: offer once (again after 30 days if declined)
SX.pkOffer=()=>pkOffer();
async function pkOffer(){if(S.demo||!SX.user||SX.user.passkeys>0)return;const last=+(ls('tht.pkoffer')||0);if(Date.now()-last<30*864e5)return;
 try{await loadAuthJs();if(!THT.passkey.supported()||!(await THT.passkey.platform()))return}catch(e){return}
 ls('tht.pkoffer',String(Date.now()));
 SX.modal(`<h2>${P('Sign in faster next time')}</h2><p class="mute">${P('Create a passkey and sign in with your fingerprint, face or screen lock — no password to type. It stays on this device and syncs through your platform account.')}</p><div class="lv-row-end"><button class="btn s" id="pkno">${P('Not now')}</button><button class="btn p" id="pkyes">${P('Create a passkey')}</button></div>`,{label:'Passkey'});
 document.getElementById('pkno').onclick=()=>SX.closeModal();
 document.getElementById('pkyes').onclick=async()=>{const b=document.getElementById('pkyes');b.disabled=true;try{const r=await THT.passkey.register('');SX.user=r.user||SX.user;if(SX.user)SX.user.passkeys=(SX.user.passkeys||0)+1;SX.closeModal();toast(P('Passkey created — next time, just your fingerprint or face'))}catch(e){b.disabled=false;toast(e.message)}}}
(async()=>{for(let i=0;i<60&&!SX.user;i++)await new Promise(r=>setTimeout(r,500));if(!SX.user)return;for(let i=0;i<120&&document.querySelector('.sx-modal');i++)await new Promise(r=>setTimeout(r,1000));setTimeout(pkOffer,1500)})();
}
