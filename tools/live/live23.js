// ===================== live layer 23: lab trends — every test over the years, with its healthy band =====================
{
const P=SX.p,S=SX.S;
const LABS=SX.LABS;
const fmtD=d=>new Date(d+'T00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
const fmtN=(v,d)=>(+v).toLocaleString('en-IN',{maximumFractionDigits:d==null?1:d,minimumFractionDigits:0});
const series=(m,key)=>(S.results[m.id]||[]).filter(x=>x.k==='lab'&&x.key===key&&x.val!=null&&x.date).slice().sort((a,b)=>a.date.localeCompare(b.date));
const keysWithHistory=m=>{const c={};(S.results[m.id]||[]).forEach(x=>{if(x.k==='lab'&&LABS[x.key])c[x.key]=(c[x.key]||0)+1});return Object.keys(c).filter(k=>c[k]>=2).sort((a,b)=>{const sa=SX.labStatus(series(m,a).slice(-1)[0],m),sb=SX.labStatus(series(m,b).slice(-1)[0],m);return (sb.s!=='in')-(sa.s!=='in')||c[b]-c[a]})};
SX.labTrendKeys=keysWithHistory;

// ---------------------------------------------------------------- the drawing (pure SVG; works offline, prints, copies)
function scale(vals,r,top,bottom){const all=vals.concat(r.filter(x=>x!=null));const lo=Math.min(...all),hi=Math.max(...all);const span=(hi-lo)||Math.abs(hi)*.2||1;const mn=lo-span*.18,mx=hi+span*.18;return v=>top+(bottom-top)*(1-(v-mn)/(mx-mn))}
function spark(pts,r,w,h){if(pts.length<2)return '';const y=scale(pts.map(p=>+p.val),r,4,h-4);const x=i=>4+(w-8)*i/(pts.length-1);
 const band=r[0]!=null||r[1]!=null?`<rect x="0" y="${r[1]!=null?y(r[1]):0}" width="${w}" height="${Math.max(0,(r[0]!=null?y(r[0]):h)-(r[1]!=null?y(r[1]):0))}" rx="3" fill="var(--green)" opacity=".12"/>`:'';
 const d=pts.map((p,i)=>(i?'L':'M')+x(i).toFixed(1)+' '+y(+p.val).toFixed(1)).join(' ');const last=pts[pts.length-1];
 return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true">${band}<path d="${d}" fill="none" stroke="var(--blue)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${x(pts.length-1).toFixed(1)}" cy="${y(+last.val).toFixed(1)}" r="3.2" fill="var(--blue)"/></svg>`}
function chart(pts,r,L,w,h){const padL=40,padR=14,padT=18,padB=28;const y=scale(pts.map(p=>+p.val),r,padT,h-padB);const t0=new Date(pts[0].date+'T00:00').getTime(),t1=new Date(pts[pts.length-1].date+'T00:00').getTime(),span=Math.max(t1-t0,864e5*30);const x=p=>padL+(w-padL-padR)*((new Date(p.date+'T00:00').getTime()-t0)/span);
 const y0=r[1]!=null?y(r[1]):padT,y1=r[0]!=null?y(r[0]):h-padB;
 const band=r[0]!=null||r[1]!=null?`<rect x="${padL}" y="${y0}" width="${w-padL-padR}" height="${Math.max(0,y1-y0)}" fill="var(--green)" opacity=".12"/>${r[1]!=null?`<text x="${w-padR}" y="${y0-4}" text-anchor="end" font-size="10" fill="var(--mute)">${P('upper')} ${fmtN(r[1],L.d)}</text>`:''}${r[0]!=null?`<text x="${w-padR}" y="${y1+12}" text-anchor="end" font-size="10" fill="var(--mute)">${P('lower')} ${fmtN(r[0],L.d)}</text>`:''}`:'';
 const d=pts.map((p,i)=>(i?'L':'M')+x(p).toFixed(1)+' '+y(+p.val).toFixed(1)).join(' ');
 const dots=pts.map(p=>{const st=SX.labStatus(p,SX.me());return `<circle cx="${x(p).toFixed(1)}" cy="${y(+p.val).toFixed(1)}" r="4.5" fill="${st.s==='in'?'var(--green)':st.mild?'var(--amber)':'var(--red)'}" stroke="var(--card)" stroke-width="2"/><text x="${x(p).toFixed(1)}" y="${(y(+p.val)-9).toFixed(1)}" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">${fmtN(p.val,L.d)}</text>`}).join('');
 const years=[...new Set(pts.map(p=>p.date.slice(0,4)))];const ticks=years.map(yr=>{const first=pts.find(p=>p.date.startsWith(yr));return `<text x="${x(first).toFixed(1)}" y="${h-8}" text-anchor="${years.length===1?'middle':'start'}" font-size="10.5" fill="var(--mute)">${yr}</text>`}).join('');
 const ax=`<line x1="${padL}" y1="${h-padB}" x2="${w-padR}" y2="${h-padB}" stroke="var(--line2)"/><text x="${padL-6}" y="${padT+4}" text-anchor="end" font-size="10" fill="var(--mute)">${L.u}</text>`;
 return `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" role="img" aria-label="${E(L.n)} ${P('over time')}">${band}${ax}<path d="${d}" fill="none" stroke="var(--blue)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>${dots}${ticks}</svg>`}

// ---------------------------------------------------------------- the Trends card on Lab results
function tile(m,key){const pts=series(m,key),L=LABS[key],last=pts[pts.length-1],prev=pts[pts.length-2],st=SX.labStatus(last,m),r=SX.labRange(key,m);
 const d=+last.val-+prev.val,arrow=Math.abs(d)<1e-9?'→':d>0?'↑':'↓';
 return `<button class="lv23-tile ${st.s}" data-sx="labtrend:${E(key)}"><div class="t"><b>${E(L.n)}</b><small>${pts.length} ${P('results')} · ${P('since')} ${pts[0].date.slice(0,4)}</small></div><div class="v"><b>${fmtN(last.val,L.d)}<small>${E(L.u)}</small></b><em class="${st.s}">${arrow} ${fmtN(Math.abs(d),L.d)} ${P('vs')} ${fmtD(prev.date).replace(/ \d{4}$/,'')}</em></div>${spark(pts,r,150,40)}</button>`}
SX.extend('tests',{before(){const m=SX.me(),keys=keysWithHistory(m);if(!keys.length)return '';
 return `<div class="card wide lv23-card"><div class="hd"><div><h3>${P('Trends')}</h3><small class="mute">${P('Each test over the years, with its healthy band. Tap one to see every value.')}</small></div></div><div class="lv23-grid">${keys.map(k=>tile(m,k)).join('')}</div></div>`}});

// ---------------------------------------------------------------- the full chart
let yearSel='all';
function open(key){const m=SX.me(),L=LABS[key];if(!L)return;const all=series(m,key);const years=[...new Set(all.map(p=>p.date.slice(0,4)))].reverse();if(yearSel!=='all'&&!years.includes(yearSel))yearSel='all';
 const pts=yearSel==='all'?all:all.filter(p=>p.date.startsWith(yearSel));const r=SX.labRange(key,m),last=all[all.length-1],st=SX.labStatus(last,m);
 const w=Math.min(560,Math.max(300,(document.documentElement.clientWidth||360)-56));
 SX.modal(`<div class="lv23-m"><div class="lv23-mh"><div><h2>${E(L.n)}</h2><p class="mute sm">${E(L.what||'')}</p></div><span class="lv23-badge ${st.s}">${st.s==='in'?P('In range'):st.s==='high'?P('Above range'):P('Below range')}</span></div>
  <div class="lv23-years">${[['all',P('All years')],...years.map(y=>[y,y])].map(([k,t])=>`<button class="chip ${yearSel===k?'on':''}" data-sx="labyear:${k}:${E(key)}">${t}</button>`).join('')}</div>
  <div class="lv23-chart">${pts.length>=2?chart(pts,r,L,w,230):`<p class="mute sm">${P('Only one result in this year.')}</p>`}</div>
  <div class="lv23-list">${pts.slice().reverse().map(p=>{const s=SX.labStatus(p,m);return `<div class="lv23-row"><span class="lv23-dot ${s.s}"></span><b>${fmtN(p.val,L.d)} <small>${E(L.u)}</small></b><small class="mute">${fmtD(p.date)}</small></div>`}).join('')}</div>
  <p class="mute sm">${st.s==='high'?E(L.hi||''):st.s==='low'?E(L.lo||''):P('Within the usual range. A normal result does not rule out a problem if you feel unwell.')}</p>
  <div class="lv-row-end"><button class="btn s" data-sx="askdoc:${E(last.id)}">${P('Discuss with your doctor')}</button><button class="btn p" data-sx="closeModal">${P('Close')}</button></div></div>`,{label:L.n,cls:'lv-wide'})}
SX.act.labtrend=([key])=>{yearSel='all';open(key)};
SX.act.labyear=([y,key])=>{yearSel=y;open(key)};
SX.labTrendChart=(m,key)=>{const pts=series(m,key);return pts.length>=2?chart(pts,SX.labRange(key,m),LABS[key],560,230):''};
}
