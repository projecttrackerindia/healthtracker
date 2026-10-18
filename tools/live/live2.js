// ===================== live layer 2: body by person, contacts, pregnancy mode, cards & insurance, notifications =====================
// Inserted by tools/live/p1.py right after the first live layer, before SX.boot(). Same scope: SX, S, E, uid, go, render, page, toast, $, $$, A, I, ic.
{
const P=SX.p,D=SX.D;
const MARK='<svg viewBox="8 10 52 44" aria-hidden="true"><path d="M21.5 15a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4v34a4 4 0 0 1-4 4h-3a4 4 0 0 1-4-4V37.5H13a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h8.5z" fill="currentColor"/><path d="M32 32h5l3.2-8 4.6 16 3.2-8h0.4" fill="none" stroke="currentColor" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="55.2" cy="32" r="3.3" fill="currentColor"/></svg>';
SX.MARK=MARK;
const you=()=>S.members.find(m=>m.rel==='You')||S.members[0];
const phShow=p=>{if(!p)return '';const m=/^\+91(\d{5})(\d{5})$/.exec(p);return m?`+91 ${m[1]} ${m[2]}`:p};
const fmtD=d=>{if(!d)return '';try{return new Date(d+'T00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}catch(e){return d}};
const daysTo=d=>{if(!d)return null;const t=new Date(d+'T00:00');if(isNaN(t))return null;return Math.ceil((t-new Date().setHours(0,0,0,0))/864e5)};
SX.newHtid=()=>{const a='ABCDEFGHJKLMNPQRSTUVWXYZ23456789';let s='';const r=new Uint32Array(12);try{crypto.getRandomValues(r)}catch(e){for(let i=0;i<12;i++)r[i]=Math.random()*1e9}for(let i=0;i<12;i++)s+=a[r[i]%a.length];return 'THT-'+s.slice(0,4)+'-'+s.slice(4,8)+'-'+s.slice(8)};
S.members.forEach(m=>{if(!m.htid)m.htid=SX.newHtid()});
S.cards=S.cards||[];S.notes=S.notes||{seen:{},snooze:{}};S.rem=S.rem||{on:false,sent:{}};S.rem.times=S.rem.times||{Morning:'08:00',Afternoon:'14:00',Evening:'18:00',Night:'21:00'};S.rem.off=S.rem.off||{};
const pregActive=()=>SX.pregOn(SX.me());

// ---------------------------------------------------------------- 1. the body follows the person: no sex switch anywhere
SX.extend('lab',{before(){const m=SX.me();return `<p class="mute sm lv2-note">${P('Showing')} <b>${E(m.name)}</b>: ${m.sex==='female'?P('female anatomy'):P('male anatomy')}. ${P('The model follows the person selected at the top.')}</p>`}});

// ---------------------------------------------------------------- 2. one person: a name, not a dropdown
const pw0=SX.paintWho;
SX.paintWho=()=>{pw0();const w=$('#sxWho');if(!w)return;const m=SX.me(),one=S.members.length===1;w.classList.toggle('lv2-one',one);
 if(one){w.innerHTML=`${SX.avatar(m,30)}<span class="sx-wn"><b>${E(m.name)}</b><small>${P('Add family')}</small></span>`;w.setAttribute('aria-haspopup','false');w.setAttribute('aria-label',P('Add a family member'));w.onclick=()=>{go('family');SX.act.fedit(['new'])}}
 else{w.setAttribute('aria-haspopup','menu');w.setAttribute('aria-label',SX.t('who'))}};

// ---------------------------------------------------------------- 3. emergency contacts
const RELS2=['Spouse','Mother','Father','Son','Daughter','Brother','Sister','Friend','Neighbour','Doctor','Other'];
const cIcon={Spouse:'💞',Mother:'👩',Father:'👨',Son:'👦',Daughter:'👧',Brother:'🧑',Sister:'👩',Friend:'🤝',Neighbour:'🏠',Doctor:'🩺',Other:'👤'};
SX.reg('contacts',{head:()=>[P('Emergency contacts'),P('The people who hear from you first when you press SOS.')],
 render:()=>{const m=SX.me(),cs=SX.contactsOf(m.id),on=cs.filter(c=>c.notify&&c.ph).length;
  return `<div class="card wide lv2-cwrap"><div class="hd"><div><h3>${m.rel==='You'?P('My contacts'):E(SX.poss(m.name))+' '+P('contacts')}</h3><small class="mute">${cs.length?`${on} ${P('of')} ${cs.length} ${P('will be alerted on SOS')}`:P('No one is alerted yet.')}</small></div><button class="btn p sm" data-sx="cadd">＋ ${P('Add contact')}</button></div>
   ${cs.length?`<div class="lv2-clist">${cs.map(c=>`<div class="lv2-c ${c.notify&&c.ph?'on':''}"><div class="lv2-cav" aria-hidden="true">${cIcon[c.rel]||'👤'}</div><div class="grow"><b>${E(c.n)}</b><small>${E(P(c.rel))}${c.ph?` · <a href="tel:${E(c.ph)}">${E(phShow(c.ph))}</a>`:` · <span class="lv2-warn">${P('No phone number')}</span>`}</small></div>
    <label class="lv2-tog" title="${E(P('Alert on SOS'))}"><input type="checkbox" data-sxc="cnotify:${c.id}" ${c.notify?'checked':''} ${c.ph?'':'disabled'}><i></i><span>${P('SOS')}</span></label><button class="lv2-ib" data-sx="cadd:${c.id}" aria-label="${E(P('Edit'))} ${E(c.n)}">${I.pen?'<svg viewBox="0 0 24 24">'+I.pen+'</svg>':'✎'}</button></div>`).join('')}</div>`:`<div class="lv2-empty"><div class="lv2-empty-ic">📵</div><b>${P('Add the people who should know')}</b><p class="mute sm">${P('When you press SOS, they get your location and Medical ID as a message, ready to send.')}</p><div class="row" style="justify-content:center"><button class="btn p" data-sx="cadd">＋ ${P('Add contact')}</button>${navigator.contacts&&navigator.contacts.select?`<button class="btn s" data-sx="cpick">📇 ${P('Pick from phone')}</button>`:''}</div></div>`}
   ${cs.length&&navigator.contacts&&navigator.contacts.select?`<div class="lv2-crow"><button class="btn s sm" data-sx="cpick">📇 ${P('Pick from phone')}</button></div>`:''}
   <p class="mute sm" style="margin:12px 0 0">🔒 ${P('Numbers stay on this device. Nothing is sent unless you press SOS and tap Send.')}</p></div>`},after:()=>{}});
SX.act.cadd=([id])=>{const m=SX.me(),c=id?SX.contactsOf(m.id).find(x=>x.id===id):null;
 SX.modal(`<h2>${c?P('Edit contact'):P('Add a contact')}</h2><form class="form lv-form" data-sxf="csave2:${c?c.id:''}" novalidate><label class="full">${P('Name')}<input name="n" required maxlength="40" value="${E(c?c.n:'')}" autocomplete="name" autofocus></label>
  <label>${P('Relation')}<select name="rel">${RELS2.map(r=>`<option value="${r}" ${c&&c.rel===r?'selected':''}>${P(r)}</option>`).join('')}</select></label>
  <label>${P('Mobile number')}<span class="lv-ph"><i>+91</i><input name="ph" inputmode="tel" autocomplete="tel-national" maxlength="16" value="${E((c?c.ph:'').replace(/^\+91/,''))}" placeholder="98765 43210"></span></label>
  <p class="full lv-err" role="alert" hidden></p>
  <div class="full lv-row-end" style="justify-content:space-between">${c?`<button class="btn s" type="button" data-sx="cdel2:${c.id}" style="color:var(--red)">${P('Remove')}</button>`:'<span></span>'}<span style="display:flex;gap:8px"><button class="btn s" type="button" data-sx="closeModal">${P('Cancel')}</button><button class="btn p" type="submit">${c?P('Save'):P('Add')}</button></span></div></form>`,{label:P('Contact')})};
SX.chg.csave2=([id],f)=>{const m=SX.me(),cs=SX.contactsOf(m.id),fd=new FormData(f),err=f.querySelector('.lv-err'),say=t=>{err.textContent=t;err.hidden=false};
 const n=String(fd.get('n')||'').replace(/\s+/g,' ').trim().slice(0,40),rel=String(fd.get('rel')||'Other'),raw=String(fd.get('ph')||'').trim();if(n.length<2)return say(P('Please enter a name.'));
 let ph='';if(raw){ph=SX.phoneNorm(raw);if(!ph||!/^\+\d{10,15}$/.test(ph))return say(P('Please check the mobile number.'))}
 if(id){const c=cs.find(x=>x.id===id);if(c){c.n=n;c.rel=rel;c.ph=ph;if(!ph)c.notify=false}}else cs.push({id:uid('c'),n,rel,ph,notify:!!ph});
 SX.save();SX.closeModal();render();toast(id?P('Contact updated'):P('Contact added'))};
SX.act.cdel2=([id])=>{const m=SX.me();S.contacts[m.id]=SX.contactsOf(m.id).filter(x=>x.id!==id);SX.save();SX.closeModal();render();toast(P('Removed'))};
SX.act.cpick=async()=>{try{const picked=await navigator.contacts.select(['name','tel'],{multiple:true});let n=0;const cs=SX.contactsOf(SX.me().id);
 for(const c of picked){const name=(c.name&&c.name[0]||'').trim().slice(0,40),tel=(c.tel&&c.tel[0]||'').trim();if(!name)continue;const ph=tel?SX.phoneNorm(tel)||'':'';if(cs.some(x=>x.ph&&x.ph===ph))continue;cs.push({id:uid('c'),n:name,rel:'Other',ph,notify:!!ph});n++}
 SX.save();render();toast(n?`${n} ${P('added')}`:P('Nothing added'))}catch(e){if(e&&e.name!=='AbortError'&&e.name!=='InvalidStateError')toast(P('Could not open your contacts'))}};

// ---------------------------------------------------------------- 4. pregnancy mode: theme, sidebar, celebration
I.preg='<path d="M12 4a2 2 0 1 0 0 .1M9.5 8.5h3a3 3 0 0 1 3 3v1.2a4 4 0 0 1 1.3 6.4L15 21H9.5a2 2 0 0 1-2-2V10.5a2 2 0 0 1 2-2z"/><path d="M13 11.5c2.4 0 3.9 1.6 3.9 3.6s-1.5 3.4-3.9 3.4"/>';
const PT={en:'Pregnancy',hi:'गर्भावस्था',te:'గర్భధారణ'},PS2={en:'Pregnancy',hi:'गर्भ',te:'గర్భం'};
const t1=SX.t;SX.t=k=>{if(k==='nav.care'&&pregActive())return PT[S.lang]||PT.en;if(k==='nav.s.care'&&pregActive())return PS2[S.lang]||PS2.en;return t1(k)};
const CARE=SX.G.find(g=>g.k==='care');
function pregNav(){const on=pregActive();CARE.ic=on?'preg':'doc';CARE.tabs=on?['preg','appts','docs','msgs','bill']:['appts','docs','msgs','preg','bill'];document.body.dataset.pregtheme=on?'on':'off';
 const b=$('#nav [data-g="care"]');if(b){const svg=b.querySelector('svg');if(svg)svg.innerHTML=I[CARE.ic];}SX.paintNav()}
SX.pregNav=pregNav;
const sa0=SX.setActive;SX.setActive=id=>{sa0(id);pregNav()};
const pg0=SX.paintGates;SX.paintGates=()=>{pg0();document.body.dataset.pregtheme=pregActive()?'on':'off'};
const ps0=SX.chg.pregsave;SX.chg.pregsave=(a,f)=>{const m=SX.me(),was=SX.pregOn(m);ps0(a,f);if(!was&&SX.pregOn(m)){pregNav();celebrate(m)}};
const po0=SX.act.pregoff2;SX.act.pregoff2=()=>{po0();pregNav()};
function celebrate(m){const w=Math.max(0,Math.floor((Date.now()-new Date(S.preg[m.id].lmp+'T00:00'))/864e5/7));
 const o=document.createElement('div');o.className='lv2-cel';o.setAttribute('role','dialog');o.setAttribute('aria-label',P('A new journey begins'));
 o.innerHTML=`<div class="lv2-cel-sky">${Array.from({length:26},(_,i)=>`<i style="--x:${(i*37)%100}%;--d:${(i%7)*.9}s;--s:${.6+(i%5)*.25}"></i>`).join('')}</div>
  <div class="lv2-cel-card"><div class="lv2-cel-lotus" aria-hidden="true"><svg viewBox="0 0 64 64"><path d="M32 8c6 8 8 16 6 26-2-10-4-18-6-26zM32 8c-6 8-8 16-6 26 2-10 4-18 6-26z" fill="#f6d365"/><path d="M14 22c10 2 17 9 18 20C22 40 15 33 14 22zM50 22c-10 2-17 9-18 20 10-2 17-9 18-20z" fill="#f2b5c4"/><path d="M8 38c9-2 18 1 24 8-9 2-18-1-24-8zM56 38c-9-2-18 1-24 8 9 2 18-1 24-8z" fill="#f28ba8"/><circle cx="32" cy="46" r="4" fill="#fff6"/></svg></div>
   <small>${P('Pregnancy tracking is on for')} ${E(m.name)}</small><h2>${P('A new journey begins')}</h2>
   <p>${w>0?`${P('Week')} ${w}. `:''}${P('Your app now wears a calmer blue, and Pregnancy has its own place in the sidebar: a week-by-week guide, the 3D mother and baby, kick counter, water, symptoms and the signs to call about.')}</p>
   <p class="lv2-cel-note">${P('The baby\u2019s sex is never shown or guessed. Everything here is information to discuss with your doctor.')}</p>
   <button class="btn lv2-cel-btn" type="button">${P('Begin')}</button></div>`;
 document.body.append(o);requestAnimationFrame(()=>o.classList.add('in'));
 const close=()=>{o.classList.remove('in');setTimeout(()=>o.remove(),500);removeEventListener('keydown',esc)};const esc=e=>{if(e.key==='Escape')close()};addEventListener('keydown',esc);o.querySelector('.lv2-cel-btn').onclick=close;o.addEventListener('click',e=>{if(e.target===o)close()})}

// ---------------------------------------------------------------- 5. health card for every member, with our mark
const bloodOf=m=>{const mid=SX.midOf(m.id);return mid.blood||(m.bloodUnknown?P('Not known'):'—')};
const vb=(on,label)=>on?`<span class="lv-ver" title="${E(label)} verified"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l2.4 2.1 3.2-.3.9 3.1 2.8 1.6-1.1 3 1.1 3-2.8 1.6-.9 3.1-3.2-.3L12 22l-2.4-2.1-3.2.3-.9-3.1L2.7 15.5l1.1-3-1.1-3 2.8-1.6.9-3.1 3.2.3z"/><path d="M8.3 12.2l2.5 2.5 5-5" fill="none"/></svg><span>${P('Verified')}</span></span>`:`<span class="lv-unver">${P('Not verified')}</span>`;
SX.cardHTML=m=>{const pv=SX.verified.phone(m);
 return `<div class="lv-card lv2-hc" role="group" aria-label="${E(P('Health card'))}"><div class="lv-card-top"><span class="lv-card-brand">${MARK}<b>the<i>health</i>tracker</b></span><span class="lv-card-k">${P('HEALTH CARD')}</span></div>
  <div class="lv-card-name">${E(m.name)}${m.rel!=='You'?`<small class="lv2-rel">${E(P(m.rel))}</small>`:''}</div>
  <div class="lv-card-grid"><div><small>${P('Age')}</small><b>${m.age||'—'}</b></div><div><small>${P('Sex')}</small><b>${m.sex==='female'?P('Female'):P('Male')}</b></div><div><small>${P('Blood')}</small><b class="lv-blood">${E(bloodOf(m))}</b></div>${m.dob?`<div><small>${P('Born')}</small><b>${E(fmtD(m.dob))}</b></div>`:''}</div>
  <div class="lv-card-ph">${m.ph?`<small>${P('Mobile')}</small><b>${E(phShow(m.ph))}</b>${m.rel==='You'?vb(pv,'Mobile'):''}`:`<small>${P('Mobile')}</small><b class="mute">${P('Not added')}</b>`}</div>
  <div class="lv-card-id"><small>${P('Health tracker ID')}</small><b>${E(m.htid||'')}</b></div></div>`};
const cardReady=m=>!!(m&&m.name&&m.name!=='You'&&m.dob&&m.sexOk);
SX.lvCardTile=m=>{if(m.rel==='You'&&!SX.cardDone(m))return `<div class="card lv-review"><div class="hd"><h3>${P('Finish your health card')}</h3></div><p class="mute sm" style="margin:0 0 10px">${P('Name, date of birth, sex, blood group and mobile number.')}</p><button class="btn p sm" data-sx="lvcardedit">${P('Complete now')}</button></div>`;
 if(m.rel!=='You'&&!cardReady(m))return `<div class="card lv-review"><div class="hd"><h3>${P('Complete')} ${E(SX.poss(m.name))} ${P('health card')}</h3></div><p class="mute sm" style="margin:0 0 10px">${P('Date of birth, sex and blood group give the right body and ranges.')}</p><button class="btn p sm" data-sx="fedit2:${m.id}">${P('Complete now')}</button></div>`;
 return `<button class="card lv-hc" data-sx="lvcardshow:${m.id}" aria-label="${E(P('Open health card'))}"><div class="hd"><h3>${P('Health card')}</h3><span class="mute sm">${P('Tap to open')}</span></div>${SX.cardHTML(m)}</button>`};
SX.act.lvcardshow=([id])=>{const m=SX.member(id)||SX.me(),canVerify=m.rel==='You'&&m.ph&&!SX.verified.phone(m);
 SX.modal(`<div class="lv-reveal"><h2>${P('Health card')}</h2>${SX.cardHTML(m)}
  ${canVerify?`<div class="lv-vbox"><div><b>${P('Verify your mobile number')}</b><small class="mute">${SX.user?P('Get the verified badge and receive SOS confirmations.'):P('Sign in to verify your number and keep your card on every device.')}</small></div>${SX.user?`<button class="btn p sm" data-sx="lvverify:phone">${P('Verify now')}</button>`:`<a class="btn p sm" href="/signin?next=/app">${P('Sign in')}</a>`}</div>`:''}
  <div class="lv-row-end" style="justify-content:space-between"><button class="btn s sm" data-sx="${m.rel==='You'?'lvcardedit':'fedit2:'+m.id}">${P('Edit details')}</button><span style="display:flex;gap:8px"><button class="btn s sm" data-sx="lvcardfull:${m.id}">${P('Show full screen')}</button><button class="btn s" data-sx="closeModal">${P('Close')}</button></span></div></div>`,{label:P('Health card'),cls:'lv-mid'})};
SX.act.lvcardfull=([id])=>{const m=SX.member(id)||SX.me();SX.closeModal(true);const o=document.createElement('div');o.className='lv2-full';o.innerHTML=`<div class="lv2-full-in">${SX.cardHTML(m)}<p class="mute sm">${P('Show this at a hospital or lab desk.')}</p><button class="btn s" type="button">${P('Close')}</button></div>`;o.querySelector('button').onclick=()=>o.remove();o.addEventListener('click',e=>{if(e.target===o)o.remove()});document.body.append(o)};
SX.act.fedit2=([id])=>{go('family');setTimeout(()=>SX.act.fedit([id]),0)};

// ---------------------------------------------------------------- 6. Cards & Insurance
SX.addStrings({'nav.cards':D('Cards & Insurance','कार्ड और बीमा','కార్డులు & బీమా'),'nav.s.cards':D('Cards','कार्ड','కార్డులు'),'tab.wallet':D('Wallet','वॉलेट','వాలెట్'),'tab.insure':D('Insurance','बीमा','బీమా'),'tab.schemes':D('Schemes','योजनाएँ','పథకాలు')});
I.card='<rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M2.5 10h19M6.5 15h4"/>';
SX.G.splice(4,0,{k:'cards',ic:'card',tabs:['wallet','insure','schemes']});
const CT={insurance:{n:'Health insurance',k:'INSURANCE',ic:'🛡️',cls:'ins'},corporate:{n:'Corporate / employer cover',k:'CORPORATE',ic:'🏢',cls:'corp'},scheme:{n:'Government scheme',k:'SCHEME',ic:'🏛️',cls:'gov'},abha:{n:'ABHA',k:'ABHA',ic:'🆔',cls:'abha'},hospital:{n:'Hospital card',k:'HOSPITAL',ic:'🏥',cls:'hosp'},other:{n:'Other card',k:'CARD',ic:'💳',cls:'oth'}};
const cards=()=>S.cards;
const cardOf=id=>cards().find(c=>c.id===id);
const mask=(v,keep=4)=>{v=String(v||'');if(!v)return '—';const d=v.replace(/\s+/g,'');return d.length<=keep?d:'•••• '+d.slice(-keep)};
const abhaFmt=v=>{const d=String(v||'').replace(/\D/g,'');return d.length===14?`${d.slice(0,2)}-${d.slice(2,6)}-${d.slice(6,10)}-${d.slice(10)}`:v||''};
const expiry=c=>{const d=daysTo(c.f.valid_to);if(d==null)return null;if(d<0)return{k:'expired',t:P('Expired')+' '+fmtD(c.f.valid_to),cls:'bad'};if(d<=30)return{k:'soon',t:`${P('Expires in')} ${d} ${P('days')}`,cls:'warn'};return{k:'ok',t:`${P('Valid till')} ${fmtD(c.f.valid_to)}`,cls:'ok'}};
const coveredNames=c=>Array.isArray(c.f.members_covered)?c.f.members_covered.filter(Boolean):[];
const coversMember=(c,m)=>{const ns=coveredNames(c).map(x=>x.toLowerCase());const fn=m.name.toLowerCase(),first=fn.split(' ')[0];return c.member===m.id||ns.some(n=>n===fn||n.split(' ')[0]===first&&first.length>2)||(c.f.holder&&c.f.holder.toLowerCase()===fn)};
const reveal={};
function cardFace(c,opt={}){const T=CT[c.type]||CT.other,f=c.f,ex=expiry(c),num=f.policy_number||f.card_number||f.member_id||f.abha_number||f.number||'',shown=reveal[c.id];
 const title=c.type==='abha'?'ABHA':c.type==='scheme'?(f.scheme_name||P('Government scheme')):c.type==='corporate'?(f.insurer||f.employer||P('Corporate cover')):c.type==='hospital'?(f.hospital||P('Hospital')):(f.insurer||f.title||T.n);
 const sub=c.type==='corporate'?[f.employer,f.plan_name].filter(Boolean).join(' · '):c.type==='abha'?(f.abha_address||''):[f.plan_name,f.tpa?'TPA: '+f.tpa:''].filter(Boolean).join(' · ');
 return `<div class="lv2-card ${T.cls} ${opt.cls||''}" data-cid="${c.id}"><div class="lv2-card-top"><span class="lv2-card-t"><i aria-hidden="true">${T.ic}</i><b>${E(title)}</b></span><span class="lv2-card-k">${E(T.k)}</span></div>
  ${sub?`<div class="lv2-card-sub">${E(sub)}</div>`:''}
  <div class="lv2-card-name">${E(f.holder||c.holder||'')}</div>
  <div class="lv2-card-num"><small>${c.type==='abha'?P('ABHA number'):c.type==='scheme'?P('Card number'):f.policy_number?P('Policy number'):f.member_id?P('Member ID'):P('Number')}</small><b class="lv2-mono ${shown&&String(num).length>16?'long':''}">${E(shown?(c.type==='abha'?abhaFmt(num):num):mask(num))}</b>${num&&!opt.flat?`<button class="lv2-eye" data-sx="creveal:${c.id}" aria-label="${E(P(shown?'Hide number':'Show number'))}">${shown?'🙈':'👁'}</button>`:''}</div>
  <div class="lv2-card-foot">${f.sum_insured?`<span><small>${P('Cover')}</small><b>₹${E(f.sum_insured)}</b></span>`:''}${f.valid_to?`<span><small>${P('Valid till')}</small><b>${E(fmtD(f.valid_to))}</b></span>`:''}${f.employee_id?`<span><small>${P('Employee ID')}</small><b>${E(f.employee_id)}</b></span>`:''}${coveredNames(c).length?`<span><small>${P('Covers')}</small><b>${coveredNames(c).length} ${P('people')}</b></span>`:''}</div>
  ${ex?`<span class="lv2-exp ${ex.cls}">${E(ex.t)}</span>`:''}${c.file?`<span class="lv2-orig" title="${E(P('Original scan kept'))}">📎</span>`:''}</div>`}
SX.act.creveal=([id])=>{reveal[id]=!reveal[id];render()};
let walletSel='';
function walletHTML(){const m=SX.me(),list=cards(),sel=cardOf(walletSel)||null,hc=S.members.filter(cardReady).concat(S.members.filter(x=>!cardReady(x)));
 const picker=`<div class="lv2-wallet" role="list">${S.members.map(x=>`<button class="lv2-slot ${walletSel==='hc:'+x.id?'on':''}" role="listitem" data-sx="wsel:hc:${x.id}">${cardReady(x)?SX.cardHTML(x):`<div class="lv-card lv2-hc lv2-hc-todo"><div class="lv-card-top"><span class="lv-card-brand">${MARK}<b>the<i>health</i>tracker</b></span></div><div class="lv-card-name">${E(x.name)}</div><p>${P('Health card not complete')}</p></div>`}</button>`).join('')}
  ${list.map(c=>`<button class="lv2-slot ${walletSel===c.id?'on':''}" role="listitem" data-sx="wsel:${c.id}">${cardFace(c,{flat:true})}</button>`).join('')}
  <button class="lv2-slot lv2-add" data-sx="caddcard"><div class="lv2-card add"><b>＋</b><span>${P('Add a card')}</span><small>${P('Insurance, ABHA, corporate, scheme')}</small></div></button></div>`;
 let detail='';
 if(walletSel.startsWith('hc:')){const x=SX.member(walletSel.slice(3));if(x)detail=cardReady(x)?`<div class="card wide"><div class="hd"><h3>${E(SX.poss(x.name))} ${P('health card')}</h3><div class="row"><button class="btn s sm" data-sx="${x.rel==='You'?'lvcardedit':'fedit2:'+x.id}">${P('Edit')}</button><button class="btn p sm" data-sx="lvcardfull:${x.id}">${P('Full screen')}</button></div></div><div class="lv2-kv">${[[P('Name'),x.name],[P('Date of birth'),fmtD(x.dob)],[P('Sex'),x.sex==='female'?P('Female'):P('Male')],[P('Blood group'),bloodOf(x)],[P('Mobile'),phShow(x.ph)||'—'],[P('Health tracker ID'),x.htid]].map(([k,v])=>`<div><small>${E(k)}</small><b>${E(v||'—')}</b></div>`).join('')}</div><p class="mute sm" style="margin:10px 0 0">${P('This ID identifies the person inside TheHealthTracker. It is not a government ID. Link an ABHA to connect government health records.')}</p></div>`:`<div class="card wide lv-review"><h3>${P('Complete')} ${E(SX.poss(x.name))} ${P('health card')}</h3><p class="mute sm">${P('Date of birth, sex and blood group are needed.')}</p><button class="btn p sm" data-sx="${x.rel==='You'?'lvcardedit':'fedit2:'+x.id}">${P('Complete now')}</button></div>`}
 else if(sel)detail=cardDetail(sel);
 const cov=coverage();
 return `<div class="card wide lv2-wcard"><div class="hd"><div><h3>${P('Your family\u2019s cards')}</h3><small class="mute">${P('Health cards, insurance, ABHA and scheme cards in one place. Tap a card to open it.')}</small></div><button class="btn p sm" data-sx="caddcard">＋ ${P('Add a card')}</button></div>${picker}</div>
  ${detail}
  <div class="card wide"><div class="hd"><h3>${P('Who is covered')}</h3><button class="btn s sm" data-sx="tab:schemes">${P('Schemes')}</button></div><div class="lv2-cov">${cov.map(r=>`<div class="lv2-covrow ${r.cards.length?'':'gap'}">${SX.avatar(r.m,36)}<div class="grow"><b>${E(r.m.name)}</b><small>${r.cards.length?r.cards.map(c=>E(c.f.insurer||c.f.scheme_name||c.f.employer||CT[c.type].n)).join(' · '):P('No health cover recorded')}</small></div>${r.cards.length?'':`<button class="btn s sm" data-sx="tab:schemes">${P('Options')}</button>`}</div>`).join('')}</div></div>`}
function coverage(){return S.members.map(m=>({m,cards:cards().filter(c=>['insurance','corporate','scheme'].includes(c.type)&&coversMember(c,m)&&(expiry(c)||{}).k!=='expired')}))}
SX.act.wsel=a=>{walletSel=a.join(':');render();setTimeout(()=>{const d=document.querySelector('.lv2-detail');if(d)d.scrollIntoView({behavior:'smooth',block:'nearest'})},50)};
function cardDetail(c){const T=CT[c.type]||CT.other,f=c.f,ex=expiry(c);
 const rows=[[P('Holder'),f.holder],[P('Insurer'),f.insurer],[P('Plan'),f.plan_name],[P('Policy number'),f.policy_number],[P('Member ID'),f.member_id],[P('Employer'),f.employer],[P('Employee ID'),f.employee_id],[P('Sum insured'),f.sum_insured?'₹'+f.sum_insured:''],[P('Valid from'),fmtD(f.valid_from)],[P('Valid till'),fmtD(f.valid_to)],[P('TPA'),f.tpa],[P('TPA helpline'),f.tpa_phone],[P('Insurer helpline'),f.insurer_phone],[P('Scheme'),f.scheme_name],[P('Card number'),f.card_number],[P('ABHA number'),abhaFmt(f.abha_number)],[P('ABHA address'),f.abha_address],[P('Hospital'),f.hospital],[P('Covers'),coveredNames(c).join(', ')],[P('Notes'),f.notes]].filter(r=>r[1]);
 return `<div class="card wide lv2-detail"><div class="hd"><div><h3>${E(f.insurer||f.scheme_name||f.employer||f.hospital||T.n)}</h3><small class="mute">${E(P(T.n))}${ex?` · <span class="lv2-exp inline ${ex.cls}">${E(ex.t)}</span>`:''}</small></div><div class="row"><button class="btn s sm" data-sx="cedit2:${c.id}">${P('Edit')}</button>${c.file?`<button class="btn s sm" data-sx="corig:${c.id}">${P('Original')}</button>`:''}<button class="btn p sm" data-sx="cfull:${c.id}">${P('Full screen')}</button></div></div>
  <div class="lv2-detail-g"><div>${cardFace(c)}</div><div class="lv2-kv">${rows.map(([k,v])=>`<div><small>${E(k)}</small><b>${E(v)}${/helpline/i.test(k)&&/\d{6,}/.test(v)?` <a class="lv2-call" href="tel:${E(String(v).replace(/[^\d+]/g,''))}">${P('Call')}</a>`:''}</b></div>`).join('')}</div></div>
  ${c.type==='insurance'||c.type==='corporate'?`<div class="lv2-tips"><b>${P('At the hospital')}</b><ul class="sx-ul"><li>${P('Show this card and a photo ID at the insurance desk before admission for cashless treatment.')}</li><li>${P('For planned treatment, pre-authorisation usually takes 1–3 working days: start early.')}</li>${f.tpa_phone||f.insurer_phone?`<li>${P('Keep the helpline handy:')} <b>${E(f.tpa_phone||f.insurer_phone)}</b></li>`:''}</ul></div>`:''}
  ${c.type==='abha'?`<p class="mute sm">${P('ABHA (Ayushman Bharat Health Account) lets hospitals and labs share records with your consent through the government\u2019s ABDM network. Direct linking from this app is coming soon; until then your ABHA number is kept here for quick access.')}</p>`:''}
  <div class="lv-row-end" style="justify-content:space-between;margin-top:8px"><small class="mute">${P('Added')} ${E(SX.fmt(c.added))}${c.src==='ai'?' · '+P('read from your photo, checked by you'):''}</small><button class="btn s sm" data-sx="cdelcard:${c.id}" style="color:var(--red)">${P('Remove card')}</button></div></div>`}
SX.act.cfull=([id])=>{const c=cardOf(id);if(!c)return;reveal[id]=true;const o=document.createElement('div');o.className='lv2-full';o.innerHTML=`<div class="lv2-full-in">${cardFace(c,{flat:true})}<p class="mute sm">${P('Show this at the insurance or hospital desk.')}</p>${c.file?`<button class="btn s" data-sx="corig:${c.id}" type="button">${P('Show original')}</button> `:''}<button class="btn s lv2-x" type="button">${P('Close')}</button></div>`;o.querySelector('.lv2-x').onclick=()=>{o.remove();reveal[id]=false};o.addEventListener('click',e=>{if(e.target===o){o.remove();reveal[id]=false}});document.body.append(o)};
SX.act.corig=async([id])=>{const c=cardOf(id);if(!c||!c.file)return;let blob=null;try{blob=await SX.files.get('card:'+c.id)}catch(e){}if(!blob){toast(P('The original is not on this device'));return}
 const u=URL.createObjectURL(blob),isPdf=/pdf/.test(blob.type);const o=document.createElement('div');o.className='lv2-full';o.innerHTML=`<div class="lv2-full-in lv2-orig-in">${isPdf?`<iframe src="${u}" title="${E(P('Original card'))}"></iframe>`:`<img src="${u}" alt="${E(P('Original card'))}">`}<p class="mute sm">${P('Your original, kept privately on this device.')}</p><button class="btn s" type="button">${P('Close')}</button></div>`;o.querySelector('button').onclick=()=>{o.remove();URL.revokeObjectURL(u)};document.body.append(o)};
SX.act.cdelcard=([id])=>{const c=cardOf(id);if(!c)return;SX.modal(`<h2>${P('Remove this card?')}</h2><p class="mute">${P('The card and its original scan are deleted from this device.')}</p><div class="lv-row-end"><button class="btn s" data-sx="closeModal">${P('Keep')}</button><button class="btn red" data-sx="cdelcard2:${id}">${P('Remove')}</button></div>`,{label:P('Remove card')})};
SX.act.cdelcard2=async([id])=>{S.cards=cards().filter(c=>c.id!==id);try{await SX.files.del('card:'+id)}catch(e){}if(walletSel===id)walletSel='';SX.save();SX.closeModal();render();toast(P('Card removed'))};
// add / edit
let cf={type:'insurance',file:null,fields:{},id:'',reading:false,read:null};
SX.act.caddcard=()=>{cf={type:'insurance',file:null,fields:{},id:'',reading:false,read:null};addSheet()};
SX.act.cedit2=([id])=>{const c=cardOf(id);if(!c)return;cf={type:c.type,file:null,fields:Object.assign({},c.f),id:c.id,reading:false,read:null,keepFile:!!c.file};addSheet('form')};
function addSheet(step){step=step||(cf.id?'form':'start');
 const types=Object.entries(CT).map(([k,v])=>`<button class="lv2-type ${cf.type===k?'on':''}" data-sx="ctype:${k}"><i>${v.ic}</i><b>${P(v.n)}</b></button>`).join('');
 const smart=SX.cfg&&SX.cfg.ai&&SX.cfg.ai.engine==='ai';
 let body='';
 if(step==='start')body=`<h2>${P('Add a card')}</h2><p class="mute">${P('Which kind of card is it?')}</p><div class="lv2-types">${types}</div>
  <div class="lv2-addways"><button class="lv2-way" data-sx="cway:photo"><i>📷</i><b>${P('Photo or scan')}</b><small>${smart?P('We read the details for you to check. The original is kept with the card.'):P('Kept with the card; you fill in the details.')}</small></button><button class="lv2-way" data-sx="cway:type"><i>⌨️</i><b>${P('Type the details')}</b><small>${P('No photo needed.')}</small></button></div>
  <input type="file" id="cfile" accept="image/*,application/pdf" capture="environment" hidden>`;
 else body=formHTML();
 SX.modal(body,{label:P('Add a card'),cls:'lv-wide'});if(step==='start'){const fi=$('#cfile');if(fi)fi.onchange=()=>{const f=fi.files&&fi.files[0];if(!f)return;if(f.size>15e6){toast(P('The file is larger than 15 MB'));return}cf.file=f;cf.fields={};if(smart)readCard();else addSheet('form')}}}
SX.act.ctype=([k])=>{cf.type=k;const b=document.querySelector('.lv2-types');if(b)b.querySelectorAll('.lv2-type').forEach(x=>x.classList.toggle('on',x.dataset.sx==='ctype:'+k))};
SX.act.cway=([w])=>{if(w==='photo'){const fi=$('#cfile');if(fi)fi.click()}else{cf.file=null;addSheet('form')}};
async function readCard(){const m=SX.me();if(!S.consent.ai_analysis){const ok=await new Promise(res=>{SX.modal(`<h2>${P('Read the card with smart reading?')}</h2><p>${P('The photo is sent to the TheHealthTracker server and our AI processing partner for this one reading. It is read and discarded; only the details come back to this device, where you check them before saving.')}</p><label class="sx-ck" style="display:flex;gap:8px;align-items:flex-start;margin:10px 0"><input type="checkbox" id="caiok" style="width:auto;margin-top:3px"><span>${P('I allow TheHealthTracker to read my documents.')}</span></label><div class="lv-row-end"><button class="btn s" id="cainot">${P('Type instead')}</button><button class="btn p" id="caigo">${P('Allow and read')}</button></div>`,{label:P('Consent'),sticky:true});$('#cainot').onclick=()=>{SX.closeModal(true);res(false)};$('#caigo').onclick=()=>{if(!$('#caiok').checked){toast(P('Please tick the box first'));return}S.consent.ai_analysis=true;SX.ledger('ai_analysis',true,'Allowed AI analysis of documents',m.id);SX.save();SX.closeModal(true);res(true)}});if(!ok){addSheet('form');return}}
 SX.modal(`<div class="sx-aiwait"><div class="sx-spin"></div><h2>${P('Reading your card…')}</h2><p class="mute">${P('A few seconds. You will check every detail before it is saved.')}</p></div>`,{label:P('Reading'),sticky:true});
 try{const fd=new FormData();fd.append('kind','card');fd.append('consent','1');fd.append('file',cf.file,cf.file.name||'card.jpg');const r=await SX.api('/ai/analyze',{method:'POST',form:fd,silent:true});cf.read=r;
  if(r.readable&&r.fields){const f=r.fields;const F={};for(const k in f)if(f[k]!=null&&f[k]!==''&&!(Array.isArray(f[k])&&!f[k].length))F[k]=f[k];if(F.members_covered&&Array.isArray(F.members_covered))F.members_covered=F.members_covered.join(', ');cf.fields=F;if(r.kind&&CT[r.kind])cf.type=r.kind;toast(P('Card read. Please check each detail.'))}
  else toast((r.warnings&&r.warnings[0])||P('Could not read the card. Fill in the details.'))}
 catch(e){toast(e.offline?P('No connection. Fill in the details; the photo is kept.'):P('Could not read the card right now. Fill in the details; the photo is kept.'))}
 addSheet('form')}
const FIELDS={insurance:[['holder',P('Policy holder')],['insurer',P('Insurer')],['plan_name',P('Plan name')],['policy_number',P('Policy number')],['member_id',P('Member ID')],['sum_insured',P('Sum insured (₹)')],['valid_from',P('Valid from'),'date'],['valid_to',P('Valid till'),'date'],['tpa',P('TPA')],['tpa_phone',P('TPA helpline'),'tel'],['insurer_phone',P('Insurer helpline'),'tel'],['members_covered',P('People covered (comma-separated)'),'full']],
 corporate:[['holder',P('Employee name')],['employer',P('Employer')],['employee_id',P('Employee ID')],['insurer',P('Insurer')],['plan_name',P('Plan / policy name')],['policy_number',P('Policy number')],['member_id',P('Member / UHID')],['sum_insured',P('Sum insured (₹)')],['valid_from',P('Valid from'),'date'],['valid_to',P('Valid till'),'date'],['tpa',P('TPA')],['tpa_phone',P('TPA helpline'),'tel'],['members_covered',P('Dependants covered (comma-separated)'),'full']],
 scheme:[['holder',P('Name on card')],['scheme_name',P('Scheme'),'scheme'],['card_number',P('Card number')],['valid_to',P('Valid till (if printed)'),'date'],['members_covered',P('Family members covered (comma-separated)'),'full']],
 abha:[['holder',P('Name')],['abha_number',P('ABHA number (14 digits)')],['abha_address',P('ABHA address (e.g. name@abdm)')]],
 hospital:[['holder',P('Name')],['hospital',P('Hospital')],['card_number',P('Card / UHID number')],['valid_to',P('Valid till'),'date']],
 other:[['holder',P('Name')],['title',P('Card name')],['number',P('Number')],['valid_to',P('Valid till'),'date']]};
const SCHEMES=['Ayushman Bharat PM-JAY','Ayushman Vay Vandana (70+)','Rajiv Aarogyasri (Telangana)','Dr YSR Aarogyasri (Andhra Pradesh)','EHS (Telangana employees)','CGHS','ECHS','ESIC','Other state scheme'];
function formHTML(){const F=FIELDS[cf.type]||FIELDS.other,f=cf.fields;
 const inp=([k,l,t])=>t==='scheme'?`<label>${E(l)}<input name="${k}" list="schl" value="${E(f[k]||'')}" maxlength="80"><datalist id="schl">${SCHEMES.map(s=>`<option value="${E(s)}">`).join('')}</datalist></label>`:`<label class="${t==='full'?'full':''}">${E(l)}<input name="${k}" type="${t==='date'?'date':t==='tel'?'tel':'text'}" value="${E(f[k]||'')}" maxlength="${t==='full'?200:80}" ${k==='abha_number'?'inputmode="numeric" placeholder="12-3456-7890-1234"':''}></label>`;
 const mem=S.members.map(m=>`<label class="chip"><input type="checkbox" name="mem" value="${m.id}" ${f.member===m.id||(cf.id&&cardOf(cf.id)&&cardOf(cf.id).member===m.id)?'checked':''} hidden onchange="this.classList.toggle('on',this.checked)">${E(m.name)}</label>`).join('');
 return `<h2>${cf.id?P('Edit card'):P('Check the details')}</h2>${cf.read&&cf.read.readable?`<p class="lv2-readok">✦ ${P('Read from your photo. Please check every number before saving.')}</p>`:cf.file?`<p class="mute sm">${P('The photo is kept with the card.')}</p>`:''}
  <div class="lv2-types sm">${Object.entries(CT).map(([k,v])=>`<button class="lv2-type ${cf.type===k?'on':''}" data-sx="ctype2:${k}"><i>${v.ic}</i><b>${P(v.n)}</b></button>`).join('')}</div>
  <form class="form lv-form" data-sxf="csavecard" novalidate>${F.map(inp).join('')}
   <div class="full"><small class="mute" style="display:block;margin-bottom:6px">${P('Whose card is this?')}</small><div class="chips">${mem}</div></div>
   <label class="full">${P('Notes')} <small>${P('optional')}</small><input name="notes" maxlength="160" value="${E(f.notes||'')}"></label>
   <p class="full lv-err" role="alert" hidden></p>
   <div class="full lv-row-end" style="justify-content:space-between"><span>${cf.file||cf.keepFile?'':`<button class="btn s" type="button" data-sx="cway:photo">📷 ${P('Add a photo')}</button><input type="file" id="cfile" accept="image/*,application/pdf" capture="environment" hidden>`}</span><span style="display:flex;gap:8px"><button class="btn s" type="button" data-sx="closeModal">${P('Cancel')}</button><button class="btn p" type="submit">${P('Save card')}</button></span></div></form>`}
SX.act.ctype2=([k])=>{const f=document.querySelector('.sx-modal form');if(f){const fd=new FormData(f);for(const [k2,v] of fd.entries())if(k2!=='mem')cf.fields[k2]=String(v)}cf.type=k;SX.modal(formHTML(),{label:P('Add a card'),cls:'lv-wide'});const fi=$('#cfile');if(fi)fi.onchange=()=>{const x=fi.files&&fi.files[0];if(x){cf.file=x;toast(P('Photo added'))}}};
SX.chg.csavecard=async(a,f)=>{const fd=new FormData(f),err=f.querySelector('.lv-err'),say=t=>{err.textContent=t;err.hidden=false};const o={};
 for(const [k,v] of fd.entries()){if(k==='mem')continue;const s=String(v).trim();if(s)o[k]=s.slice(0,200)}
 const mems=fd.getAll('mem');
 if(!o.holder)return say(P('Please enter the name on the card.'));
 if(cf.type==='abha'){const d=String(o.abha_number||'').replace(/\D/g,'');if(d.length!==14)return say(P('An ABHA number has 14 digits.'));o.abha_number=d}
 if(cf.type==='insurance'&&!o.insurer&&!o.policy_number)return say(P('Add the insurer or the policy number.'));
 if(o.valid_from&&o.valid_to&&o.valid_to<o.valid_from)return say(P('Valid till must be after valid from.'));
 if(o.members_covered)o.members_covered=o.members_covered.split(',').map(x=>x.trim()).filter(Boolean);
 const id=cf.id||uid('cd');let c=cardOf(id);
 if(c){c.f=o;c.type=cf.type;c.member=mems[0]||'';c.updated=Date.now()}else{c={id,type:cf.type,member:mems[0]||'',f:o,file:null,src:cf.read&&cf.read.readable?'ai':'manual',added:Date.now()};S.cards.push(c)}
 if(cf.file){try{await SX.files.put('card:'+id,cf.file);c.file={mime:cf.file.type,name:cf.file.name,size:cf.file.size}}catch(e){toast(P('The photo could not be stored; the details are saved'))}}
 walletSel=id;SX.save();SX.closeModal();if(page!=='wallet')go('wallet');else render();toast(cf.id?P('Card updated'):P('Card added'));SX.notesRefresh()};
SX.reg('wallet',{head:()=>[P('Cards'),P('Every card your family may need at a hospital desk, in one place.')],render:walletHTML,after(){const on=document.querySelector('.lv2-slot.on');if(on&&on.scrollIntoView)try{on.scrollIntoView({block:'nearest',inline:'center'})}catch(e){}}});
// insurance tab
SX.reg('insure',{head:()=>[P('Insurance'),P('Policies, who they cover, and renewals.')],render:()=>{const ins=cards().filter(c=>c.type==='insurance'||c.type==='corporate'),cov=coverage();
 return `<div class="card wide"><div class="hd"><div><h3>${P('Policies')}</h3><small class="mute">${ins.length?`${ins.length} ${P('on file')}`:P('No policy added yet.')}</small></div><button class="btn p sm" data-sx="caddcard">＋ ${P('Add a policy')}</button></div>
  ${ins.length?`<div class="lv2-plist">${ins.map(c=>{const ex=expiry(c);return `<button class="lv2-prow" data-sx="wopen:${c.id}"><div class="lv2-pico">${CT[c.type].ic}</div><div class="grow"><b>${E(c.f.insurer||c.f.employer||CT[c.type].n)}</b><small>${[c.f.plan_name,c.f.policy_number?P('Policy')+' '+mask(c.f.policy_number):'',c.f.sum_insured?'₹'+c.f.sum_insured:''].filter(Boolean).map(E).join(' · ')}</small></div>${ex?`<span class="lv2-exp inline ${ex.cls}">${E(ex.t)}</span>`:''}<span class="lv2-chev">›</span></button>`}).join('')}</div>`:`<div class="lv2-empty"><div class="lv2-empty-ic">🛡️</div><b>${P('Keep every policy where you can find it')}</b><p class="mute sm">${P('Upload a photo of the card or policy page. Renewal reminders appear in notifications 30 days before expiry.')}</p></div>`}</div>
  <div class="card wide"><h3>${P('Who is covered')}</h3><div class="lv2-cov">${cov.map(r=>`<div class="lv2-covrow ${r.cards.length?'':'gap'}">${SX.avatar(r.m,36)}<div class="grow"><b>${E(r.m.name)} <small class="mute">· ${r.m.age} ${P('yrs')}</small></b><small>${r.cards.length?r.cards.map(c=>E(c.f.insurer||c.f.scheme_name||c.f.employer||CT[c.type].n)+(c.f.sum_insured?' · ₹'+E(c.f.sum_insured):'')).join(' · '):P('No cover recorded: check the schemes you may be eligible for')}</small></div>${r.cards.length?'':`<button class="btn s sm" data-sx="tab:schemes">${P('Schemes')}</button>`}</div>`).join('')}</div><p class="mute sm" style="margin:10px 0 0">${P('A person counts as covered when their name is on a card or the card is marked as theirs.')}</p></div>
  ${SX.lvSoon(P('Compare and buy cover'),P('Comparing policies and applying inside the app will be done with an IRDAI-licensed partner, so advice is regulated. Until then, use the coverage view to spot gaps and discuss them with an advisor.'),'📋')}`},after:()=>{}});
SX.act.wopen=([id])=>{walletSel=id;go('wallet')};
// schemes tab
const STATES=['Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Delhi','Goa','Gujarat','Haryana','Himachal Pradesh','Jammu & Kashmir','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal','Other'];
const SCHEME_INFO=[
 {id:'pmjay',n:'Ayushman Bharat PM-JAY',who:'Families listed under the scheme (based on the national socio-economic survey and state lists). Cover of ₹5 lakh per family per year for admissions at empanelled hospitals.',check:'Check "Am I eligible" on the official site with your mobile number or ration card.',url:'https://beneficiary.nha.gov.in/',fit:m=>true,tag:P('National')},
 {id:'avv',n:'Ayushman Vay Vandana card (70+)',who:'Every citizen aged 70 or above, whatever the family income. ₹5 lakh per year on top of any other cover.',check:'Apply on the PM-JAY beneficiary portal or the Ayushman app with Aadhaar.',url:'https://beneficiary.nha.gov.in/',fit:m=>m.age>=70,tag:P('Seniors')},
 {id:'aarogyasri',n:'Rajiv Aarogyasri (Telangana)',who:'Telangana families with a white (BPL) ration card or a low annual income as set by the state.',check:'Eligibility and the current cover limit are on the state portal; hospitals have an Aarogyasri help desk.',url:'https://rajivaarogyasri.telangana.gov.in/',state:'Telangana',fit:m=>true},
 {id:'ysr',n:'Dr YSR Aarogyasri (Andhra Pradesh)',who:'Andhra Pradesh families within the state\u2019s income limit.',check:'Check on the state portal or at a network hospital help desk.',url:'https://www.ysraarogyasri.ap.gov.in/',state:'Andhra Pradesh',fit:m=>true},
 {id:'ehs',n:'EHS (Telangana employees and pensioners)',who:'Telangana state government employees, pensioners and their dependants.',check:'Your department issues the EHS card.',url:'https://ehf.telangana.gov.in/',state:'Telangana',fit:m=>m.age>=18},
 {id:'cghs',n:'CGHS',who:'Central government employees, pensioners and dependants in CGHS cities.',check:'Through your department or the CGHS portal.',url:'https://cghs.gov.in/',fit:m=>m.age>=18},
 {id:'esic',n:'ESIC',who:'Employees in covered establishments earning up to the ESI wage ceiling, and their families.',check:'Your employer registers you; check your ESIC insurance number.',url:'https://www.esic.gov.in/',fit:m=>m.age>=18&&m.age<=65},
 {id:'echs',n:'ECHS',who:'Ex-servicemen pensioners and dependants.',check:'Through the ECHS polyclinic.',url:'https://echs.gov.in/',fit:m=>m.age>=18}];
SX.reg('schemes',{head:()=>[P('Government schemes'),P('Cover you may already be entitled to.')],render:()=>{const st=S.state||'';
 const list=SCHEME_INFO.filter(s=>!s.state||s.state===st||!st);const gaps=coverage().filter(r=>!r.cards.length).map(r=>r.m);
 return `<div class="card wide"><div class="hd"><h3>${P('Your state')}</h3><select data-sxc="setstate" aria-label="${E(P('State'))}"><option value="">${P('Choose')}</option>${STATES.map(s=>`<option ${st===s?'selected':''}>${s}</option>`).join('')}</select></div><p class="mute sm" style="margin:0">${P('State schemes differ. Choose your state to see the ones that apply.')}${gaps.length?` <b>${gaps.map(m=>E(m.name)).join(', ')}</b> ${gaps.length>1?P('have'):P('has')} ${P('no cover recorded, so these are worth checking.')}`:''}</p></div>
  <div class="lv2-schemes">${list.map(s=>{const fits=S.members.filter(s.fit);return `<div class="card lv2-scheme"><div class="hd"><h3>${E(s.n)}</h3>${s.tag?`<span class="lv-tag">${E(s.tag)}</span>`:s.state?`<span class="lv-tag">${E(s.state)}</span>`:''}</div><p>${E(s.who)}</p><p class="mute sm">${E(s.check)}</p>${fits.length&&fits.length<S.members.length?`<p class="sm"><b>${P('May apply to:')}</b> ${fits.map(m=>E(m.name)).join(', ')}</p>`:''}<div class="row"><a class="btn s sm" href="${s.url}" target="_blank" rel="noopener">${P('Official site')} ↗</a><button class="btn s sm" data-sx="cschemeadd:${E(s.n)}">${P('I have this card')}</button></div></div>`}).join('')}</div>
  <p class="sx-disc">${P('Scheme rules and limits change. The official site is always the final word; the app only helps you spot what to check.')}</p>`},after:()=>{}});
SX.chg.setstate=(a,el)=>{S.state=el.value;SX.save();render()};
SX.act.cschemeadd=([n])=>{cf={type:'scheme',file:null,fields:{scheme_name:n,holder:you().name},id:'',reading:false,read:null};addSheet('form')};

// ---------------------------------------------------------------- 7. notification centre + medicine reminders
I.bell='<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20a2 2 0 0 0 4 0"/>';
const slotMin=sl=>{const t=(S.rem.times||{})[sl]||{Morning:'08:00',Afternoon:'14:00',Evening:'18:00',Night:'21:00'}[sl];const [h,m]=t.split(':').map(Number);return h*60+m};
const fmtSlot=sl=>{const t=(S.rem.times||{})[sl]||'';const [h,m]=t.split(':').map(Number);return `${h%12||12}:${String(m).padStart(2,'0')} ${h>=12?'PM':'AM'}`};
const nowMin=()=>{const d=new Date();return d.getHours()*60+d.getMinutes()};
function notes(){const out=[],t=SX.today();
 S.members.forEach(m=>{const plan=SX.dosePlan(m);['Morning','Afternoon','Evening','Night'].forEach(sl=>{const due=plan.filter(p=>p.w===sl&&!p.done&&!S.rem.off[p.x.id]);if(!due.length)return;const late=nowMin()>=slotMin(sl);if(!late)return;
   out.push({id:`dose:${m.id}:${t}:${sl}`,k:'dose',ic:'💊',t:`${E(m.name)}: ${due.map(p=>E(p.x.n)).join(', ')}`,s:`${P(sl)} ${P('dose')} · ${fmtSlot(sl)}`,go:'rx',m:m.id,acts:[['dosedone:'+m.id+':'+sl,P('Mark taken')]]})});
  (S.meds[m.id]||[]).forEach(x=>{if(x.left!=null&&x.left<=7)out.push({id:`low:${x.id}:${t}`,k:'low',ic:'📦',t:`${E(x.n)} ${P('is running low')}`,s:`${x.left} ${P('left')} · ${E(m.name)}`,go:'rx',m:m.id})});
  (S.appts[m.id]||[]).forEach(a=>{const d=daysTo(a.date);if(d!=null&&d>=0&&d<=7)out.push({id:`visit:${a.id}:${t}`,k:'visit',ic:'📅',t:`${E(a.dn||P('Doctor visit'))} · ${E(m.name)}`,s:d===0?P('Today')+(a.time?' · '+a.time:''):d===1?P('Tomorrow'):`${P('In')} ${d} ${P('days')}`,go:'appts',m:m.id})});
  if(SX.pregOn(m)){const w=Math.max(0,Math.floor((Date.now()-new Date(S.preg[m.id].lmp+'T00:00'))/864e5/7));out.push({id:`preg:${m.id}:${w}`,k:'preg',ic:'🤰',t:`${P('Week')} ${w} · ${E(m.name)}`,s:P('See this week\u2019s guide and trackers'),go:'preg',m:m.id})}});
 cards().forEach(c=>{const ex=expiry(c);if(!ex||ex.k==='ok')return;out.push({id:`card:${c.id}:${ex.k}:${t.slice(0,7)}`,k:'card',ic:'🛡️',t:`${E(c.f.insurer||c.f.scheme_name||c.f.employer||CT[c.type].n)} · ${E(ex.t)}`,s:ex.k==='expired'?P('Renew it to stay covered'):P('Renew before it lapses'),go:'wallet',cid:c.id})});
 const y=you();if(y&&y.ph&&!SX.verified.phone(y)&&SX.user)out.push({id:'verify:phone',k:'verify',ic:'✅',t:P('Verify your mobile number'),s:P('Get the verified badge'),act:'lvverify:phone'});
 if(y&&!(SX.contactsOf(y.id)||[]).some(c=>c.ph))out.push({id:'contacts:none',k:'setup',ic:'🆘',t:P('Add an emergency contact'),s:P('SOS can message them with your location'),go:'contacts',m:y.id});
 return out.filter(n=>!(S.notes.snooze[n.id]>Date.now()))}
SX.notes=notes;
function unseen(){return notes().filter(n=>!S.notes.seen[n.id]).length}
function bell(){let b=$('#sxBell');if(!b){const tb=$('.topb');if(!tb)return;b=document.createElement('button');b.id='sxBell';b.className='sx-lang lv2-bell';b.setAttribute('aria-label',P('Notifications'));b.innerHTML=`<svg viewBox="0 0 24 24">${I.bell}</svg><em hidden></em>`;const th=tb.querySelector('.theme');tb.insertBefore(b,th||null);b.onclick=()=>openNotes()}
 const n=unseen(),em=b.querySelector('em');em.hidden=!n;em.textContent=n>9?'9+':n}
SX.notesRefresh=bell;
function openNotes(){const list=notes();list.forEach(n=>S.notes.seen[n.id]=Date.now());SX.save();bell();
 SX.modal(`<div class="lv2-notes"><div class="hd"><h2 style="margin:0">${P('Notifications')}</h2><button class="btn s sm" data-sx="remset">${P('Reminder settings')}</button></div>
  ${list.length?list.map(n=>`<div class="lv2-note"><i>${n.ic}</i><div class="grow"><b>${n.t}</b><small>${n.s}</small></div><div class="lv2-note-a">${(n.acts||[]).map(([a,l])=>`<button class="btn p sm" data-sx="${a}">${l}</button>`).join('')}<button class="btn s sm" data-sx="${n.act?n.act:'nopen:'+(n.go||'dash')+':'+(n.m||'')+':'+(n.cid||'')}">${n.act?P('Verify'):P('Open')}</button><button class="lv2-ib" data-sx="nsnooze:${n.id}" aria-label="${E(P('Snooze'))}">💤</button></div></div>`).join(''):`<div class="lv2-empty"><div class="lv2-empty-ic">🔔</div><b>${P('All clear')}</b><p class="mute sm">${P('Dose reminders, renewals and visits show up here.')}</p></div>`}
  <p class="mute sm" style="margin:12px 0 0">${'Notification' in window?(Notification.permission==='granted'?P('Phone notifications are on while the app is open or installed.'):P('Turn on phone notifications in Reminder settings to be alerted when the app is in the background.')):P('This browser cannot show notifications.')}</p></div>`,{label:P('Notifications')})}
SX.act.nopen=([g,m,cid])=>{SX.closeModal();if(m&&SX.member(m)&&m!==S.active)SX.setActive(m);if(cid)walletSel=cid;go(g)};
SX.act.nsnooze=([id])=>{S.notes.snooze[id]=Date.now()+60*60e3;SX.save();openNotes();toast(P('Snoozed for an hour'))};
SX.act.dosedone=([mid,sl])=>{const m=SX.member(mid);if(!m)return;SX.dosePlan(m).filter(p=>p.w===sl&&!p.done).forEach(p=>{S.taken[m.id].s[p.k]=1;if(p.x.left!=null&&p.x.left>0)p.x.left--});SX.save();openNotes();if(page==='rx'||page==='dash')render();SX.paintNav()};
// reminder settings
SX.act.remset=()=>{const list=S.members.flatMap(m=>(S.meds[m.id]||[]).map(x=>({m,x})));const perm='Notification' in window?Notification.permission:'none';
 SX.modal(`<h2>${P('Medicine reminders')}</h2><div class="row between" style="margin:0 0 12px"><div><b>${P('Remind me')}</b><small class="mute" style="display:block">${P('At the times below, for every medicine that is on')}</small></div><label class="sx-sw"><input type="checkbox" data-sxc="remtog2" ${S.rem.on?'checked':''}><i></i></label></div>
  <div class="lv2-times">${['Morning','Afternoon','Evening','Night'].map(sl=>`<label>${P(sl)}<input type="time" data-sxc="remtime:${sl}" value="${E(S.rem.times[sl])}"></label>`).join('')}</div>
  <div class="lv2-perm">${perm==='granted'?`<span class="lv-ver"><span>✓</span> ${P('Phone notifications on')}</span> <button class="btn s sm" data-sx="remtest">${P('Send a test')}</button>`:perm==='denied'?`<span class="lv2-warn">${P('Notifications are blocked for this site in your browser settings.')}</span>`:perm==='none'?`<span class="mute sm">${P('This browser cannot show notifications.')}</span>`:`<button class="btn p sm" data-sx="remperm">🔔 ${P('Allow phone notifications')}</button>`}</div>
  ${list.length?`<h4 class="sx-h4">${P('Per medicine')}</h4><div class="lv2-medlist">${list.map(({m,x})=>`<label class="row"><div class="grow"><b>${E(x.n)}</b><small class="mute">${E(m.name)} · ${x.when.map(w=>P(w)).join(', ')}</small></div><span class="sx-sw"><input type="checkbox" data-sxc="remmed:${x.id}" ${S.rem.off[x.id]?'':'checked'}><i></i></span></label>`).join('')}</div>`:`<p class="mute sm">${P('Add medicines to set reminders for them.')}</p>`}
  <p class="mute sm" style="margin:10px 0 0">${P('Reminders fire while TheHealthTracker is open in a tab or installed on your phone. Server push for a closed app is coming soon.')}</p>
  <div class="lv-row-end"><button class="btn p" data-sx="closeModal">${P('Done')}</button></div>`,{label:P('Reminders')})};
SX.chg.remtog2=(a,el)=>{S.rem.on=el.checked;SX.save();if(el.checked&&'Notification' in window&&Notification.permission==='default')SX.act.remperm()};
SX.chg.remtime=([sl],el)=>{if(/^\d\d:\d\d$/.test(el.value)){S.rem.times[sl]=el.value;SX.save()}};
SX.chg.remmed=([id],el)=>{if(el.checked)delete S.rem.off[id];else S.rem.off[id]=true;SX.save()};
SX.act.remperm=async()=>{try{const r=await Notification.requestPermission();if(r==='granted'){toast(P('Phone notifications on'));notify(P('Reminders are on'),P('You will be reminded at your medicine times.'))}else toast(P('Notifications not allowed'))}catch(e){}SX.act.remset()};
SX.act.remtest=()=>notify(P('Test reminder'),P('This is how a medicine reminder looks.'));
async function notify(title,body,tag){if(!('Notification' in window)||Notification.permission!=='granted')return;try{const reg=navigator.serviceWorker&&await navigator.serviceWorker.getRegistration();if(reg&&reg.showNotification){reg.showNotification(title,{body,tag,icon:'/brand/png/user-icon-192.png',badge:'/brand/png/user-icon-192.png',renotify:!!tag});return}}catch(e){}try{new Notification(title,{body,tag,icon:'/brand/png/user-icon-192.png'})}catch(e){}}
function remTick2(){if(!S.rem.on)return;const t=SX.today(),nm=nowMin();
 S.members.forEach(m=>{['Morning','Afternoon','Evening','Night'].forEach(sl=>{const key=m.id+t+sl,at=slotMin(sl);if(nm<at||nm>at+45||S.rem.sent[key])return;const due=SX.dosePlan(m).filter(p=>p.w===sl&&!p.done&&!S.rem.off[p.x.id]);if(!due.length)return;S.rem.sent[key]=1;SX.save();
  const msg=`${m.name}: ${due.map(p=>p.x.n).join(', ')}`;toast('⏰ '+msg);notify(P(sl)+' '+P('medicines'),msg,'dose-'+key);bell()})})}
setInterval(remTick2,30000);setTimeout(remTick2,3000);
// replace the old reminders card on My medicines
SX.extend('rx',{after(){return `<div class="card wide lv2-remcard"><div class="hd"><div><h3>${P('Reminders')}</h3><small class="mute">${S.rem.on?`${P('On')} · ${['Morning','Afternoon','Evening','Night'].map(sl=>P(sl)+' '+fmtSlot(sl)).join(' · ')}`:P('Off')}</small></div><button class="btn s sm" data-sx="remset">${P('Settings')}</button></div></div>`}});
const b0=SX.boot;SX.boot=()=>{b0();bell();pregNav()};
const r0=render;render=function(...a){const r=r0.apply(this,a);bell();return r};
}
