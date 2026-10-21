// ===================== live layer 3: family accounts & sync, cycle tracker, booking, Heart Lab gate, AI reader, pregnancy polish =====================
{
const P=SX.p,D=SX.D;
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1'},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status,detail:j.detail});return j});
const myId=()=>(SX.user&&SX.user.memberId)||((S.members.find(m=>m.rel==='You')||S.members[0])||{}).id;
SX.myId=myId;
const isMe=m=>!!m&&m.id===myId();
const fmtD=d=>{if(!d)return '';try{return new Date(d+'T00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short'})}catch(e){return d}};
const addDays=(d,n)=>{const t=new Date(d+'T00:00');t.setDate(t.getDate()+n);return t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0')};
const dayDiff=(a,b)=>Math.round((new Date(b+'T00:00')-new Date(a+'T00:00'))/864e5);

// ---------------------------------------------------------------- A. household sync (signed-in accounts)
const EXCL=new Set(['key','net','notes','purged','mig','sync','lang','rem']);
const SYK='dk6.sync';
let meta={v:0,sect:{},hash:{},dirty:false,first:true};
try{const m=JSON.parse(localStorage.getItem(SYK));if(m&&typeof m.v==='number')meta=Object.assign(meta,m)}catch(e){}
const saveMeta=()=>{try{localStorage.setItem(SYK,JSON.stringify(meta))}catch(e){}};
const hash=s=>{let h=5381;for(let i=0;i<s.length;i++)h=((h<<5)+h+s.charCodeAt(i))|0;return h};
const pick=()=>{const o={};for(const k of Object.keys(S))if(!EXCL.has(k))o[k]=S[k];return o};
function rehash(stamp){const st=pick(),t=Date.now();let changed=false;for(const k of Object.keys(st)){const h=hash(JSON.stringify(st[k]));if(meta.hash[k]!==h){meta.hash[k]=h;if(stamp){meta.sect[k]=t;changed=true}}}for(const k of Object.keys(meta.hash))if(!(k in st)){delete meta.hash[k];if(stamp){meta.sect[k]=t;changed=true}}return changed}
let pushT=0,applying=false,pushing=false;
const sv0=SX.save;SX.save=(now)=>{sv0(now);if(applying)return;if(rehash(true)){meta.dirty=true;saveMeta();schedulePush()}};
function schedulePush(){if(!SX.user||!meta.dirty)return;clearTimeout(pushT);pushT=setTimeout(push,2500)}
async function push(){if(!SX.user||pushing||!navigator.onLine)return;pushing=true;try{const r=await J('/sync','PUT',{base:meta.v,state:pick(),sect:meta.sect});meta.v=r.version;meta.dirty=false;saveMeta();paintSync('ok')}
 catch(e){if(e.status===409&&e.detail&&e.detail.state){merge(e.detail);pushing=false;return push()}if(e.status===401){SX.user=null}else if(e.status===413){toast(e.message)}paintSync(navigator.onLine?'err':'off')}finally{pushing=false}}
function apply(state,version,sect){applying=true;try{for(const k of Object.keys(S))if(!EXCL.has(k))delete S[k];for(const k of Object.keys(state||{}))if(!EXCL.has(k))S[k]=state[k];if(!Array.isArray(S.members)||!S.members.length)S.members=[{id:'m1',pid:null,name:'You',rel:'You',age:0,sex:'male',w:0,h:0,av:'YO',c:'',shared:true}];
  SX.runSeeds();S.members.forEach(m=>{if(m.dob&&SX.ageFrom)m.age=SX.ageFrom(m.dob);if(!m.htid&&SX.newHtid)m.htid=SX.newHtid()});
  const me=SX.user&&SX.user.memberId;if(meta.first&&me&&S.members.some(m=>m.id===me))S.active=me;if(!S.members.some(m=>m.id===S.active))S.active=S.members[0].id;
  meta.v=version;meta.sect=sect||{};meta.dirty=false;meta.first=false;rehash(false);saveMeta();sv0(true)}finally{applying=false}
 try{if(document.querySelector('.lv-ob')&&SX.cardDone(S.members.find(m=>m.rel==='You')||S.members[0]))SX.closeModal(true)}catch(e){}
 SX.pendingModel=true;SX.applyModel();if(SX.pregNav)SX.pregNav();SX.paintWho();try{go(page,{keep:true})}catch(e){if(typeof render==='function')render()}paintSync('ok')}
function merge(remote){const rs=remote.state||{},rsect=remote.sect||{},loc=pick(),out={},sect={};const keys=new Set([...Object.keys(loc),...Object.keys(rs)]);
 for(const k of keys){const lt=meta.sect[k]||0,rt=rsect[k]||0;
  if(k==='members'){const L=loc.members||[],R=rs.members||[],byId=new Map();(rt>=lt?L:R).forEach(m=>byId.set(m.id,m));(rt>=lt?R:L).forEach(m=>byId.set(m.id,Object.assign({},byId.get(m.id)||{},m)));out[k]=[...byId.values()]}
  else out[k]=rt>lt?rs[k]:(k in loc?loc[k]:rs[k]);
  sect[k]=Math.max(lt,rt)}
 const act=S.active;apply(out,remote.version,sect);if(S.members.some(m=>m.id===act))S.active=act;meta.dirty=true;saveMeta()}
// a device that has never synced and holds only the untouched starter profile takes the family's data as is (never merges its placeholder in)
const localFresh=()=>{const y=S.members.find(m=>m.rel==='You')||S.members[0];let joined=false;try{joined=!!localStorage.getItem('dk6.join')}catch(e){}return joined||(S.members.length===1&&!SX.cardDone(y)&&!Object.values(S.results||{}).some(a=>a&&a.length)&&!Object.values(S.meds||{}).some(a=>a&&a.length)&&!(S.vault||[]).length)};
async function pull(){if(!SX.user||!navigator.onLine)return;try{const r=await J('/sync');if(r.memberId&&SX.user)SX.user.memberId=r.memberId;
  if(r.version>meta.v){if(!meta.dirty||!r.state||(meta.v===0&&localFresh())){apply(r.state,r.version,r.sect);try{localStorage.removeItem('dk6.join')}catch(e){}}else merge(r);if(meta.dirty)push()}
  else if(r.version===0&&S.members.length&&(SX.cardDone(S.members.find(m=>m.rel==='You')||S.members[0])||S.members.length>1)){meta.dirty=true;push()}
  else if(meta.dirty)push();else paintSync('ok');
  if(SX.user&&!SX.user.memberId){const me=S.members.find(m=>m.rel==='You');if(me){J('/family/me','POST',{member_id:me.id}).then(()=>{SX.user.memberId=me.id}).catch(()=>{})}}}
 catch(e){if(e.status===401)SX.user=null;paintSync(navigator.onLine?'err':'off')}}
SX.sync={pull,push,meta:()=>meta};
function paintSync(st){const a=document.getElementById('sxAcct');if(!a)return;a.dataset.sync=st;a.title=(P('Account & security'))+(st==='ok'?' · '+P('Synced'):st==='err'?' · '+P('Sync paused'):'')}
const lu1=SX.loadUser;SX.loadUser=async()=>{await lu1();if(SX.user){try{if(SX.hello)await SX.hello()}catch(e){}pull()}};
addEventListener('online',()=>{if(meta.dirty)push();else pull()});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&SX.user)pull()});
addEventListener('pagehide',()=>{if(meta.dirty&&SX.user&&navigator.sendBeacon){/* best effort: the next open pushes it */}});
// "me" in a shared household: my own profile is always visible and greeted as You
const vw0=SX.viewable;SX.viewable=m=>!!m&&(isMe(m)||vw0(m));
SX.reg('dash',{head:()=>{const m=SX.me(),f=m.name.split(' ')[0],me=isMe(m)||m.rel==='You';return [me?`${P('Hello')}, ${f} 👋`:`${f}'s ${P('health')}`,new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long'})+(me?'. '+P('Here is today at a glance.'):'. '+P(m.rel)+'. '+P('Here is today at a glance.'))]}});
// sign-in nudge for guests with real data
SX.extend('family',{before(){if(SX.user||!SX.cardDone(S.members.find(m=>m.rel==='You')||S.members[0]))return '';return `<div class="card wide lv3-nudge"><div><b>${P('Keep your family\u2019s records safe')}</b><p class="mute sm" style="margin:4px 0 0">${P('Sign in to back them up (encrypted, stored in India) and to invite family members to see their own profile on their phone.')}</p></div><a class="btn p sm" href="/signin?next=/app">${P('Sign in')}</a></div>`}});

// ---------------------------------------------------------------- B. family accounts: invite and status
let INV=null;
async function loadInvites(){if(!SX.user)return null;try{INV=await J('/family/invites')}catch(e){INV=null}return INV}
const invStatus=m=>{if(!INV)return null;const acc=INV.accounts.find(a=>a.memberId===m.id);if(acc)return{k:'joined',t:acc.me?P('You'):P('Has an account'),sub:acc.phone||acc.email||''};const i=INV.invites.filter(x=>x.memberId===m.id).sort((a,b)=>b.created-a.created)[0];if(i&&i.status==='pending')return{k:'pending',t:P('Invited'),sub:(i.contact||'')+' · '+P('link valid till')+' '+fmtD(new Date(i.expires*1000).toISOString().slice(0,10)),tok:i.token};return null};
SX.extend('family',{after(){if(!SX.user)return '';return `<div class="card wide" id="lv3-acc"><div class="hd"><div><h3>${P('Family accounts')}</h3><small class="mute">${P('Each adult can sign in on their own phone and see their profile and the family\u2019s shared records.')}</small></div></div>
  <div class="lv3-acclist">${S.members.map(m=>{const st=invStatus(m),me=isMe(m);return `<div class="row lv3-accrow">${SX.avatar(m,40)}<div class="grow"><b>${E(m.name)}${me?` <span class="lv-tag">${P('You')}</span>`:''}</b><small class="mute">${st?E(st.t)+(st.sub?' · '+E(st.sub):''):m.age<18?P('Under 18: managed by you'):P('No account yet')}</small></div>${me||m.age<18?'':st&&st.k==='joined'?`<span class="lv-ver"><span>✓</span> ${P('Joined')}</span>`:st&&st.k==='pending'?`<button class="btn s sm" data-sx="finvite:${m.id}">${P('Resend')}</button>`:`<button class="btn p sm" data-sx="finvite:${m.id}">${P('Invite')}</button>`}</div>`}).join('')}</div>
  <p class="mute sm" style="margin:10px 0 0">${P('Profiles marked Private in Consent stay hidden from other accounts. Photos and PDFs stay on the device where they were added.')}</p></div>`},mounted(){if(SX.user&&!INV)loadInvites().then(()=>{if(page==='family')render()})}});
SX.act.finvite=([id])=>{const m=SX.member(id);if(!m)return;if(!SX.user){location.href='/signin?next=/app';return}
 SX.modal(`<h2>${P('Invite')} ${E(m.name)}</h2><p class="mute">${P('They create their own account and see their profile, your shared records and the family\u2019s cards. Nothing is sent until you share the link.')}</p>
  <form class="form lv-form" data-sxf="finvite2:${id}" novalidate><label class="full">${P('Their mobile number or email')} <small>${P('optional')}</small><input name="c" value="${E(m.ph||'')}" placeholder="98765 43210 or name@example.com" autocomplete="off"></label><p class="full lv-err" role="alert" hidden></p>
  <div class="full lv-row-end"><button class="btn s" type="button" data-sx="closeModal">${P('Cancel')}</button><button class="btn p" type="submit">${P('Create invite link')}</button></div></form>`,{label:P('Invite')})};
SX.chg.finvite2=async([id],f)=>{const m=SX.member(id),err=f.querySelector('.lv-err'),c=String(new FormData(f).get('c')||'').trim();
 try{const r=await J('/family/invite','POST',{member_id:id,name:m.name,contact:c});if(c&&!m.ph&&r.channel==='phone'){m.ph=SX.phoneNorm(c)||m.ph;SX.save()}await loadInvites();
  const msg=`${(SX.user.name||'').split(' ')[0]} ${P('added you to the family on Urban Health. Create your account here (link valid 7 days):')} ${r.link}`;
  SX.modal(`<h2>${P('Share the invite')}</h2><p class="mute">${r.sent?P('An email has been sent. You can also share the link yourself.'):P('Send this link to')+' '+E(m.name)+'.'}</p><p class="lv3-link">${E(r.link)}</p>
   <div class="row"><a class="btn p" href="https://wa.me/${m.ph?E(m.ph.replace(/\\D/g,'')):''}?text=${encodeURIComponent(msg)}" target="_blank" rel="noopener">💬 WhatsApp</a>${navigator.share?`<button class="btn s" data-sx="fshare:${encodeURIComponent(msg)}">${P('Share…')}</button>`:''}<button class="btn s" data-sx="fcopy:${encodeURIComponent(r.link)}">${P('Copy link')}</button></div>
   <div class="lv-row-end"><button class="btn s" data-sx="closeModal">${P('Done')}</button></div>`,{label:P('Invite')});render()}
 catch(e){err.textContent=e.message;err.hidden=false}};
SX.act.fshare=async([t])=>{try{await navigator.share({text:decodeURIComponent(t)})}catch(e){}};
SX.act.fcopy=async([l])=>{try{await navigator.clipboard.writeText(decodeURIComponent(l));toast(P('Link copied'))}catch(e){toast(P('Could not copy'))}};

// ---------------------------------------------------------------- C. wallet: masked until opened
const ch0=SX.cardHTML;SX.cardHTML=(m,opt)=>{const h=ch0(m);if(!(opt&&opt.mask))return h;const mp=m.ph?m.ph.replace(/^(\+\d\d)(\d{5})(\d{5})$/,'$1 ••••• $3'):'';const mid=(m.htid||'').replace(/^(THT-)\w{4}-\w{4}-(\w{4})$/,'$1••••-••••-$2');
 let out=h;if(m.ph)out=out.split(E(m.ph.replace(/^\+91(\d{5})(\d{5})$/,'+91 $1 $2'))).join(E(mp));if(m.htid)out=out.split(E(m.htid)).join(E(mid));return out.replace(/<span class="lv-ver"[\s\S]*?<\/span><\/span>|<span class="lv-unver">[^<]*<\/span>/,'')};

// ---------------------------------------------------------------- D. Heart Lab only when it is relevant
S.heartLab=S.heartLab||{};
const heartOn=m=>{if(!m)return false;if(S.heartLab[m.id])return true;const mid=SX.midOf(m.id);if((mid.conditions||[]).some(c=>/heart|cardiac|hypertens|\bbp\b|pressure|cholesterol|angina|stent|bypass|arrhythm|afib|ecg|valve/i.test(c)))return true;
 if(SX.labFlags(m).some(f=>/^(ldl|tc|hdl|tg)$/.test(f.x.key)))return true;if((S.results[m.id]||[]).some(r=>r.k==='find'&&/ecg|echo|heart|cardiac/i.test(r.n||'')))return true;const v=SX.latest&&SX.latest(m,'sys');return !!(v&&(v.sys>=140||v.dia>=90))};
SX.heartOn=heartOn;
const tv0=SX.tabVisible;SX.tabVisible=k=>{if(k==='heart')return page==='heart'||heartOn(SX.me());if(k==='cycle'){const m=SX.me();return m.sex==='female'&&m.age>=12&&m.age<=55&&!SX.pregOn(m)};return tv0(k)};
const tab0=SX.act.tab;SX.act.tab=([k])=>{if(k==='heart'&&!heartOn(SX.me())){const m=SX.me();SX.modal(`<h2>${P('Heart Lab')}</h2><p class="mute">${P('A living 3D heart for people with a heart condition, high blood pressure, cholesterol or an ECG to follow. It is not needed for everyone.')}</p><p>${P('Show Heart Lab for')} <b>${E(m.name)}</b>?</p><div class="lv-row-end"><button class="btn s" data-sx="closeModal">${P('Not now')}</button><button class="btn p" data-sx="hearton:${m.id}">${P('Show it')}</button></div>`,{label:'Heart Lab'});return}tab0([k])};
SX.act.hearton=([id])=>{S.heartLab[id]=true;SX.save();SX.closeModal();go('heart')};
SX.extend('set',{after(){const m=SX.me();return `<div class="card wide"><div class="row between"><div><b>${P('Heart Lab for')} ${E(m.name)}</b><small class="mute" style="display:block">${P('Shown automatically for heart conditions, high BP or cholesterol results. Switch it on here any time.')}</small></div><label class="sx-sw"><input type="checkbox" data-sxc="heartsw" ${heartOn(m)?'checked':''}><i></i></label></div></div>`}});
SX.chg.heartsw=(a,el)=>{S.heartLab[SX.me().id]=el.checked;SX.save();SX.paintNav();if(page==='set')render()};

// ---------------------------------------------------------------- E. Appointments (your log) and Booking (find a place) as separate tabs
SX.addStrings({'tab.book':D('Booking','बुकिंग','బుకింగ్'),'tab.cycle':D('Cycle','चक्र','సైకిల్'),'tab.appts':D('Appointments','अपॉइंटमेंट','అపాయింట్‌మెంట్లు')});
const CARE=SX.G.find(g=>g.k==='care');CARE.tabs=['appts','book','cycle','docs','msgs','preg','bill'];
const pn0=SX.pregNav;SX.pregNav=()=>{pn0();const on=SX.pregOn(SX.me());CARE.tabs=on?['preg','appts','book','docs','msgs','bill']:['appts','book','cycle','docs','msgs','preg','bill']};
const visits=m=>SX.apptsOf(m);
SX.reg('appts',{head:()=>[P('Appointments'),P('Your family\u2019s doctor visits, past and upcoming.')]});
let HOSP=null,bookSp='';
const SPEC=[['gp','General physician'],['cardio','Cardiology'],['endo','Diabetes & hormones'],['obgyn','Women\u2019s health'],['paed','Paediatrics'],['ortho','Bones & joints'],['gastro','Stomach & liver'],['nephro','Kidney'],['pulmo','Chest & lungs'],['neuro','Brain & nerves'],['derm','Skin'],['eye','Eye'],['ent','ENT'],['dent','Dental'],['psy','Mental health']];
SX.reg('book',{head:()=>[P('Booking'),P('Find the right place, then add the visit to your appointments.')],render:()=>{const m=SX.me();
 return `<div class="card wide"><h3>${P('What do you need?')}</h3><div class="chips">${SPEC.map(([k,n])=>`<button class="chip ${bookSp===k?'on':''}" data-sx="bsp:${k}">${E(P(n))}</button>`).join('')}</div>
  ${bookSp?`<p class="mute sm" style="margin:12px 0 0">${P('Suggested from your records:')} ${suggestSpec(m)||P('nothing specific right now')}.</p>`:''}</div>
  <div class="card wide"><div class="hd"><div><h3>${P('Hospitals near you')}</h3><small class="mute">${HOSP?(HOSP.approx?P('Showing')+' '+E(HOSP.city)+' · '+P('tap “Use my location” for exact distances'):E(HOSP.city)):P('Verified partner hospitals, nearest first.')}</small></div><button class="btn s sm" data-sx="bgeo">📍 ${P('Use my location')}</button></div>
  ${HOSP===null?`<div class="sx-livel"><div class="sx-spin sm"></div> ${P('Finding hospitals…')}</div>`:HOSP.error?`<p class="mute sm">${E(HOSP.error)}</p>`:HOSP.hospitals.length?`<div class="lv3-hlist">${HOSP.hospitals.map(h=>`<div class="lv3-h"><div class="grow"><b>${E(h.name)}</b><small>${[h.km!=null?h.km+' km':'',h.address||h.area||'',h.rating?'★ '+h.rating:''].filter(Boolean).map(E).join(' · ')}</small></div>${h.phone?`<a class="btn p sm" href="tel:${E(h.phone)}">${P('Call')}</a>`:''}${h.lat&&h.lng?`<a class="btn s sm" href="https://www.google.com/maps/dir/?api=1&destination=${h.lat},${h.lng}" target="_blank" rel="noopener">${P('Directions')}</a>`:''}<button class="btn s sm" data-sx="badd:${E(h.name)}">＋ ${P('Add visit')}</button></div>`).join('')}</div>`:`<div class="lv2-empty"><div class="lv2-empty-ic">🏥</div><b>${P('No partner hospital near you yet')}</b><p class="mute sm">${P('We are onboarding hospitals city by city. You can still add any visit to your appointments.')}</p><button class="btn p sm" data-sx="badd:">＋ ${P('Add a visit')}</button></div>`}</div>
  ${SX.lvSoon(P('Book with a doctor in the app'),P('Online booking with verified doctors, with the records you choose to share, is coming. Until then: call, visit, and keep the appointment here so the whole family sees it.'),'📅')}`},
 after(){if(HOSP===null)loadHosp()}});
function suggestSpec(m){const f=SX.labFlags(m)[0];if(!f)return '';const L=f.st.L;const map={cardio:'Cardiology',endo:'Diabetes & hormones',hepato:'Stomach & liver',nephro:'Kidney',hemato:'General physician',ortho:'Bones & joints',obgyn:'Women\u2019s health'};return map[L.sp]?P(map[L.sp])+' ('+E(L.n)+' '+(f.st.s==='high'?P('high'):P('low'))+')':''}
async function loadHosp(){try{const g=await SX.geo(false);const q=g?`?lat=${g.lat}&lng=${g.lng}`:'';HOSP=await SX.api('/hospitals'+q,{silent:true})}catch(e){HOSP={error:e.offline?P('No connection right now.'):P('Hospitals are not available right now.')}}if(page==='book')render()}
SX.act.bsp=([k])=>{bookSp=k;render()};SX.act.bgeo=async()=>{await SX.geo(true);HOSP=null;render();loadHosp()};
SX.act.badd=([name])=>{go('appts');setTimeout(()=>{SX.act.vadd();const f=document.querySelector('.lv-vform input[name=dh]');if(f&&name)f.value=name;const w=document.querySelector('.lv-vform input[name=why]');if(w&&bookSp)w.value=P(SPEC.find(s=>s[0]===bookSp)[1])},60)};

// ---------------------------------------------------------------- F. period & fertility tracker
S.cycle=S.cycle||{};
const cyc=m=>(S.cycle[m.id]=S.cycle[m.id]||{periods:[],len:null,notes:[]});
function cycleStats(m){const c=cyc(m),ps=c.periods.map(p=>p.d).sort();if(!ps.length)return null;const gaps=[];for(let i=1;i<ps.length;i++){const g=dayDiff(ps[i-1],ps[i]);if(g>=15&&g<=60)gaps.push(g)}
 const recent=gaps.slice(-6),avg=c.len||(recent.length?Math.round(recent.reduce((a,b)=>a+b,0)/recent.length):28),last=ps[ps.length-1],today=SX.today(),day=dayDiff(last,today)+1;
 const next=addDays(last,avg),ov=addDays(next,-14),fs=addDays(ov,-5),fe=addDays(ov,1),late=dayDiff(next,today),vary=recent.length>=3?Math.max(...recent)-Math.min(...recent):0;
 const phase=day<=5?'period':today>=fs&&today<=fe?'fertile':today<fs?'follicular':'luteal';
 return{avg,last,day,next,ov,fs,fe,late,vary,phase,n:ps.length,plen:(c.periods.find(p=>p.d===last)||{}).len||5}}
SX.cycleStats=cycleStats;
SX.reg('cycle',{head:()=>[P('Cycle'),P('Periods, the fertile window and what to watch for.')],render:()=>{const m=SX.me(),st=cycleStats(m),c=cyc(m);
 const hero=st?`<div class="card wide sx-hero lv3-cyc ${st.phase}"><div class="sx-hero-t"><div><small>${E(m.name)} · ${P('Cycle day')} ${st.day}</small><b class="lv-h0">${st.phase==='period'?P('On your period'):st.phase==='fertile'?P('Fertile window'):st.late>0?`${P('Period is')} ${st.late} ${P('days late')}`:`${P('Next period in')} ${-st.late} ${P('days')}`}</b>
   <p class="mute sm" style="margin:4px 0 0">${st.phase==='fertile'?P('Most likely days to conceive this cycle:')+' '+fmtD(st.fs)+' – '+fmtD(st.fe):st.late>0?P('Up to a week late is common. If you could be pregnant, a home test is accurate from the first day of a missed period.'):P('Fertile window')+' '+fmtD(st.fs)+' – '+fmtD(st.fe)+' · '+P('ovulation around')+' '+fmtD(st.ov)}</p></div>
   <div class="sx-hero-v"><div><small>${P('Cycle')}</small><b>${st.avg} ${P('days')}</b></div><div><small>${P('Last period')}</small><b>${fmtD(st.last)}</b></div>${st.vary?`<div><small>${P('Varies by')}</small><b>${st.vary} ${P('days')}</b></div>`:''}</div></div>
   <div class="lv3-cycbar" aria-hidden="true">${Array.from({length:st.avg},(_,i)=>{const d=addDays(st.last,i);const k=i<st.plen?'p':d>=st.fs&&d<=st.fe?'f':d===st.ov?'o':'';return `<i class="${k} ${d===SX.today()?'now':''}"></i>`}).join('')}</div><div class="lv3-cyclg"><span><i class="p"></i>${P('Period')}</span><span><i class="f"></i>${P('Fertile')}</span><span><i class="o"></i>${P('Ovulation')}</span></div>
   <div class="lv-hero-a"><button class="btn p sm" data-sx="cylog">＋ ${P('Log a period')}</button>${st.late>=5?`<button class="btn s sm" data-sx="tab:pregopt">${P('Could I be pregnant?')}</button>`:''}</div></div>`
  :`<div class="card wide sx-hero lv-hero0"><div class="sx-hero-t"><div><small>${E(m.name)} · ${P('Cycle')}</small><b class="lv-h0">${P('Log your last period to start')}</b><p class="mute sm" style="margin:4px 0 0">${P('From the first day of your last period the app estimates your next period, ovulation and the fertile window. Estimates get better with each cycle you log.')}</p></div></div><div style="padding:6px 0 12px"><button class="btn p sm" data-sx="cylog">＋ ${P('Log a period')}</button></div></div>`;
 const up=st?[[P('Fertile window'),fmtD(st.fs)+' – '+fmtD(st.fe)],[P('Ovulation (estimate)'),fmtD(st.ov)],[P('Next period'),fmtD(st.next)],[P('Period after that'),fmtD(addDays(st.next,st.avg))]]:[];
 return hero+`<div class="lv3-two wide"><div class="card"><h3>${P('Coming up')}</h3>${up.length?`<div class="lv2-kv">${up.map(([k,v])=>`<div><small>${E(k)}</small><b>${E(v)}</b></div>`).join('')}</div><p class="mute sm" style="margin:10px 0 0">${P('Ovulation usually happens about 14 days before the next period, so these are estimates. They are less reliable when cycles vary a lot, and this is not a method of contraception.')}</p>`:`<p class="mute sm">${P('Dates appear after your first log.')}</p>`}</div>
  <div class="card"><div class="hd"><h3>${P('History')}</h3><small class="mute">${c.periods.length} ${P('logged')}</small></div>${c.periods.length?c.periods.slice().sort((a,b)=>b.d.localeCompare(a.d)).slice(0,8).map(p=>`<div class="row"><div class="grow"><b>${E(fmtD(p.d))}</b><small class="mute">${p.len?p.len+' '+P('days'):''}${p.flow?' · '+P(p.flow):''}${p.sym?' · '+E(p.sym):''}</small></div><button class="btn g sm" data-sx="cydel:${p.d}" aria-label="${E(P('Remove'))}">✕</button></div>`).join(''):`<p class="mute sm">${P('No periods logged yet.')}</p>`}</div></div>
  <div class="card wide"><h3>${P('Worth knowing')}</h3><ul class="sx-ul">${st&&st.vary>=9?`<li>${P('Your cycles vary by')} ${st.vary} ${P('days. Variation over 7–9 days is worth mentioning to a doctor, especially with heavy bleeding, pain or difficulty conceiving.')}</li>`:''}<li>${P('Bleeding between periods, very heavy periods (soaking a pad every hour), or severe pain are reasons to see a doctor.')}</li><li>${P('Trying for a baby: the two days before ovulation are the most fertile. Folic acid 400 µg a day is advised from before conception.')}</li><li>${P('Missed a period and could be pregnant? Take a home test, and if positive, switch on Pregnancy tracking: your last period date fills in automatically.')}</li></ul></div>`},after:()=>{}});
SX.act.cylog=()=>{const tm=SX.today();SX.modal(`<h2>${P('Log a period')}</h2><form class="form lv-form" data-sxf="cysave" novalidate><label>${P('First day')}<input name="d" type="date" required max="${tm}" value="${tm}"></label><label>${P('Length')} <small>${P('days')}</small><input name="len" type="number" min="1" max="14" value="5"></label>
 <label>${P('Flow')}<select name="flow"><option value="">${P('Not noted')}</option><option>${P('Light')}</option><option>${P('Medium')}</option><option>${P('Heavy')}</option></select></label><label>${P('Symptoms')} <small>${P('optional')}</small><input name="sym" maxlength="80" placeholder="${E(P('cramps, headache…'))}"></label>
 <p class="full lv-err" role="alert" hidden></p><div class="full lv-row-end"><button class="btn s" type="button" data-sx="closeModal">${P('Cancel')}</button><button class="btn p" type="submit">${P('Save')}</button></div></form>`,{label:P('Period')})};
SX.chg.cysave=(a,f)=>{const m=SX.me(),fd=new FormData(f),d=String(fd.get('d')||''),err=f.querySelector('.lv-err');if(!d||d>SX.today()){err.textContent=P('Please check the date.');err.hidden=false;return}
 const c=cyc(m);c.periods=c.periods.filter(p=>Math.abs(dayDiff(p.d,d))>10);c.periods.push({d,len:Math.max(1,Math.min(14,+fd.get('len')||5)),flow:String(fd.get('flow')||''),sym:String(fd.get('sym')||'').slice(0,80)});SX.save();SX.closeModal();render();toast(P('Period logged'))};
SX.act.cydel=([d])=>{const c=cyc(SX.me());c.periods=c.periods.filter(p=>p.d!==d);SX.save();render()};
// pregnancy opt-in: pre-fill the last period date from the cycle log
const pregon0=SX.act.pregon;SX.act.pregon=()=>{pregon0();const st=cycleStats(SX.me());const i=document.querySelector('.sx-sheet input[name=d]');if(i&&st&&!i.value)i.value=st.last};
// cycle notifications
const notes0=SX.notes;SX.notes=()=>{const out=notes0();S.members.forEach(m=>{if(!(m.sex==='female'&&!SX.pregOn(m)))return;const st=cycleStats(m);if(!st)return;const t=SX.today();
 if(st.fs===addDays(t,1)||st.fs===t)out.push({id:`cyc:f:${m.id}:${st.fs}`,k:'cycle',ic:'🌸',t:`${P('Fertile window')} · ${E(m.name)}`,s:`${fmtD(st.fs)} – ${fmtD(st.fe)}`,go:'cycle',m:m.id});
 if(-st.late===2)out.push({id:`cyc:p:${m.id}:${st.next}`,k:'cycle',ic:'🩸',t:`${P('Period expected in 2 days')} · ${E(m.name)}`,s:fmtD(st.next),go:'cycle',m:m.id});
 if(st.late===7)out.push({id:`cyc:l:${m.id}:${st.next}`,k:'cycle',ic:'🗓️',t:`${P('Period is a week late')} · ${E(m.name)}`,s:P('A home pregnancy test is accurate now'),go:'cycle',m:m.id})});return out};

// ---------------------------------------------------------------- G. pregnancy: trackers up front
I.pregtrk=1;
SX.pregTrackers=()=>`<div class="card lv3-trk"><div class="hd"><h3>${P('Today\u2019s trackers')}</h3><small class="mute">${P('Tap to open')}</small></div><div class="lv3-trkg">
 <button data-pa="tab:tools"><i>🦶</i><b>${P('Kick counter')}</b><small>${P('Count 10 movements')}</small></button><button data-pa="tab:tools"><i>⏱️</i><b>${P('Contractions')}</b><small>${P('Time and spacing')}</small></button><button data-pa="tab:water"><i>💧</i><b>${P('Water')}</b><small>${P('Daily goal')}</small></button><button data-pa="tab:health"><i>🩺</i><b>${P('Symptoms & signs')}</b><small>${P('What to call about')}</small></button><button data-pa="tab:food"><i>🥗</i><b>${P('Food')}</b><small>${P('This trimester')}</small></button><button data-pa="tab:birth"><i>👶</i><b>${P('Birth plan')}</b><small>${P('Bag, plan, labour')}</small></button></div></div>`;

// ---------------------------------------------------------------- H. Home: read a document with AI, see it on the body
const CODE_RE={ldl:/left coronary artery$|wall of ventricle/,tc:/left coronary artery$|wall of ventricle/,hdl:/left coronary artery$|wall of ventricle/,tg:/left coronary artery$|wall of ventricle/,alt:/surface of liver|caudate lobe of liver|quadrate lobe of liver/,ast:/surface of liver|caudate lobe of liver/,bili:/gallbladder|caudate lobe of liver/,alb:/caudate lobe of liver/,creat:/^(left|right) kidney$/,urea:/^(left|right) kidney$/,uric:/^(left|right) kidney$/,hba1c:/pancrea/,glu_f:/pancrea/,glu_pp:/pancrea/,glu_r:/pancrea/,tsh:/thyroid/,t3:/thyroid/,t4:/thyroid/,hb:/^spleen$|sternum/,wbc:/^spleen$/,plt:/^spleen$/,vitd:/femur|lumbar vertebra/,ca:/femur|lumbar vertebra/,b12:/^stomach$/,crp:/^spleen$/,esr:/^spleen$/,psa:/^prostate$/};
SX.act.onbody=([code])=>{const m=SX.me(),f=SX.labFlags(m).find(x=>x.x.key===code);if(!f){toast(P('No flagged result to show'));return}const L=f.st.L,re=CODE_RE[code];
 const show=()=>{try{A.setSpec(L.sp);if(re)A.pickMatch(re,`${L.n}: ${f.x.val} ${L.u}`,f.st.s==='high'?'High':'Low')}catch(e){console.warn(e)}};
 if(page!=='dash'&&page!=='lab'){go('dash');setTimeout(show,300)}else show()};
SX.extend('dash',{before(){const m=SX.me(),recent=(S.vault||[]).filter(v=>v.m===m.id&&v.ai).sort((a,b)=>(b.date||'').localeCompare(a.date||'')).slice(0,2),flags=SX.labFlags(m).slice(0,4);
 return `<div class="card lv3-ai"><div class="hd"><div><h3>✦ ${P('Read a report with AI')}</h3><small class="mute">${P('Upload a report or prescription. It is explained in plain words and the findings are shown on the body.')}</small></div></div>
  <div class="row"><button class="btn p sm" data-sx="aipick">📄 ${P('Upload & read')}</button><button class="btn s sm" data-sx="tab:vault">${P('Vault')}</button></div><input type="file" id="aifile" accept="image/*,application/pdf" capture="environment" hidden>
  ${flags.length?`<div class="lv3-flags">${flags.map(f=>`<button class="lv3-flag ${f.st.s}" data-sx="onbody:${f.x.key}"><b>${E(f.st.L.n)}</b><small>${E(String(f.x.val))} ${E(f.st.L.u)} · ${f.st.s==='high'?P('High'):P('Low')} · ${P('see on body')}</small></button>`).join('')}</div>`:recent.length?`<p class="mute sm" style="margin:10px 0 0">${P('Latest read:')} ${recent.map(v=>E(v.name)).join(', ')}</p>`:''}</div>`},
 mounted(){const i=$('#aifile');if(i)i.onchange=()=>{const f=i.files&&i.files[0];i.value='';if(f)readDoc(f)}}});
SX.act.aipick=()=>{const i=$('#aifile');if(i)i.click()};
async function readDoc(f){const m=SX.me();if(!/^(image\/|application\/pdf)/.test(f.type)||f.size>15e6){toast(P('PDF or image under 15 MB only'));return}const id=uid('v');try{await SX.files.put(id,f)}catch(e){toast(P('This browser could not store the file'));return}
 const kind=/presc|rx/i.test(f.name)?'Prescription':'Lab report';S.vault.push({id,m:m.id,name:f.name.replace(/\.[a-z0-9]+$/i,'').slice(0,80),kind,date:SX.today(),size:f.size,mime:f.type,file:true});SX.save();
 await SX.act.ai([id]);if(page==='dash')render()}
// after values are saved from a reading, show the first flagged one on the body instead of a table
const as0=SX.act.aisave;SX.act.aisave=([id])=>{const m=SX.me(),before=(S.results[m.id]||[]).length;as0([id]);const after=(S.results[m.id]||[]).length;if(after>before){const f=SX.labFlags(m)[0];if(f){go('dash');setTimeout(()=>SX.act.onbody([f.x.key]),400)}}};

// ---------------------------------------------------------------- I. join link on first open
try{const t=sessionStorage.getItem('tht-joined');if(t){sessionStorage.removeItem('tht-joined');toast(P('Welcome to the family'))}}catch(e){}
}
