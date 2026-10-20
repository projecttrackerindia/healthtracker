// ===================== live layer 22: the phone design system — theme, icons, app bar, tab bar, Home, quick add, assistant hero =====================
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;
const ls=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){return null}};

// ---------------------------------------------------------------- A. theme: light unless the person chose dark; the choice sticks
{const r=document.documentElement,saved=ls('tht.theme');r.dataset.theme=saved==='dark'?'dark':'light';
 new MutationObserver(()=>{const t=r.dataset.theme;if(t==='dark'||t==='light')ls('tht.theme',t);else{r.dataset.theme='light';ls('tht.theme','light')}}).observe(r,{attributes:true,attributeFilter:['data-theme']})}

// ---------------------------------------------------------------- B. one icon set (24-unit stroke icons)
const I={
 home:'<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
 records:'<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>',
 pill:'<rect x="3" y="8.5" width="18" height="7" rx="3.5" transform="rotate(-45 12 12)"/><path d="m8.5 8.5 7 7"/>',
 heart:'<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
 grid:'<rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 steps:'<path d="M9 4c-2 0-3 2-3 4.5S7.5 13 9 13s3-2 3-4.5S11 4 9 4z"/><path d="M8 14h3l-.5 6h-2z"/><path d="M15 8c1.6 0 2.5 1.6 2.5 3.5S16.5 15 15 15s-2.5-1.6-2.5-3.5S13.4 8 15 8z"/><path d="M14 16h2.5l-.3 4h-2z"/>',
 moon:'<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
 pulse:'<path d="M3 12h4l2-6 4 12 2-6h6"/>',
 bp:'<circle cx="12" cy="12" r="8"/><path d="M12 8v4l2.5 2"/>',
 drop:'<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
 scale:'<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 10h8M12 10v6"/>',
 upload:'<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 20h16"/>',
 calendar:'<rect x="4" y="5" width="16" height="15" rx="2.5"/><path d="M4 10h16M8 3v4M16 3v4"/>',
 id:'<rect x="3" y="5" width="18" height="14" rx="2.5"/><circle cx="8.5" cy="11" r="2"/><path d="M5.5 16c.6-1.6 1.7-2.4 3-2.4s2.4.8 3 2.4M14 10h4M14 14h4"/>',
 cross:'<path d="M10 4h4v6h6v4h-6v6h-4v-6H4v-4h6z"/>',
 cart:'<path d="M3 4h2l2.4 11h10.8L21 7H6"/><circle cx="9" cy="19" r="1.4"/><circle cx="17" cy="19" r="1.4"/>',
 users:'<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/><circle cx="17" cy="9" r="2.5"/><path d="M15.5 14c2.7 0 5 1.8 5 4.5"/>',
 phone:'<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18h2"/>',
 watch:'<rect x="7" y="7" width="10" height="10" rx="3"/><path d="M9 7l.6-4h4.8L15 7M9 17l.6 4h4.8l.6-4"/>',
 bluetooth:'<path d="M7 7l10 10-5 4V3l5 4L7 17"/>',
 ecg:'<path d="M3 12h3l2-5 3 10 3-8 2 3h5"/>',
 ring:'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3.5"/>',
 bell:'<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
 chevron:'<path d="m9 6 6 6-6 6"/>',
 sparkle:'<path d="M12 3l2 5.5L19.5 10 14 12l-2 5.5L10 12 4.5 10 10 8.5z"/>',
 mic:'<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4"/>',
 message:'<path d="M4 6h16v10H9l-5 4z"/>',
 shield:'<path d="M12 3l8 3v6c0 4.5-3.4 7.8-8 9-4.6-1.2-8-4.5-8-9V6z"/>',
 pin:'<path d="M12 21s-6-5.5-6-10a6 6 0 0 1 12 0c0 4.5-6 10-6 10z"/><circle cx="12" cy="11" r="2"/>',
 lab:'<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3"/>',
 user:'<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/>'
};
SX.ico=(n,cls)=>`<svg class="${cls||''}" viewBox="0 0 24 24" aria-hidden="true">${I[n]||I.sparkle}</svg>`;
const EMOJI={'⬆':'upload','💊':'pill','📅':'calendar','🪪':'id','🩹':'cross','🫀':'heart','📱':'phone','⌚':'watch','🩺':'bluetooth','💓':'ecg','💍':'ring','📄':'records','📍':'pin','🧪':'lab','👤':'user','🛡️':'shield'};
function swapEmoji(root){if(!phone())return;(root||document).querySelectorAll('.sx-qa button i, .lv11-ic').forEach(el=>{const k=EMOJI[el.textContent.trim()];if(k&&!el.querySelector('svg'))el.innerHTML=SX.ico(k)})}

// ---------------------------------------------------------------- C. tab bar: our icons, labels on
const TAB={Home:'home',Records:'records',Medicines:'pill',Care:'heart',More:'grid'};
function tabbar(){if(!phone())return;document.querySelectorAll('#mtab button').forEach(b=>{const t=(b.querySelector('span')||{}).textContent||'';const k=TAB[t.trim()];if(k&&!b.dataset.lv22){b.dataset.lv22=k;if(t.trim()==='Medicines')b.querySelector('span').textContent=P('Meds');const svg=b.querySelector('svg');const n=document.createElement('span');n.innerHTML=SX.ico(k);if(svg)svg.replaceWith(n.firstChild);else b.prepend(n.firstChild)}})}

// ---------------------------------------------------------------- D. Home: greeting, family strip, stat tiles, week strip
const day=n=>{const d=new Date();d.setDate(d.getDate()-n);return d.toISOString().slice(0,10)};
const latest=(m,k)=>{const V=S.vitals[m.id]||[];for(let i=V.length-1;i>=0;i--)if(V[i][k]!=null)return V[i];return null};
const ago=t=>{const h=Math.round((Date.now()-t)/36e5);return h<1?P('just now'):h<24?h+' '+P('h ago'):Math.round(h/24)+' '+P('d ago')};
function tiles(m){const st=(S.steps[m.id]||{})[day(0)],sl=(S.sleep[m.id]||{})[day(0)]||(S.sleep[m.id]||{})[day(1)],hr=latest(m,'hr'),bp=latest(m,'sys'),goal=10000;
 const T=[];
 T.push(`<button class="lv22-tile hi" data-sx="tab:lab"><div class="t"><span>${P('Steps today')}</span><span class="lv22-tile-i">${SX.ico('steps')}</span></div><b>${st!=null?st.toLocaleString('en-IN'):'—'}<small>${st!=null?Math.round(st/goal*100)+'% '+P('of goal'):''}</small></b><em>${st!=null?P('from your phone or watch'):P('connect a watch or the app')}</em></button>`);
 T.push(`<button class="lv22-tile" data-sx="tab:lab"><div class="t"><span>${P('Sleep')}</span><span class="lv22-tile-i">${SX.ico('moon')}</span></div><b>${sl!=null?sl:'—'}<small>${sl!=null?P('hours'):''}</small></b><em>${sl!=null?P('last night'):P('no sleep data yet')}</em></button>`);
 T.push(`<button class="lv22-tile" data-sx="vlog"><div class="t"><span>${P('Heart rate')}</span><span class="lv22-tile-i">${SX.ico('pulse')}</span></div><b>${hr?hr.hr:'—'}<small>${hr?'bpm':''}</small></b><em class="${hr&&(hr.hr>100||hr.hr<50)?'warn':''}">${hr?ago(hr.t):P('tap to add')}</em></button>`);
 T.push(`<button class="lv22-tile" data-sx="vlog"><div class="t"><span>${P('Blood pressure')}</span><span class="lv22-tile-i">${SX.ico('bp')}</span></div><b>${bp?bp.sys+'/'+bp.dia:'—'}<small>${bp?'mmHg':''}</small></b><em class="${bp&&(bp.sys>=140||bp.dia>=90)?'bad':bp&&bp.sys>=130?'warn':''}">${bp?(bp.sys>=140||bp.dia>=90?P('high · discuss with your doctor'):bp.sys>=130?P('slightly raised'):P('normal')):P('tap to add')}</em></button>`);
 return `<div class="lv22-tiles">${T.join('')}</div>`}
function week(m){const V=S.vitals[m.id]||[],st=S.steps[m.id]||{},names=['S','M','T','W','T','F','S'];let n=0;const cells=[];
 for(let i=6;i>=0;i--){const d=day(i),dt=new Date(d+'T12:00:00');const on=!!(st[d]||V.some(v=>new Date(v.t).toISOString().slice(0,10)===d));if(on)n++;cells.push(`<i class="${on?'on':''} ${i===0?'today':''}"><b>${on?'✓':''}</b>${names[dt.getDay()]}</i>`)}
 return `<div class="lv22-week"><div class="l">${P('This week')}<small>${n?n+' '+P('of 7 days with readings'):P('no readings yet this week')}</small></div><div class="lv22-days">${cells.join('')}</div></div>`}
function family(){const ms=S.members||[];if(ms.length<2&&!SX.user)return '';return `<div class="lv22-fam">${ms.map(m=>`<button class="${m.id===S.active?'on':''}" data-sx="who:${E(m.id)}">${SX.avatar(m,54)}<span>${E(m.rel==='You'?P('You'):m.name.split(' ')[0])}</span></button>`).join('')}<button class="add" data-sx="tab:family"><div class="av">+</div><span>${P('Add')}</span></button></div>`}
SX.extend('dash',{before(){if(!phone())return '';const m=SX.me();const h=new Date().getHours(),g=h<12?P('Good morning'):h<17?P('Good afternoon'):P('Good evening');
 return `<div class="lv22-top"><div class="lv22-hello"><div><small>${g},</small><b>${E(m.name.split(' ')[0])}</b></div><span class="lv22-date">${new Date().toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'})}</span></div>${family()}${tiles(m)}${week(m)}</div>`}});
// name the Home cards that have no class, so the stylesheet can order them
function tagCards(){if(!phone()||page!=='dash')return;document.querySelectorAll('#page>.card:not([data-lv22])').forEach(c=>{const h=c.querySelector('h3');const t=h?h.textContent.trim():'';const k=/^Medicines today/.test(t)?'meds':/^Next visit/.test(t)?'visit':/^Vitals/.test(t)?'vitals':/^Safety setup/.test(t)?'safety':/^Worth a conversation/.test(t)?'talk':/^Quick actions/.test(t)?'quick':'';if(k)c.dataset.lv22=k})}

// ---------------------------------------------------------------- E. quick add
function fab(){if(!phone())return;let b=document.getElementById('lv22add');if(!b){b=document.createElement('button');b.id='lv22add';b.setAttribute('aria-label',P('Add'));b.innerHTML=SX.ico('plus');b.onclick=quick;document.body.appendChild(b)}}
function quick(){const m=SX.me();SX.modal(`<h2>${P('Add')}</h2><p class="mute sm" style="margin:0">${P('For')} ${E(m.name.split(' ')[0])}</p><div class="lv22-qa">
 <button data-sx="vlog"><i>${SX.ico('pulse')}</i>${P('Reading')}</button><button data-sx="tab:vault"><i>${SX.ico('upload')}</i>${P('Report')}</button><button data-sx="medadd"><i>${SX.ico('pill')}</i>${P('Medicine')}</button>
 <button data-sx="tab:appts"><i>${SX.ico('calendar')}</i>${P('Visit')}</button><button data-sx="tab:family"><i>${SX.ico('users')}</i>${P('Family member')}</button><button data-sx="tab:assist"><i>${SX.ico('sparkle')}</i>${P('Ask the assistant')}</button></div>`,{label:P('Add')});
 document.querySelectorAll('.lv22-qa button').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>{if(/^tab:/.test(b.dataset.sx))SX.closeModal()},0)))}

// ---------------------------------------------------------------- F. assistant hero in every state
function orb(){if(!phone()||page!=='assist')return;const ag=document.querySelector('.lv5-agent');if(!ag||ag.querySelector('.lv22-orbwrap'))return;const m=SX.me();const el=document.createElement('div');el.className='lv22-orbwrap';el.innerHTML=`<div class="lv22-orb"></div><small>${P('Hello')} ${E(m.name.split(' ')[0])}</small><b>${P('How can I help you today?')}</b>`;ag.prepend(el)}

// ---------------------------------------------------------------- wiring
function refresh(){tabbar();fab();tagCards();swapEmoji();orb()}
new MutationObserver(()=>setTimeout(refresh,0)).observe(document.getElementById('page'),{childList:true});
new MutationObserver(()=>setTimeout(refresh,0)).observe(document.body,{attributes:true,attributeFilter:['data-page']});
setTimeout(refresh,300);
SX.lv22={ico:SX.ico,tiles,week};
}
