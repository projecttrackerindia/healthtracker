// ===================== live layer 14: deep links, idle sign-out, care that fits the person, phone polish =====================
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;

// ---------------------------------------------------------------- A. deep links: /app/<person>/<profile>/<page> (opaque ids, never names)
const b64=buf=>btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const HID={};async function hid(s){if(HID[s])return HID[s];if(!crypto.subtle){HID[s]=btoa(s).slice(0,10);return HID[s]}const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode('tht-link|'+(S.key||'')+'|'+s));HID[s]=b64(d).slice(0,12);return HID[s]}
const PAGE_OK=p=>typeof PAGES==='object'&&!!PAGES[p];
let urlT=0;async function syncUrl(replace){if(!S.key)return;const u=SX.user?await hid(SX.user.id):'guest',m=await hid(SX.me().id);const path=`/app/${u}/${m}/${page}`;if(location.pathname===path)return;try{history[replace?'replaceState':'pushState']({page,mid:SX.me().id},'',path+location.search)}catch(e){}}
new MutationObserver(()=>{clearTimeout(urlT);urlT=setTimeout(()=>syncUrl(false),80)}).observe(document.body,{attributes:true,attributeFilter:['data-page']});
addEventListener('popstate',e=>{const st=e.state;if(!st)return;if(st.mid&&SX.member(st.mid)&&S.active!==st.mid){S.active=st.mid;SX.save()}if(st.page&&PAGE_OK(st.page)&&page!==st.page)go(st.page)});
(async()=>{const parts=location.pathname.split('/').filter(Boolean);if(parts[0]!=='app'||parts.length<4)return;const [,,mtok,pg]=parts;for(let i=0;i<40&&!(S.members&&S.members.length);i++)await new Promise(r=>setTimeout(r,250));
 for(const m of S.members||[]){if(await hid(m.id)===mtok){if(S.active!==m.id){S.active=m.id;SX.save()}break}}
 if(PAGE_OK(pg)&&page!==pg)setTimeout(()=>go(pg),300);setTimeout(()=>syncUrl(true),800)})();
// the person switcher changes the profile: reflect it
const save14=SX.save;SX.save=function(){const r=save14.apply(this,arguments);clearTimeout(urlT);urlT=setTimeout(()=>syncUrl(true),200);return r};

// ---------------------------------------------------------------- B. signed out after 30 minutes without a touch
const IDLE_MS=30*60*1000,WARN_MS=60*1000;let lastAct=Date.now(),warned=false;
const bump=()=>{lastAct=Date.now();if(warned){warned=false;const t=document.getElementById('lv14idle');if(t)t.remove()}};
['pointerdown','keydown','touchstart','scroll','input'].forEach(ev=>addEventListener(ev,bump,{passive:true}));
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')check()});
async function idleOut(){try{await fetch('/api/v1/auth/logout',{method:'POST',headers:{'x-tht':'1','content-type':'application/json'},credentials:'same-origin',body:'{}'})}catch(e){}try{sessionStorage.setItem('tht.idle','1')}catch(e){}location.href='/signin?idle=1'}
function check(){if(!SX.user)return;const idle=Date.now()-lastAct;if(window.__callOpen)return;if(idle>=IDLE_MS){idleOut();return}
 if(idle>=IDLE_MS-WARN_MS&&!warned){warned=true;const t=document.createElement('div');t.id='lv14idle';t.className='lv14-idle';t.innerHTML=`<b>${P('Still there?')}</b><span>${P('You will be signed out in a minute to protect your records.')}</span><button class="btn p sm">${P('Stay signed in')}</button>`;t.querySelector('button').onclick=bump;document.body.appendChild(t)}}
setInterval(check,15000);

// ---------------------------------------------------------------- C. care that fits the person: pregnancy and cycle only where they apply; "you're healthy" until a plan exists
const female=m=>m&&m.sex==='female';
const tv14=SX.tabVisible;SX.tabVisible=k=>{const m=SX.me();if(k==='cycle'&&!(female(m)&&m.age>=10&&m.age<=60))return false;if(k==='preg'&&!(SX.canPreg(m)||(SX.pregOn&&SX.pregOn(m))))return false;if(k==='child'&&!(m&&m.age<18))return false;if(k==='pregcare'&&!(SX.pregOn&&SX.pregOn(m)))return false;return tv14(k)};
// the Care group always opens on something that applies
{const care=SX.G.find(g=>g.k==='care');if(care){const fix=()=>{const m=SX.me();const preg=SX.pregOn&&SX.pregOn(m);if(!preg){const t=['careplan'];if(female(m)&&m.age>=10&&m.age<=60)t.push('cycle');if(m.age<18)t.push('child');care.tabs=t}};fix();const pn=SX.pregNav;SX.pregNav=()=>{pn();fix()}}}
S.careSuggest=S.careSuggest||{};
function healthyHTML(m){const sug=S.careSuggest[m.id];const d=SX.midOf(m.id);const conds=(d.conditions||[]).filter(Boolean);const flags=(SX.labFlags?SX.labFlags(m):[]).slice(0,3);
 return `<div class="card wide lv14-healthy"><div class="lv14-hh"><div class="lv14-ok">✓</div><div><h3>${P('Nothing to manage right now')}</h3><p class="mute sm">${E(m.name.split(' ')[0])} ${P('has no ongoing condition on record. A care plan appears here when a report shows something to follow, a doctor adds a condition after a visit, or you set one up.')}</p></div></div>
  ${sug?`<div class="lv14-sug"><b>🩺 ${P('From your doctor')}</b><p>${E(sug.doc?'Dr '+sug.doc+': ':'')}${E(sug.cond)}${sug.t?` · ${new Date(sug.t).toLocaleDateString('en-IN',{day:'numeric',month:'short'})}`:''}</p><div class="row"><button class="btn p sm" data-sx="careenable:${E(encodeURIComponent(sug.cond))}">${P('Start a care plan for this')}</button><button class="btn s sm" data-sx="caredismiss">${P('Not now')}</button></div></div>`:''}
  ${!sug&&(conds.length||flags.length)?`<div class="lv14-sug soft"><b>${P('Worth a care plan?')}</b><p>${conds.length?P('On the health card:')+' '+E(conds.join(', '))+'. ':''}${flags.length?P('Out of range recently:')+' '+flags.map(f=>E(f.st.L.n)).join(', ')+'.':''}</p><div class="row">${conds.slice(0,2).map(c=>`<button class="btn s sm" data-sx="careenable:${E(encodeURIComponent(c))}">${E(c)}</button>`).join('')}</div></div>`:''}
  <div class="row" style="margin-top:10px"><button class="btn s sm" data-sx="careshow">＋ ${P('Set up a care plan')}</button><button class="btn s sm" data-sx="tab:assist">✦ ${P('Ask the assistant')}</button></div></div>`}
SX.extend('careplan',{before(){const m=SX.me();const cp=(S.care||{})[m.id];if(cp&&cp.on)return '';return healthyHTML(m)},mounted(){const m=SX.me();const cp=(S.care||{})[m.id];if(!(cp&&cp.on)){const f=document.querySelector('#page .lv14-healthy ~ .card');if(f&&!window.__careShow){f.classList.add('lv14-hidden')}}}});
SX.act.careshow=()=>{window.__careShow=true;const f=document.querySelector('#page .lv14-hidden');if(f){f.classList.remove('lv14-hidden');f.scrollIntoView({behavior:'smooth',block:'start'})}};
SX.act.careenable=([c])=>{window.__careShow=true;render();const f=document.querySelector('#page .lv14-hidden');if(f)f.classList.remove('lv14-hidden');const inp=document.querySelector('#page [name=cond],#page input[data-k=cond]');if(inp){inp.value=decodeURIComponent(c);inp.focus();inp.scrollIntoView({behavior:'smooth',block:'center'})}};
SX.act.caredismiss=()=>{delete S.careSuggest[SX.me().id];SX.save();render()};
// a doctor's e-prescription note becomes a care suggestion for that person
document.addEventListener('tht:notice',ev=>{const n=ev.detail;if(!n||n.kind!=='prescription'||!n.ref)return;const m=SX.member(n.member)||SX.me();const cond=n.ref.diagnosis||'';if(cond&&!((S.care||{})[m.id]||{}).on){S.careSuggest[m.id]={cond,doc:n.ref.doctor||'',t:n.t*1000}}});
// readings/reports pages: no pregnancy prompts for people it cannot apply to
const prg=SX.pregTrackers;if(prg)SX.pregTrackers=(...a)=>{const m=SX.me();return SX.canPreg(m)||(SX.pregOn&&SX.pregOn(m))?prg(...a):''};

// ---------------------------------------------------------------- D. phone polish: swipe between sub-tabs, pull to refresh, hiding tab bar, haptics, greeting
let tx=0,ty=0,tt=0;
addEventListener('touchstart',e=>{if(!phone()||e.touches.length!==1)return;tx=e.touches[0].clientX;ty=e.touches[0].clientY;tt=Date.now()},{passive:true});
addEventListener('touchend',e=>{if(!phone()||!tt)return;const t=e.changedTouches[0],dx=t.clientX-tx,dy=t.clientY-ty;tt=0;if(Math.abs(dx)<70||Math.abs(dy)>50||e.target.closest('.sx-modal,.lv6-map,.lv13-gmap,canvas,input,textarea,.lv2-rail,.sx-tabs,.lv11-ecgs,.lv12-inc'))return;
 const tabs=[...document.querySelectorAll('#page>.sx-tabs button')].filter(b=>b.offsetParent);const i=tabs.findIndex(b=>b.classList.contains('on'));if(i<0)return;const j=dx<0?i+1:i-1;if(j<0||j>=tabs.length)return;tabs[j].click();hap()},{passive:true});
let pulling=0;addEventListener('touchmove',e=>{if(!phone()||e.touches.length!==1||scrollY>0||document.querySelector('.sx-modal'))return;const dy=e.touches[0].clientY-ty;if(dy>90&&!pulling){pulling=1;const el=document.createElement('div');el.className='lv14-pull';el.textContent='↻ '+P('Refreshing…');document.body.appendChild(el);Promise.resolve(SX.sync&&SX.sync()).catch(()=>{}).finally(()=>{setTimeout(()=>{el.remove();pulling=0;try{render()}catch(e){}},700)})}},{passive:true});
let lastY=0;addEventListener('scroll',()=>{if(!phone())return;const bar=document.getElementById('mtab');if(!bar)return;const y=scrollY;const down=y>lastY+8&&y>120;const up=y<lastY-8||y<60;if(down)bar.classList.add('lv14-hide');else if(up)bar.classList.remove('lv14-hide');lastY=y;document.body.classList.toggle('lv14-scrolled',y>40)},{passive:true});
function hap(){try{const c=window.Capacitor;if(c&&c.Plugins&&c.Plugins.Haptics)c.Plugins.Haptics.impact({style:'LIGHT'});else if(navigator.vibrate)navigator.vibrate(8)}catch(e){}}
document.addEventListener('click',e=>{if(phone()&&e.target.closest('#mtab button, .sx-tabs button'))hap()});
// greeting in the app bar on phones
function greet(){if(!phone())return;const h=new Date().getHours();const g=h<12?P('Good morning'):h<17?P('Good afternoon'):P('Good evening');let el=document.getElementById('lv14greet');if(!el){el=document.createElement('div');el.id='lv14greet';const top=document.querySelector('.top');if(top)top.insertBefore(el,top.firstChild)}const m=SX.me();el.textContent=g+(m?', '+m.name.split(' ')[0]:'')}
setTimeout(greet,500);setInterval(greet,60000);
// hide the environment badge on phones; it is for the team
if(phone()){const b=document.getElementById('lv4env');if(b)b.style.display='none'}
}
