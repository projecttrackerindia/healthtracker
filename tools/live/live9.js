// ===================== live layer 9: pregnancy tabs complete, care plan out of pregnancy, pregnancy page tidy =====================
{
const P=SX.p;
const PP9=['pkick','pctr','pwater','psymp','pfood','pweek','pmusic','pwell','pben','pbirth'];window.__pregPages=new Set(PP9);
SX.addStrings({'tab.pweek':SX.D('Week','सप्ताह','వారం'),'tab.pmusic':SX.D('Music','संगीत','సంగీతం'),'tab.pwell':SX.D('Wellbeing','सेहत','శ్రేయస్సు'),'tab.pben':SX.D('Benefits','लाभ','ప్రయోజనాలు')});
{const care=SX.G.find(g=>g.k==='care');const fix=()=>{if(!care)return;const preg=SX.pregOn(SX.me());care.tabs=preg?['preg',...PP9,'careplan','child']:['careplan','cycle','child']};fix();const pn4=SX.pregNav;SX.pregNav=()=>{pn4();fix()}}
// the care plan is not part of a pregnancy; pregnancy is the care
const tv9=SX.tabVisible;SX.tabVisible=k=>{if(k==='careplan'&&SX.pregOn(SX.me()))return false;return tv9(k)};
SX.extend('careplan',{mounted(){if(SX.pregOn(SX.me()))go('preg')}});
const PG9=()=>window.__preg||null;
const week9=()=>{const g=PG9();if(!g)return 0;try{g.PS.week=Math.max(0,Math.min(42,g.ga().w))}catch(e){}return g.PS.week||0};
const gate9=()=>{const m=SX.me();if(!SX.pregOn(m))return `<div class="card wide"><p class="mute" style="margin:0">${P('Pregnancy mode is off for this profile.')}</p></div>`;if(!PG9())return `<div class="card wide"><p class="mute" style="margin:0">${P('Loading…')}</p></div>`;return ''};
const head9=(ic,t,s)=>`<div class="lv8-ph"><div class="lv8-phi">${ic}</div><div><h3>${E(t)}</h3><p class="mute sm">${E(s)}</p></div><span class="lv8-wk">${P('Week')} ${week9()}</span></div>`;
const wrap9=(key,ic,t,s)=>({head:()=>[P(t),P(s)],render(){const g0=gate9();if(g0)return g0;const g=PG9();week9();let html='';try{html=g.T[key]?g.T[key]():''}catch(e){html=`<p class="mute">${E(e.message)}</p>`}return `<div class="card wide lv8-pwrap lv8-${key}">${head9(ic,P(t),P(s))}<div class="lv8-pin">${html}</div></div>`},after(){const g=PG9();try{if(g&&g.AT[key])g.AT[key]()}catch(e){}}});
SX.reg('pweek',wrap9('week','🗓️','This week','Baby and mother this week: size, changes, what is due.'));
SX.reg('pmusic',wrap9('music','🎵','Music','Gentle sound for you and the baby; what the baby can hear now.'));
SX.reg('pwell',wrap9('well','🧘','Wellbeing','Sleep, movement, mood and rest for this trimester.'));
SX.reg('pben',wrap9('ben','🎁','Benefits','Maternity benefits and schemes you may be entitled to.'));
// the Pregnancy page: journey + 3D lab only (trackers and guides are tabs)
SX.pregTrackers=()=>'';

// counting kicks must feel instant: update the ring and number in place, no page re-render per tap
document.addEventListener('click',e=>{const b=e.target.closest('.lv8-tap');if(!b||b.dataset.pa!=='kick')return;const g=PG9();if(!g||!g.PS.kick)return;e.preventDefault();e.stopPropagation();const K=g.PS.kick;K.n++;if(navigator.vibrate)try{navigator.vibrate(30)}catch(x){}
 const num=b.querySelector('b'),sm=b.querySelector('small'),ring=b.closest('.lv8-ring');if(num)num.textContent=K.n;if(ring)ring.style.setProperty('--p',Math.min(100,K.n*10));
 if(K.n>=10){if(sm)sm.textContent=P('Done!');const save=document.querySelector('[data-pa=kickEnd]');if(save)save.textContent='✓ '+P('Save session');if(!document.querySelector('.lv8-ok')){const card=document.querySelector('.lv8-kick');if(card)card.insertAdjacentHTML('beforeend',`<p class="lv8-ok">✅ ${P('10 movements in')} ${Math.floor((Date.now()-K.s)/60000)}:${String(Math.round((Date.now()-K.s)/1000)%60).padStart(2,'0')} — ${P('that is reassuring. Save the session.')}</p>`)}}},true);
}
