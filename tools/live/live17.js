// ===================== live layer 17: phone shell v2 — app bar with a title, pinned Health Card with SOS, sub-tabs in the bar, keyboard-aware assistant =====================
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;
const TITLE={dash:'Home',assist:'Assistant',lab:'Body',heart:'Heart Lab',devices:'Devices',mid:'Medical ID',sos:'SOS',aid:'First aid',contacts:'Contacts',bill:'Bills',orders:'Orders'};

// ---------------------------------------------------------------- A. app bar: one title, from the page
let titleEl=null;
function title(){if(!phone())return;const tb=document.querySelector('.topb');if(!tb)return;if(!titleEl){titleEl=document.createElement('div');titleEl.id='lv17title';tb.insertBefore(titleEl,document.getElementById('sxBell')||null)}
 const h=document.getElementById('hh');let t=TITLE[page]?P(TITLE[page]):(h?h.textContent:'');if(page==='dash')t=P('Home');titleEl.textContent=t.replace(/\s*👋\s*/,'')}

// ---------------------------------------------------------------- B. sub-tabs move into the bar
let slot=null;
function tabs(){if(!phone())return;const top=document.querySelector('.top');if(!top)return;if(!slot){slot=document.createElement('div');slot.id='lv17tabs';top.appendChild(slot)}
 const strip=document.querySelector('#page>.sx-tabs');if(strip){slot.innerHTML='';slot.appendChild(strip);slot.classList.add('has');const on=strip.querySelector('button.on');if(on)on.scrollIntoView({inline:'center',block:'nearest'})}
 else if(!slot.querySelector('.sx-tabs')||!document.body.contains(slot.querySelector('.sx-tabs')))slot.classList.remove('has');
 // a strip that belongs to another page is stale once the page changes without one
 if(!strip&&slot.querySelector('.sx-tabs')&&slot.dataset.page!==page){slot.innerHTML='';slot.classList.remove('has')}
 slot.dataset.page=page;measure()}
function measure(){const top=document.querySelector('.top');if(top)document.documentElement.style.setProperty('--lv17-top',top.getBoundingClientRect().height+'px')}

// ---------------------------------------------------------------- C. the Health Card banner (on until switched off in Medical ID)
if(S.hcBanner===undefined)S.hcBanner=true;
let hc=null;
function hcHTML(){const m=SX.me();if(!m)return '';const d=SX.midOf(m.id);const al=(d.allergies||[]).filter(Boolean),co=(d.conditions||[]).filter(Boolean);
 const line=[al.length?`<i>${P('Allergic')}: ${E(al.slice(0,2).join(', '))}${al.length>2?' +'+(al.length-2):''}</i>`:P('No allergies on record'),co.length?E(co.slice(0,2).join(', ')):''].filter(Boolean).join(' · ');
 return `<button class="bg ${d.blood?'':'none'}" data-sx="tab:mid" aria-label="${P('Medical ID')}">${d.blood?E(d.blood):P('ID')}</button><button class="tx" data-sx="tab:mid" style="all:unset;flex:1;min-width:0;cursor:pointer"><b>${E(m.name)}</b><small>${line}</small></button><button class="sos" data-sx="sos" aria-label="${P('SOS: emergency help')}"><i></i>SOS</button>`}
function banner(){const top=document.querySelector('.top');if(!top)return;if(!hc){hc=document.createElement('div');hc.id='lv17hc';top.appendChild(hc)}
 const on=phone()&&S.hcBanner!==false&&!S.demo?true:(phone()&&S.demo);document.body.classList.toggle('lv17-hc',!!on);if(on){const h=hcHTML();if(hc.innerHTML!==h)hc.innerHTML=h}measure()}
SX.chg.hcbanner=(a,el)=>{S.hcBanner=!!el.checked;SX.save();banner();nativeCard();toast(S.hcBanner?P('Health card pinned on every screen'):P('Health card banner off'))};
SX.extend('mid',{before(){if(!phone())return '';return `<div class="card lv17-hcset"><div class="grow"><h3>${P('Health card banner')}</h3><p>${P('Blood group, allergies and SOS pinned under the top bar on every screen. It stays until you switch it off here.')}</p></div><label class="lv17-sw"><input type="checkbox" data-sxc="hcbanner" ${S.hcBanner!==false?'checked':''}><span></span></label></div>`}});

// ---------------------------------------------------------------- D. Today keeps the greeting (the bar does not repeat it)
function greet(){if(!phone()||page!=='dash')return;const pg=document.getElementById('page');if(!pg||document.getElementById('lv17greet'))return;const h=new Date().getHours();const g=h<12?P('Good morning'):h<17?P('Good afternoon'):P('Good evening');const m=SX.me();const el=document.createElement('div');el.id='lv17greet';el.innerHTML=`${g} · ${new Date().toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'})}<b>${E((m?m.name:'').split(' ')[0])}</b>`;pg.insertBefore(el,pg.firstChild)}

// ---------------------------------------------------------------- E. keyboard: the tab bar steps aside, the input stays visible
const vv=window.visualViewport;
if(vv){let base=vv.height;vv.addEventListener('resize',()=>{if(!phone())return;const kb=base-vv.height>120;document.body.classList.toggle('lv17-kb',kb);if(!kb)base=Math.max(base,vv.height);if(kb){const f=document.activeElement;if(f&&f.closest&&f.closest('.lv5-ask'))setTimeout(()=>f.scrollIntoView({block:'nearest'}),50)}})}
document.addEventListener('focusin',e=>{if(phone()&&e.target.matches('input,textarea,select'))document.body.classList.add('lv17-focus')});
document.addEventListener('focusout',()=>setTimeout(()=>{if(!document.activeElement||!document.activeElement.matches('input,textarea,select')){document.body.classList.remove('lv17-focus','lv17-kb')}},80));

// ---------------------------------------------------------------- F. Heart Lab labels on demand (phones)
function hlBtn(){if(!phone())return;const st=document.getElementById('hstage');if(!st||document.getElementById('lv17lbl'))return;const b=document.createElement('button');b.id='lv17lbl';b.type='button';b.textContent=P('Labels');b.onclick=()=>document.body.classList.toggle('lv17-labels');st.appendChild(b)}

// ---------------------------------------------------------------- G. the Android app: the Health Card as a notification that stays until switched off
async function nativeCard(){try{const C=window.Capacitor;if(!C||!C.isNativePlatform||!C.isNativePlatform())return;const HC=C.Plugins&&C.Plugins.HealthCard;
 if(HC){const m=SX.me();const d=SX.midOf(m.id);if(S.hcBanner===false||S.demo){await HC.hide();return}await HC.show({name:m.name,memberId:m.id,blood:d.blood||'',allergies:(d.allergies||[]).filter(Boolean).join(', '),conditions:(d.conditions||[]).filter(Boolean).join(', ')});return}
 const LN=C.Plugins&&C.Plugins.LocalNotifications;if(!LN)return;
 if(S.hcBanner===false||S.demo){await LN.cancel({notifications:[{id:7001}]});return}
 const perm=await LN.checkPermissions();if(perm.display!=='granted'){const r=await LN.requestPermissions();if(r.display!=='granted')return}
 const m=SX.me();const d=SX.midOf(m.id);const al=(d.allergies||[]).filter(Boolean);
 try{await LN.registerActionTypes({types:[{id:'hc',actions:[{id:'sos',title:'SOS',destructive:true},{id:'open',title:P('Medical ID')}]}]})}catch(e){}
 await LN.schedule({notifications:[{id:7001,title:`${d.blood?d.blood+' · ':''}${m.name}`,body:(al.length?P('Allergic')+': '+al.join(', '):P('No allergies on record'))+(d.conditions&&d.conditions.length?' · '+d.conditions.join(', '):''),ongoing:true,autoCancel:false,actionTypeId:'hc',iconColor:'#E11D48',extra:{kind:'hc'}}]});
 if(!window.__lv17ln){window.__lv17ln=1;LN.addListener('localNotificationActionPerformed',ev=>{if(ev.actionId==='sos')SX.openSOS();else go('mid')})}}catch(e){}}

// lock-screen card taps arrive as urbanhealth://sos or urbanhealth://medical-id
try{const C=window.Capacitor,AP=C&&C.Plugins&&C.Plugins.App;if(AP&&AP.addListener)AP.addListener('appUrlOpen',ev=>{const u=String(ev&&ev.url||'');if(u.startsWith('urbanhealth://sos'))setTimeout(()=>SX.openSOS(),300);else if(u.startsWith('urbanhealth://medical-id'))setTimeout(()=>go('mid'),300)})}catch(e){}
// ---------------------------------------------------------------- wiring
function refresh(){title();tabs();banner();greet()}
new MutationObserver(()=>setTimeout(refresh,0)).observe(document.body,{attributes:true,attributeFilter:['data-page']});
new MutationObserver(()=>{if(phone()){const strip=document.querySelector('#page>.sx-tabs');if(strip)tabs();greet()}}).observe(document.getElementById('page'),{childList:true});
const save17=SX.save;SX.save=function(){const r=save17.apply(this,arguments);clearTimeout(window.__lv17t);window.__lv17t=setTimeout(()=>{banner()},120);return r};
addEventListener('resize',()=>{refresh()});
setTimeout(()=>{refresh();hlBtn();nativeCard()},400);
setInterval(measure,3000);
}
