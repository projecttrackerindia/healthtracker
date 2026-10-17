// ===================== DoKKo six-sidebar layer · core =====================
// Store, six-item navigation with sub-tabs, family switcher, SOS button, emergency-word guard,
// modal/menu helpers, body drawer and en/hi/te chrome strings. Feature pages live in the other six/*.js files.
(()=>{
'use strict';
const SX=window.SX={act:{},chg:{},last:{},heads:{},badge:{},seeds:[],pageOf:{}};
const E=esc;
SX.E=E;

// ---------------------------------------------------------------- strings (chrome only; clinical text stays English)
const D=(en,hi,te)=>({en,hi,te});
const T={
 'nav.home':D('Home','होम','హోమ్'),'nav.records':D('Records & Labs','रिकॉर्ड और जाँच','రికార్డులు & ల్యాబ్‌లు'),'nav.meds':D('Medicines','दवाइयाँ','మందులు'),
 'nav.s.home':D('Home','होम','హోమ్'),'nav.s.records':D('Records','रिकॉर्ड','రికార్డులు'),'nav.s.meds':D('Medicines','दवाइयाँ','మందులు'),'nav.s.care':D('Care','देखभाल','సంరక్షణ'),'nav.s.safety':D('Safety','सुरक्षा','భద్రత'),'nav.s.family':D('Family','परिवार','కుటుంబం'),
 'nav.care':D('Care','देखभाल','సంరక్షణ'),'nav.safety':D('Safety','सुरक्षा','భద్రత'),'nav.family':D('Family & Privacy','परिवार और गोपनीयता','కుటుంబం & గోప్యత'),
 'tab.dash':D('Today','आज','ఈ రోజు'),'tab.lab':D('Body','शरीर','శరీరం'),'tab.heart':D('Heart Lab','हृदय लैब','గుండె ల్యాబ్'),
 'tab.vault':D('Vault','दस्तावेज़','పత్రాలు'),'tab.tests':D('Lab results','जाँच परिणाम','ల్యాబ్ ఫలితాలు'),'tab.insights':D('Insights','जानकारी','విశ్లేషణ'),
 'tab.rx':D('My medicines','मेरी दवाइयाँ','నా మందులు'),'tab.finder':D('Find & order','खोजें और मँगाएँ','వెతకండి & ఆర్డర్'),'tab.orders':D('Orders','ऑर्डर','ఆర్డర్లు'),
 'tab.appts':D('Appointments','अपॉइंटमेंट','అపాయింట్‌మెంట్లు'),'tab.docs':D('Doctors','डॉक्टर','డాక్టర్లు'),'tab.msgs':D('Messages','संदेश','సందేశాలు'),
 'tab.preg':D('Pregnancy','गर्भावस्था','గర్భధారణ'),'tab.bill':D('Bills','बिल','బిల్లులు'),
 'tab.sos':D('SOS','SOS','SOS'),'tab.aid':D('First aid','प्राथमिक उपचार','ప్రథమ చికిత్స'),'tab.mid':D('Medical ID','मेडिकल आईडी','మెడికల్ ఐడి'),'tab.contacts':D('Contacts','संपर्क','కాంటాక్ట్‌లు'),
 'tab.family':D('Family','परिवार','కుటుంబం'),'tab.consent':D('Consent','सहमति','సమ్మతి'),'tab.data':D('My data','मेरा डेटा','నా డేటా'),'tab.set':D('Settings','सेटिंग्स','సెట్టింగ్‌లు'),
 'sos':D('SOS','SOS','SOS'),'emergency':D('Emergency','आपातकाल','అత్యవసరం'),
 'call112':D('Call 112','112 पर कॉल करें','112కి కాల్ చేయండి'),'call108':D('Ambulance 108','एम्बुलेंस 108','అంబులెన్స్ 108'),
 'openSOS':D('Open SOS','SOS खोलें','SOS తెరవండి'),'dismiss':D('Dismiss','बंद करें','మూసివేయండి'),'firstaid':D('First aid','प्राथमिक उपचार','ప్రథమ చికిత్స'),
 'emg.title':D('This could be an emergency.','यह आपातकाल हो सकता है।','ఇది అత్యవసర పరిస్థితి కావచ్చు.'),
 'emg.body':D('If someone is in danger, call 112 now. Do not wait for the app.','अगर किसी की जान खतरे में है, तो अभी 112 पर कॉल करें। ऐप का इंतज़ार न करें।','ఎవరికైనా ప్రమాదం ఉంటే, వెంటనే 112కి కాల్ చేయండి. యాప్ కోసం ఆగకండి.'),
 'emg.mind':D('You are not alone. Talk to someone now: Tele-MANAS 14416 (free, 24×7). If you are in immediate danger, call 112.','आप अकेले नहीं हैं। अभी किसी से बात करें: टेली-मानस 14416 (निःशुल्क, 24×7)। तुरंत खतरा हो तो 112 पर कॉल करें।','మీరు ఒంటరివారు కాదు. ఇప్పుడే మాట్లాడండి: టెలి-మానస్ 14416 (ఉచితం, 24×7). తక్షణ ప్రమాదం ఉంటే 112కి కాల్ చేయండి.'),
 'emg.preg':D('Bleeding, severe pain, leaking fluid or less baby movement in pregnancy needs a doctor or hospital now. Call 112 if it is severe.','गर्भावस्था में रक्तस्राव, तेज़ दर्द, पानी रिसना या बच्चे की हलचल कम होने पर तुरंत डॉक्टर या अस्पताल जाएँ। गंभीर हो तो 112 पर कॉल करें।','గర్భధారణలో రక్తస్రావం, తీవ్రమైన నొప్పి, నీరు కారడం లేదా శిశు కదలికలు తగ్గితే వెంటనే డాక్టర్/ఆసుపత్రికి వెళ్లండి. తీవ్రంగా ఉంటే 112కి కాల్ చేయండి.'),
 'sos.title':D('Emergency help','आपातकालीन मदद','అత్యవసర సహాయం'),
 'sos.sub':D('Call first. Alert your contacts next.','पहले कॉल करें, फिर संपर्कों को बताएँ।','ముందు కాల్ చేయండి, తర్వాత కాంటాక్ట్‌లకు తెలియజేయండి.'),
 'sos.hold':D('Hold to alert my contacts','संपर्कों को सूचित करने के लिए दबाए रखें','నా కాంటాక్ట్‌లకు తెలియజేయడానికి నొక్కి ఉంచండి'),
 'who':D('Switch person','व्यक्ति बदलें','వ్యక్తిని మార్చండి'),'manage':D('Manage family','परिवार प्रबंधित करें','కుటుంబాన్ని నిర్వహించండి'),
 'lang':D('Language','भाषा','భాష'),'close':D('Close','बंद करें','మూసివేయండి')
};
SX.t=k=>{const o=T[k];return o?(o[S.lang]||o.en):k};
SX.addStrings=o=>Object.assign(T,o);SX.D=D;
const PH={};SX.addPhrases=o=>Object.assign(PH,o);SX.p=en=>{const o=PH[en];return o?((S.lang==='hi'?o[0]:S.lang==='te'?o[1]:en)||en):en};

// ---------------------------------------------------------------- store
const LSK='dk6',uid=p=>p+Math.random().toString(36).slice(2,9);
SX.uid=uid;
const demo=()=>({v:1,lang:'en',active:'m1',created:Date.now(),
 members:[
  {id:'m1',pid:'p1',name:'Prasanna',rel:'You',age:34,sex:'male',w:72,h:175,av:'PR',c:'m',shared:true},
  {id:'m2',pid:'p3',name:'Ananya',rel:'Spouse',age:29,sex:'female',w:60,h:162,av:'AN',c:'',shared:true},
  {id:'m3',pid:'p2',name:'Ramesh',rel:'Father',age:61,sex:'male',w:78,h:170,av:'RA',c:'y',shared:true},
  {id:'m4',pid:'p4',name:'Lakshmi',rel:'Mother',age:58,sex:'female',w:68,h:158,av:'LA',c:'g',shared:true},
  {id:'m5',pid:'p5',name:'Arjun',rel:'Brother',age:24,sex:'male',w:70,h:178,av:'AR',c:'m',shared:true}]});
let S;
try{const j=JSON.parse(localStorage.getItem(LSK));if(j&&j.v===1&&Array.isArray(j.members)&&j.members.length)S=j}catch(e){}
if(!S)S=demo();
SX.S=S;
let svT=0;
SX.save=(now)=>{if(SX.wiped)return;clearTimeout(svT);const go_=()=>{try{localStorage.setItem(LSK,JSON.stringify(S))}catch(e){if(!SX._warned){SX._warned=1;toast('This browser would not save your changes (storage full or blocked).')}}};now?go_():svT=setTimeout(go_,150)};
addEventListener('pagehide',()=>SX.save(true));
SX.init=f=>{SX.seeds.push(f)};      // modules register default data
SX.runSeeds=()=>{SX.seeds.forEach(f=>{try{f(S)}catch(e){console.warn('seed',e)}});SX.save()};

// Family display names for the demo patients (same fictional people, shown as one household)
{const N={p1:['Prasanna',34],p2:['Ramesh',61],p3:['Ananya',29],p4:['Lakshmi',58],p5:['Arjun',24]};PATS.forEach(p=>{const n=N[p.id];if(n){p.n=n[0];p.age=n[1];p.av=n[0].slice(0,2).toUpperCase()}})}

// ---------------------------------------------------------------- members
SX.me=()=>S.members.find(m=>m.id===S.active)||S.members[0];
SX.member=id=>S.members.find(m=>m.id===id);
SX.bmi=m=>m&&m.w&&m.h?m.w/((m.h/100)**2):null;
SX.bmiCat=b=>b==null?'':b<18.5?'Below the healthy range':b<23?'Healthy range':b<27.5?'Above the healthy range':'Well above the healthy range';   // Asia-Pacific cut-offs
SX.viewable=m=>!!m&&(m.rel==='You'||m.shared!==false);
SX.pat=m=>m&&m.pid?PATS.find(p=>p.id===m.pid):null;
SX.canPreg=m=>!!m&&m.sex==='female'&&m.age>=14&&m.age<=55;
SX.pregOn=m=>!!(m&&S.preg&&S.preg[m.id]&&S.preg[m.id].on);
SX.avatar=(m,s=40)=>`<div class="av ${E(m.c||'')}" style="width:${s}px;height:${s}px;font-size:${Math.round(s/3.1)}px" aria-hidden="true">${E((m.av||m.name.slice(0,2)).toUpperCase())}</div>`;
SX.fmt=ts=>new Date(ts).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
SX.fmtT=ts=>new Date(ts).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'});
SX.today=()=>{const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')};

// ---------------------------------------------------------------- groups & pages
SX.G=[
 {k:'home',ic:'dash',tabs:['dash','lab','heart']},
 {k:'records',ic:'test',tabs:['vault','tests','insights']},
 {k:'meds',ic:'rx',tabs:['rx','finder','orders']},
 {k:'care',ic:'doc',tabs:['appts','docs','msgs','preg','bill']},
 {k:'safety',ic:'shield',tabs:['sos','aid','mid','contacts']},
 {k:'family',ic:'pat',tabs:['family','consent','data','set']}];
I.shield='<path d="M12 3l7.5 2.8v5.6c0 4.4-3 8.2-7.5 9.6-4.5-1.4-7.5-5.2-7.5-9.6V5.8z"/><path d="M12 8.2v4.6M12 15.8h.01"/>';
const grpOf=p=>{const g=SX.G.find(g=>g.tabs.includes(p));return g?g.k:(p==='pregopt'?'care':p==='patients'?'family':'home')};
SX.grpOf=grpOf;
SX.tabVisible=k=>{if(k==='preg'){const m=SX.me();return SX.canPreg(m)||SX.pregOn(m)}return true};
// page registration: SX.reg('vault',{head:()=>[title,sub],render:()=>html,after:()=>{}})
SX.reg=(k,o)=>{if(o.render)PAGES[k]=o.render;if(o.after)AFTER[k]=o.after;if(o.head){SX.heads[k]=o.head;Object.defineProperty(HEAD,k,{get:o.head,configurable:true,enumerable:true})}};
SX.headOf=(k,title,sub)=>{SX.heads[k]=()=>[title(),sub()];Object.defineProperty(HEAD,k,{get:SX.heads[k],configurable:true,enumerable:true})};

// ---------------------------------------------------------------- navigation
function buildNav(){const nav=$('#nav');nav.querySelectorAll('button').forEach(b=>b.remove());
 SX.G.forEach(g=>{const b=document.createElement('button');b.dataset.p=g.tabs[0];b.dataset.g=g.k;b.setAttribute('aria-label',SX.t('nav.'+g.k));b.innerHTML=ic(g.ic)+`<span class="sx-nl">${E(SX.t('nav.'+g.k))}</span><span class="sx-ns">${E(SX.t('nav.s.'+g.k))}</span><em hidden></em>`;b.onclick=()=>go(SX.last[g.k]||g.tabs[0]);nav.append(b)});
 const old=$('.consult')||$('.sx-sidesos');if(old){old.className='sx-sidesos';old.innerHTML=`<b>${E(SX.t('emergency'))}</b><button class="sx-sosbtn" data-sx="sos" aria-label="${E(SX.t('openSOS'))}"><i></i>SOS</button><div class="sx-sidecall"><a href="tel:112">112</a><a href="tel:108">108</a></div>`}
}
function paintNav(){$$('#nav [data-g]').forEach(b=>{const k=b.dataset.g;b.querySelector('.sx-nl').textContent=SX.t('nav.'+k);b.querySelector('.sx-ns').textContent=SX.t('nav.s.'+k);b.setAttribute('aria-label',SX.t('nav.'+k));const f=SX.badge[k],n=f?f():0,em=b.querySelector('em');em.hidden=!n;em.textContent=n||''})}
SX.paintNav=paintNav;
SX.paintGates=()=>{document.body.dataset.preg=SX.pregOn(SX.me())?'on':'off'};

const _go=go;
go=function(p,opt){
 if(p==='preg'&&!SX.pregOn(SX.me()))p='pregopt';
 SX.bodyDrawer(false);SX.closeMenu();
 const g=grpOf(p);SX.last[g]=p==='pregopt'?'preg':p;
 const gb=$('#nav [data-g="'+g+'"]');if(gb)gb.dataset.p=p;
 const r=_go.call(this,p,opt||{});
 if((p==='dash'||p==='lab')&&SX.pendingModel)SX.applyModel();
 document.body.dataset.pg=p;SX.paintGates();paintNav();return r};

const MEMBER_PAGES=new Set(['dash','lab','vault','tests','insights','rx','finder','orders','mid','preg','appts']);
const _render=render;
render=function(...a){
 const m=SX.me(),g=SX.G.find(x=>x.k===grpOf(page));
 if(!SX.viewable(m)&&MEMBER_PAGES.has(page)&&page!=='lab'){
  $('#page').innerHTML=tabsHTML(g)+`<div class="card sx-lock"><div class="sx-lockic">🔒</div><h3>${E(m.name)} has not shared records with you</h3><p class="mute">Medical records are private by default. ${E(m.name)} can allow family access in Family &amp; Privacy → Consent. Emergency details stay available in the Safety section.</p><button class="btn p" data-sx="tab:consent">Open consent settings</button></div>`;paintNav();return}
 const r=_render.apply(this,a);
 const pg=$('#page');if(g)pg.insertAdjacentHTML('afterbegin',tabsHTML(g));
 paintNav();SX.paintWho();return r};
function tabsHTML(g){const cur=page==='pregopt'?'preg':page;
 return `<div class="sx-tabs wide" role="tablist" aria-label="${E(SX.t('nav.'+g.k))}">${g.tabs.filter(SX.tabVisible).map(k=>`<button role="tab" aria-selected="${k===cur}" class="${k===cur?'on':''}" data-sx="tab:${k}">${E(SX.t('tab.'+k))}</button>`).join('')}</div>`}
SX.act.tab=([k])=>go(k);

// ---------------------------------------------------------------- header: person switcher + language
function buildTop(){const tb=$('.topb');if(!tb)return;const pill=tb.querySelector('.pill');if(pill)pill.remove();
 const who=document.createElement('button');who.id='sxWho';who.className='sx-who';who.setAttribute('aria-haspopup','menu');who.setAttribute('aria-label',SX.t('who'));
 const lang=document.createElement('button');lang.id='sxLang';lang.className='sx-lang';lang.setAttribute('aria-haspopup','menu');lang.setAttribute('aria-label',SX.t('lang'));
 tb.prepend(lang);tb.prepend(who);who.onclick=()=>SX.menu(who,whoMenu());lang.onclick=()=>SX.menu(lang,langMenu())}
SX.paintWho=()=>{const w=$('#sxWho');if(!w)return;const m=SX.me();w.innerHTML=`${SX.avatar(m,30)}<span class="sx-wn"><b>${E(m.name)}</b><small>${E(m.rel)}</small></span><i aria-hidden="true">▾</i>`;
 const l=$('#sxLang');if(l){l.textContent={en:'EN',hi:'हि',te:'తె'}[S.lang];l.setAttribute('aria-label',SX.t('lang'))}};
function whoMenu(){return `<div class="sx-mh">${E(SX.t('who'))}</div>`+S.members.map(m=>`<button role="menuitem" class="sx-mi ${m.id===S.active?'on':''}" data-sx="who:${m.id}">${SX.avatar(m,32)}<span><b>${E(m.name)}</b><small>${E(m.rel)} · ${m.age} · ${m.sex==='female'?'♀':'♂'}${SX.viewable(m)?'':' · 🔒 private'}</small></span>${m.id===S.active?'<i>✓</i>':''}</button>`).join('')+`<button role="menuitem" class="sx-mi sx-mm" data-sx="tab:family">${E(SX.t('manage'))} →</button>`}
function langMenu(){return `<div class="sx-mh">${E(SX.t('lang'))}</div>`+[['en','English'],['hi','हिन्दी'],['te','తెలుగు']].map(([k,n])=>`<button role="menuitem" class="sx-mi ${k===S.lang?'on':''}" data-sx="lang:${k}"><span><b>${n}</b></span>${k===S.lang?'<i>✓</i>':''}</button>`).join('')+`<p class="sx-mnote">Menus, SOS and emergency alerts are translated. Medical guidance stays in English until a clinician has reviewed each translation.</p>`}
SX.act.who=([id])=>{SX.closeMenu();SX.setActive(id)};
SX.act.lang=([k])=>{SX.closeMenu();S.lang=k;document.documentElement.lang=k;SX.save();buildNav();go(page,{keep:true});SX.paintWho()};

SX.setActive=id=>{if(!SX.member(id)||id===S.active)return;S.active=id;SX.save();SX.pendingModel=true;
 if(typeof SX.syncPreg==='function')SX.syncPreg();
 if(page==='preg'||page==='pregopt'){const m=SX.me();go(SX.canPreg(m)||SX.pregOn(m)?'preg':'dash');SX.paintWho();return}
 if(page==='dash'||page==='lab')SX.applyModel();
 render();SX.paintWho();toast('Now showing '+SX.me().name)};
SX.applyModel=async()=>{const m=SX.me();SX.pendingModel=false;if(!A.ready)return;try{if(A.focus||A.patient)A.clearFocus();if(A.sex!==m.sex)await A.setSex(m.sex)}catch(e){console.warn(e)}if(page==='dash'||page==='lab')render()};

// ---------------------------------------------------------------- modal, popover menu
let modalEl=null,lastFocus=null,menuEl=null,menuAnchor=null;
SX.modal=(html,opt={})=>{SX.closeModal(true);lastFocus=document.activeElement;
 const w=document.createElement('div');w.className='sx-modal'+(opt.cls?' '+opt.cls:'');
 w.innerHTML=`<div class="sx-sheet" role="dialog" aria-modal="true" aria-label="${E(opt.label||'Dialog')}" tabindex="-1">${html}</div>`;
 w.addEventListener('pointerdown',e=>{if(e.target===w&&!opt.sticky)SX.closeModal()});
 document.body.append(w);document.body.classList.add('sx-mo');modalEl=w;w._onclose=opt.onclose;
 const f=w.querySelector('[autofocus]')||w.querySelector('.sx-sheet');setTimeout(()=>{try{f.focus({preventScroll:true})}catch(e){}},30);return w};
SX.closeModal=quiet=>{if(!modalEl)return;const w=modalEl;modalEl=null;document.body.classList.remove('sx-mo');try{w._onclose&&w._onclose()}catch(e){}w.remove();if(!quiet&&lastFocus&&lastFocus.focus)try{lastFocus.focus()}catch(e){}};
SX.act.closeModal=()=>SX.closeModal();
SX.menu=(anchor,html)=>{if(menuEl&&menuAnchor===anchor){SX.closeMenu();return}SX.closeMenu();const m=document.createElement('div');m.className='sx-menu';m.setAttribute('role','menu');m.innerHTML=html;document.body.append(m);
 const r=anchor.getBoundingClientRect(),w=m.offsetWidth;m.style.top=Math.round(r.bottom+8)+'px';m.style.left=Math.round(Math.min(innerWidth-w-10,Math.max(10,r.right-w)))+'px';menuEl=m;menuAnchor=anchor;anchor.setAttribute('aria-expanded','true')};
SX.closeMenu=()=>{if(!menuEl)return;menuEl.remove();if(menuAnchor)menuAnchor.removeAttribute('aria-expanded');menuEl=menuAnchor=null};
document.addEventListener('pointerdown',e=>{if(menuEl&&!menuEl.contains(e.target)&&!(menuAnchor&&menuAnchor.contains(e.target)))SX.closeMenu()});
addEventListener('keydown',e=>{if(e.key!=='Escape')return;if(modalEl){SX.closeModal();e.preventDefault();return}if(menuEl){SX.closeMenu();return}const b=$('#sxEmg');if(b&&!b.hidden){b.hidden=true;return}if($('#stage').classList.contains('sx-drawer'))SX.bodyDrawer(false)});

// ---------------------------------------------------------------- 3D body as a drawer on pages that have no stage
SX.bodyDrawer=on=>{const st=$('#stage');if(!st)return;
 if(on){if(!st.hidden)return;st.hidden=false;st.classList.add('sx-drawer');document.body.classList.add('sx-drawer-open');if(!$('#sxDrawerX')){const x=document.createElement('button');x.id='sxDrawerX';x.className='sx-dx';x.setAttribute('aria-label','Close body view');x.textContent='✕';x.onclick=()=>SX.bodyDrawer(false);st.append(x)}}
 else if(st.classList.contains('sx-drawer')){st.classList.remove('sx-drawer');document.body.classList.remove('sx-drawer-open');if(page!=='dash'&&page!=='lab')st.hidden=true}
 else return;
 dispatchEvent(new Event('resize'))};
// buttons such as “View on body” / “Target organ” work from any page: they open the body in a drawer
document.addEventListener('click',e=>{const b=e.target.closest('[data-act]');if(!b)return;const k=b.dataset.act.split(':')[0];
 if(['spec','test','finding','patient','cond'].includes(k)&&$('#stage').hidden&&page!=='preg'&&page!=='heart')setTimeout(()=>{if($('#stage').hidden)SX.bodyDrawer(true)},0)});

// ---------------------------------------------------------------- click / change delegation
document.addEventListener('click',e=>{const b=e.target.closest('[data-sx]');if(!b||b.disabled)return;const[k,...a]=b.dataset.sx.split(':');const f=SX.act[k];if(f)f(a,b,e)});
document.addEventListener('change',e=>{const b=e.target.closest('[data-sxc]');if(!b)return;const[k,...a]=b.dataset.sxc.split(':');const f=SX.chg[k];if(f)f(a,b,e)});
document.addEventListener('submit',e=>{const f=e.target.closest('[data-sxf]');if(!f)return;e.preventDefault();const[k,...a]=f.dataset.sxf.split(':');const h=SX.chg[k];if(h)h(a,f,e)});

// ---------------------------------------------------------------- emergency-word guard (never diagnoses; only points to help)
const EM=[
 ['cardiac','heart',/\bchest (pain|pains|pressure|tightness|tight)\b|\bheart attack\b|\bcardiac arrest\b|सीने (में )?(दर्द|जकड़न|भारीपन)|छाती (में )?दर्द|दिल का दौरा|हार्ट अटैक|ఛాతీ(లో)? నొప్పి|గుండెపోటు|గుండె నొప్పి/i],
 ['breath','cpr',/\b(can'?t|cannot|can not|unable to|struggling to|trouble|difficulty|hard to) (breathe|breathing)\b|\bnot breathing\b|\bshort(ness)? of breath\b|\bgasping\b|सांस (नहीं|लेने में (तकलीफ|दिक्कत|परेशानी))|साँस (नहीं|लेने में (तकलीफ|दिक्कत|परेशानी))|दम घुट|ఊపిరి (ఆడ|తీసుకోలేక|అందడం)|శ్వాస తీసుకోవడంలో/i],
 ['unconscious','cpr',/\b(unconscious|unresponsive|passed out|not responding|collapsed|won'?t wake up)\b|बेहोश|होश (नहीं|खो)|స్పృహ (తప్పి|కోల్పో)|అపస్మారక/i],
 ['bleeding','bleed',/\b(heavy|severe|profuse|uncontrolled) bleeding\b|\bbleeding (heavily|badly|a lot|won'?t stop)\b|\bblood (is )?(everywhere|won'?t stop)\b|(बहुत|ज्यादा|ज़्यादा) खून (बह|निकल)|खून (नहीं रुक|बंद नहीं)|(ఎక్కువ|తీవ్రమైన) రక్తస్రావం|రక్తం ఆగ/i],
 ['seizure','seizure',/\b(seizure|seizures|convulsion|convulsing|having a fit)\b|दौरा पड़|मिर्गी|झटके आ|మూర్ఛ|ఫిట్స్/i],
 ['stroke','stroke',/\bstroke\b|\bface (is )?droop\w*|\bslurred speech\b|\bsudden (weakness|numbness) (in|on) (one|my) (side|arm|leg|face)\b|लकवा|पक्षाघात|चेहरा टेढ़ा|పక్షవాతం/i],
 ['poison','poison',/\boverdos(e|ed|ing)\b|\bpoison(ed|ing)?\b|\bswallowed (a lot|too many|bleach|acid|kerosene|pesticide|poison)\b|जहर|ज़हर|ओवरडोज|విషం|ఓవర్ ?డోస్/i],
 ['allergy','allergy',/\banaphyla\w*|\bthroat (is )?(closing|swelling|swollen)\b|\bsevere allergic\b/i],
 ['snake','snake',/\bsnake ?bite\b|\bbitten by (a )?snake\b|सांप ने काट|साँप ने काट|పాము (కాటు|కరిచ)/i],
 ['choking','choking',/\b(choking|choked)\b|\bsomething stuck in (my |his |her |the )?(throat|windpipe)\b/i],
 ['drowning','drown',/\bdrown(ing|ed)\b/i],
 ['burn','burn',/\b(severe|bad|serious|major) burns?\b/i],
 ['mind','',/\bsuicid\w*|\bkill myself\b|\bend my life\b|\bwant to die\b|\bself[- ]?harm\b|\bhurt myself\b|\bno reason to live\b|आत्महत्या|मरना चाहता|मरना चाहती|ఆత్మహత్య|చనిపోవాలని/i],
 ['preg','preg',/\b(bleeding|pain|cramps?) (while|during|in) (my )?pregnan\w*|\bbaby (is )?(not|isn'?t|stopped) (moving|kicking)\b|\bwaters? (broke|breaking)\b|\bno (baby )?movement\b/i]];
SX.emergency=txt=>{if(!txt||txt.length<4)return null;const t=String(txt).slice(0,600);for(const[id,aid,re]of EM)if(re.test(t))return{id,aid};return null};
const mute={};
function showEmg(hit){const now=Date.now();if(mute[hit.id]>now)return;
 let b=$('#sxEmg');if(!b){b=document.createElement('div');b.id='sxEmg';b.className='sx-emg';b.setAttribute('role','alert');document.body.append(b)}
 const mind=hit.id==='mind',preg=hit.id==='preg';
 b.innerHTML=`<div class="sx-emg-t"><b>${E(SX.t('emg.title'))}</b><span>${E(SX.t(mind?'emg.mind':preg?'emg.preg':'emg.body'))}</span></div><div class="sx-emg-b">${mind?'<a class="btn red" href="tel:14416">Tele-MANAS 14416</a>':''}<a class="btn ${mind?'s':'red'}" href="tel:112">${E(SX.t('call112'))}</a>${mind?'':`<a class="btn s" href="tel:108">${E(SX.t('call108'))}</a>`}${mind?'':`<button class="btn s" data-sx="sos">${E(SX.t('openSOS'))}</button>`}${hit.aid?`<button class="btn s" data-sx="aid:${hit.aid}">${E(SX.t('firstaid'))}</button>`:''}<button class="btn g" data-sx="emgx:${hit.id}">${E(SX.t('dismiss'))}</button></div>`;
 b.hidden=false}
SX.act.emgx=([id])=>{mute[id]=Date.now()+90000;const b=$('#sxEmg');if(b)b.hidden=true};
let emT=0;
document.addEventListener('input',e=>{const t=e.target;if(!t||!/^(INPUT|TEXTAREA)$/.test(t.tagName)||/password|file|range|checkbox|radio|number|date/.test(t.type||''))return;
 clearTimeout(emT);emT=setTimeout(()=>{const h=SX.emergency(t.value);if(h)showEmg(h)},350)},true);
SX.showEmergency=showEmg;

// ---------------------------------------------------------------- persistent SOS button
// organ picker under the 3D body (Home and Anatomy Lab): one tap focuses the body on a system
const ORG=[['all','🧍','Whole body'],['cardio','🫀','Heart'],['pulmo','🫁','Lungs'],['neuro','🧠','Brain'],['gastro','🥣','Stomach & gut'],['hepato','🟤','Liver'],['nephro','🫘','Kidneys'],['ortho','🦴','Bones'],['endo','⚗️','Hormones']];
function buildOrgans(){if($('#sxOrg')||!$('#stage'))return;const d=document.createElement('div');d.id='sxOrg';d.className='sx-org';d.setAttribute('role','tablist');d.setAttribute('aria-label','Focus the 3D body on a system');
 d.innerHTML=ORG.map(([id,e,n])=>`<button role="tab" data-org="${id}" aria-selected="false"><i>${e}</i><span>${E(SX.p(n))}</span></button>`).join('');$('#stage').append(d);
 d.addEventListener('click',e=>{const b=e.target.closest('[data-org]');if(!b||typeof A==='undefined'||!A.ready)return;const id=b.dataset.org;if(id==='all'){A.clearFocus()}else A.setSpec(id);if(typeof render==='function')render();paintOrgans()});
 if(typeof A!=='undefined'){['setSpec','clearFocus','setPatient'].forEach(k=>{const f=A[k];if(typeof f!=='function')return;A[k]=function(...a){const r=f.apply(this,a);setTimeout(paintOrgans,0);return r}})}
 paintOrgans()}
function paintOrgans(){const d=$('#sxOrg');if(!d)return;const F=typeof A!=='undefined'&&A.focus,k=F&&F.kind==='spec'?F.key:F?'':'all';$$('#sxOrg [data-org]').forEach(b=>{const on=b.dataset.org===k;b.classList.toggle('on',on);b.setAttribute('aria-selected',on);b.querySelector('span').textContent=SX.p(ORG.find(o=>o[0]===b.dataset.org)[2])});const on=d.querySelector('.on');if(on&&on.scrollIntoView)try{on.scrollIntoView({block:'nearest',inline:'center',behavior:'smooth'})}catch(e){}}
SX.paintOrgans=paintOrgans;
function buildFab(){if($('#sxFab'))return;const b=document.createElement('button');b.id='sxFab';b.className='sx-fab';b.dataset.sx='sos';b.setAttribute('aria-label','SOS: emergency help');b.innerHTML='<i></i><span>SOS</span>';document.body.append(b)}

// ---------------------------------------------------------------- boot
SX.boot=()=>{
 document.documentElement.lang=S.lang;
 SX.runSeeds();
 buildNav();buildTop();buildFab();buildOrgans();SX.paintWho();
 const first=SX.me();if(first.sex!==A.sex)SX.pendingModel=true;
 go(page==='dash'?'dash':page,{keep:true});
};
// the main script has finished by now; wait for the 3D engine object (not for the model) and start
SX.ready=true;
})();
