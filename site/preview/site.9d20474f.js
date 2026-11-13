
(()=>{
const R=matchMedia('(prefers-reduced-motion: reduce)').matches;
const $=s=>document.querySelector(s);
const C=v=>v<0?0:v>1?1:v, seg=(p,a,b)=>C((p-a)/(b-a)), mix=(a,b,t)=>a+(b-a)*t;
const E=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2, EO=t=>1-Math.pow(1-t,3);
let W=innerWidth,H=innerHeight,mob=W<560||(W<900&&H>W);
document.getElementById('yr').textContent=new Date().getFullYear();

/* words: wrap each word; *word* marks the highlighted close */
const wt=$('#wtxt');const WT_EN=wt.textContent.trim();wt.innerHTML=wt.textContent.trim().split(/\s+/).map(w=>w.startsWith('*')?`<span class="hl">${w.replace(/\*/g,'')}</span>`:`<span>${w}</span>`).join(' ');
let words=[...wt.children];words.forEach(w=>w.setAttribute('aria-hidden','true'));

/* scene registry: each gets smoothed progress 0..1 */
const fx={
 hero(p){
  const t1=E(seg(p,0,.42)), t2=E(seg(p,.05,.62));
  $('#htxt').style.cssText=`opacity:${1-seg(p,.04,.3)};transform:translateY(${-t1*14}vh) scale(${1-t1*.08});filter:blur(${seg(p,.08,.3)*8}px)`;
  const hp=$('#hphone'),ph=$('#hph');
  const y=mix(mob?78:66,0,t2), rx=mix(48,0,t2), sc=mix(.86,1,t2);
  hp.style.transform=`translate(-50%,calc(-50% + ${y}vh + 26px))`;
  ph.style.transform=`rotateX(${rx}deg) scale(${sc})`;
  const r=hp.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,w=r.width;
  [['#hc1',-1,-.26,.5],['#hc2',1,.02,.58],['#hc3',-1,.28,.66]].forEach(([id,s,dy,st])=>{
   const t=EO(seg(p,st,st+.18)),el=$(id),ew=el.offsetWidth;
   const gap=mob?-.18:.12, x=s<0?cx-w/2-ew-w*gap+ew*(mob?.25:0):cx+w/2+w*gap-ew*(mob?.25:0);
   el.style.left=Math.max(10,Math.min(W-ew-10,x))+'px';el.style.top=(cy+dy*r.height-28)+'px';
   el.style.opacity=t;el.style.transform=`translateY(${(1-t)*40}px) scale(${mix(.8,1,t)})`;el.style.filter=`blur(${(1-t)*10}px)`});
  $('#hint').style.visibility=p>.02?'hidden':'visible';
  $('#hwhite').style.opacity=E(seg(p,.86,1));
 },
 words(p){const n=words.length;words.forEach((w,i)=>{w.style.opacity=.14+.86*seg(p,i/n*.78+.04,i/n*.78+.1)})},
 body(p){
  const bt=$('#btitle'),q=seg(p,.17,.25);bt.style.opacity=1-q;bt.style.transform=`translateY(${-q*40}px)`;
  const a=EO(seg(p,0,.16)), z=E(seg(p,.72,.94));
  const bb=$('#bbox');bb.style.opacity=a;
  bb.style.transform=`translate(-50%,-50%) translateY(${mix(8,0,a)}vh) scale(${mix(.86,1,a)*mix(1,mob?1.7:2.1,z)})`;
  bb.style.transformOrigin=`50% ${mix(50,36,z)}%`;
  for(let i=1;i<=4;i++){const st=.18+i*.1,t=EO(seg(p,st,st+.1)),f=1-seg(p,.7,.78);
   const ln=document.getElementById('ln'+i),L=ln.getTotalLength();ln.style.strokeDasharray=`${L}`;ln.style.strokeDashoffset=L*(1-t);ln.style.opacity=f;
   const dt=document.getElementById('dt'+i);dt.setAttribute('r',9*t);dt.style.opacity=f;
   const c=document.getElementById('cl'+i);c.style.opacity=t*f;c.style.transform=`translateY(${(1-t)*18}px) scale(${mix(.85,1,t)})`;c.style.translate='0 0';const cr=c.getBoundingClientRect();let dx=0;if(cr.right>W-8)dx=W-8-cr.right;if(cr.left+dx<8)dx=8-cr.left;c.style.translate=dx+'px 0'}
  const be=$('#bend'),t=EO(seg(p,.84,.96));be.style.opacity=t;be.style.transform=`translateY(${(1-t)*30}px)`;
 },
 zoom(p){
  const ph=$('#zph'),ref=ph.offsetHeight,rw=ref*300/661;
  const S0=Math.max(W/(rw*.934),H/(ref*.934))*1.04;
  const t=E(seg(p,.05,.55)), m=E(seg(p,.55,.78));
  const s=mix(S0,mob?.6:1,t);
  const dx=mob?0:mix(0,Math.min(W*.22,300),m), dy=mix(mob?0:0,mob?H*.19:0,m)+mix(ref*.3*S0,0,t);
  ph.style.transform=`translate(calc(-50% + ${dx}px),calc(-50% + ${dy}px)) scale(${s})`;
  const tx=$('#ztxt');tx.style.opacity=m;tx.style.marginTop=(1-m)*30+'px';
 },
 story(p){
  const i=Math.min(3,Math.floor(p*4*.999));
  document.querySelectorAll('#stxt .stp').forEach((s,k)=>s.classList.toggle('on',k===i));
  document.querySelectorAll('#svis .sc').forEach((s,k)=>s.classList.toggle('on',k===i));{const cv=document.querySelector('.camv');if(cv)cv.style.setProperty('--h',cv.clientHeight+'px')}
  document.querySelectorAll('#bars i').forEach((b,k)=>b.style.transform=`scaleX(${C(p*4-k)})`);
 },
 gal(p,el){const tr=$('#track');tr.style.transform=`translateX(${-E(seg(p,.04,.96))*Math.max(0,tr.scrollWidth-W)}px)`},
 sos(p){
  const h=seg(p,.12,.48), done=p>.5;
  $('#sring').style.strokeDashoffset=289*(1-h);
  $('#score').style.transform=`scale(${done?1:mix(1,.93,h)})`;
  $('#stxtb').textContent=done?'Help':'SOS';
  const b=EO(seg(p,.5,.7));
  [1,2,3].forEach(k=>{const r=$('#rg'+k);const q=C(b*1.4-(k-1)*.2);r.style.transform=`scale(${1+q*(1.2+k*.7)})`;r.style.opacity=done?(1-q)*.9:.35});
  $('#sglow').style.opacity=mix(.25,1,b);
  document.querySelectorAll('#outs .out').forEach((o,k)=>o.classList.toggle('on',p>.55+k*.08));
 },
 mac(p){
  const t=E(seg(p,.08,.62));
  const ang=mix(-92,0,t);$('#lid').style.transform=`rotateX(${ang}deg)`;const bk=ang<-89.5;$('#lid .f').style.visibility=bk?'hidden':'visible';$('#lid .b').style.visibility=bk?'visible':'hidden';
  $('#macw').style.transform=`translateX(-50%) translateY(${mix(6,0,t)}vh) scale(${mix(.92,1,t)})`;
  const mt=$('#mtitle');mt.style.opacity=mix(.0,1,EO(seg(p,0,.2)));mt.style.transform=`translateY(${(1-EO(seg(p,0,.2)))*30}px)`;
 },
 lock(p){
  const t=E(seg(p,.08,.5)), g=EO(seg(p,.48,.62));
  $('#shk').setAttribute('transform',`translate(0 ${mix(-46,0,t)})`);
  $('#lglow').style.opacity=g*.9;
  $('#lk').style.transform=`translate(-50%,-50%) scale(${mix(.9,1,t)+g*.04-seg(p,.62,.75)*.04})`;
  const lt=$('#ltxt'),u=EO(seg(p,.5,.7));lt.style.opacity=u;lt.style.transform=`translateY(${(1-u)*40}px)`;
 }
};


/* ---------- lab at your door ---------- */
const LR=document.getElementById('lroute'),LT=document.getElementById('ltech');let LL=0;
fx.lab=function(p){
 if(!LL)LL=LR.getTotalLength();
 const tilt=E(seg(p,0,.25)),r=E(seg(p,.08,.5));
 document.getElementById('lmap').style.transform=`rotateX(${mix(52,18,tilt)}deg) scale(${mix(1.25,1.02,tilt)}) translateY(${mix(4,0,tilt)}%)`;
 LR.style.strokeDasharray=LL;LR.style.strokeDashoffset=LL*(1-r);
 const pt=LR.getPointAtLength(LL*r);LT.setAttribute('transform',`translate(${pt.x} ${pt.y})`);
 const mins=Math.ceil(12*(1-r));const arrived=r>=.999;
 document.getElementById('lmin').textContent=arrived?'0':String(mins);
 document.getElementById('letaT').textContent=tr(p>=.6?'Sample collected':arrived?'Ravi has arrived':'Ravi is on the way');
 const stepAt=[0,.08,.56,.7,.84];let cur=0;stepAt.forEach((a,i)=>{if(p>=a)cur=i});
 document.querySelectorAll('#lsteps .ls').forEach((el,i)=>{el.classList.toggle('on',i<=cur);el.classList.toggle('cur',i===cur)});
 const n=document.getElementById('lnote'),q=EO(seg(p,.84,.94));n.style.opacity=q;n.style.transform=`translateY(${(1-q)*30}px) scale(${mix(.96,1,q)})`;
 document.getElementById('leta').style.opacity=1-seg(p,.8,.86);
};

/* ---------- family constellation ---------- */
const FN=[{a:-162,r:1},{a:-18,r:1},{a:148,r:1},{a:32,r:1}];
fx.family=function(p){
 // layout from measured sizes so nothing collides on short or narrow screens
 const ft=$('#ftitle'),q=seg(p,.62,.72);ft.style.opacity=1-q;ft.style.transform=`translateY(${-q*30}px)`;
 const n1=$('#n1'),nh=n1.offsetHeight||130,nw=n1.offsetWidth||120,mh=$('#n0').offsetHeight||150;
 const tb=ft.offsetTop+ft.offsetHeight+18,fe=$('#fend'),fb=H-(fe.offsetHeight+H*.07)-12;
 const gapY=Math.max(nh+26,(mh)*.9);                       // vertical distance between the two nodes on each side
 const room=fb-tb;                                           // free height between title and bottom text
 const cy=Math.round(tb+Math.max(room/2,gapY/2+nh/2));
 const cx=W/2;
 const sideX=mob?Math.min(W/2-nw/2-10,W*.33):Math.min(Math.max(W*.24,mh*1.6),420);
 const svg=$('#flines');svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
 if(!svg.dataset.ready){svg.dataset.ready=1;svg.innerHTML='<defs><linearGradient id="fg" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#4F7BFF"/><stop offset="1" stop-color="#E2458A"/></linearGradient></defs>'+[0,1,2,3].map(i=>`<line class="base" id="fl${i}" stroke="url(#fg)" stroke-width="2" stroke-linecap="round"/><line class="flow" id="ff${i}" stroke="#7C5CFF" stroke-width="4.5"/>`).join('')}
 $('#fglow').style.top=cy+'px';
 ['#n0','#n1','#n2','#n3','#n4'].forEach(id=>$(id).style.top=cy+'px');
 const o1=$('#orb1'),o2=$('#orb2'),oa=EO(seg(p,.05,.25))*(1-seg(p,.62,.72));
 [o1,o2].forEach(o=>o.style.top=cy+'px');$('#fglow').style.opacity=oa;
 o1.style.width=sideX*2+'px';o1.style.height=gapY*1.15+'px';o2.style.width=sideX*2.5+'px';o2.style.height=gapY*1.7+'px';
 o1.style.opacity=oa;o2.style.opacity=oa*.5;o2.style.transform=`translate(-50%,-50%) rotate(${p*20}deg)`;
 const z=E(seg(p,.66,.9));
 const me=$('#n0'),ma=EO(seg(p,.02,.14));
 me.style.opacity=ma*(1-z);me.style.transform=`translate(-50%,-50%) scale(${mix(.6,1,ma)*(1-z*.4)})`;
 // left: Amma (top), Arjun (bottom); right: Nanna (top), Kavya (bottom)
 const POS=[[-1,-1],[1,-1],[-1,1],[1,1]];const fg=svg.querySelector('#fg');fg.setAttribute('x1',cx-sideX);fg.setAttribute('x2',cx+sideX);
 POS.forEach(([sx,sy],i)=>{const el=$('#n'+(i+1)),t=EO(seg(p,.14+i*.1,.26+i*.1));
  const drift=Math.sin(p*6+i)*6;
  let x=sx*sideX*mix(1.5,1,t), y=sy*gapY/2+drift;
  let sc=mix(.5,1,t),op=t;
  if(i===3){const ky=Math.min(0,(tb+fb)/2-cy-mh*.2);x=mix(x,0,z);y=mix(y,ky,z);sc*=mix(1,1.45,z);el.querySelector('em').style.opacity=1-z}else op*=1-z;
  el.style.opacity=op;el.style.transform=`translate(calc(-50% + ${x}px),calc(-50% + ${y}px)) scale(${sc})`;
  const ex=cx+x,ey=cy+y-nh*.18,L=Math.hypot(ex-cx,ey-cy),dl=L*t;
  const bl=svg.querySelector('#fl'+i),fl=svg.querySelector('#ff'+i);
  bl.setAttribute('x1',cx);bl.setAttribute('y1',cy);bl.setAttribute('x2',ex);bl.setAttribute('y2',ey);bl.setAttribute('stroke-dasharray',L);bl.setAttribute('stroke-dashoffset',L-dl);bl.setAttribute('opacity',(1-z)*.8);
  fl.setAttribute('x1',ex);fl.setAttribute('y1',ey);fl.setAttribute('x2',cx);fl.setAttribute('y2',cy);fl.setAttribute('opacity',(t>.98?1:0)*(1-z)*.9)});
 const u=EO(seg(p,.8,.94));fe.style.opacity=u;fe.style.transform=`translateY(${(1-u)*30}px)`;
};

/* ---------- kids vaccine rings ---------- */
const KR=[184,156,128,100,72],KL=['Birth','14 weeks','9 months','18 months','5 years'],KS=['Next: 6 weeks','Next: 9 months','Next: 16 months','Next: 5 years','All caught up'];
(()=>{const g=$('#ksvg');let h='';KR.forEach((r,i)=>{const c=2*Math.PI*r;
 h+=`<circle cx="200" cy="200" r="${r}" fill="none" stroke="rgba(0,0,0,.06)" stroke-width="20"/>`+
    `<circle id="kr${i}" cx="200" cy="200" r="${r}" fill="none" stroke="url(#k${i})" stroke-width="20" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c}" transform="rotate(-90 200 200)" style="filter:drop-shadow(0 4px 8px rgba(0,0,0,.12))"/>`+
    `<circle id="kd${i}" cx="200" cy="${200-r}" r="0" fill="#fff"/>`});
 g.insertAdjacentHTML('beforeend',h)})();
let kPrev=-1;
fx.kids=function(p){
 let act=0;
 KR.forEach((r,i)=>{const a=.06+i*.18,t=E(seg(p,a,a+.14)),c=2*Math.PI*r;
  document.getElementById('kr'+i).setAttribute('stroke-dashoffset',c*(1-t));
  const ang=(-90+360*t)*Math.PI/180,d=document.getElementById('kd'+i);
  d.setAttribute('cx',200+Math.cos(ang)*r);d.setAttribute('cy',200+Math.sin(ang)*r);d.setAttribute('r',t>0.01?5:0);
  if(p>=a)act=i});
 if(act!==kPrev){kPrev=act;
  document.querySelectorAll('#kcards .kc').forEach((c,k)=>c.classList.toggle('on',k===act));
  document.querySelectorAll('#kdots i').forEach((c,k)=>c.classList.toggle('on',k===act));
  $('#kage').textContent=tr(KL[act]);$('#ktsub').textContent=tr(KS[act]);
  const tt=$('#ktoast');tt.classList.remove('on');void tt.offsetWidth;if(p>.1)tt.classList.add('on');}
 $('#ksvg').style.transform=`rotate(${mix(-8,0,EO(seg(p,0,.2)))}deg)`;$('#kring').style.transform=`scale(${mix(.9,1,EO(seg(p,0,.15)))})`;
};

const scenes=[...document.querySelectorAll('.scene')].map(el=>({el,f:(p,e)=>fx[e.id](p,e),p:-1,t:0,top:0,h:0}));
const galEl=document.getElementById('gal');
function measure(){W=innerWidth;H=innerHeight;mob=W<560||(W<900&&H>W);
 const tr=$('#track');galEl.style.height=(Math.max(0,tr.scrollWidth-W)+H*1.6)+'px';
 scenes.forEach(s=>{const r=s.el.getBoundingClientRect();s.top=r.top+scrollY;s.h=s.el.offsetHeight});
 scenes.forEach(s=>{s.p=-1})}
const nav=document.getElementById('nav'),prog=document.getElementById('prog');
const darkSecs=[...document.querySelectorAll('[data-dark],.priv,.final')];
function frame(){
 const y=scrollY;
 for(const s of scenes){
  const t=C((y-s.top)/Math.max(1,s.h-H));
  if(y+H<s.top-H*.5||y>s.top+s.h+H*.5){s.t=t;if(s.p<0){s.p=t;s.f(t,s.el)}continue}
  const np=R||window.__snap||s.p<0?t:s.p+(t-s.p)*.12;
  if(Math.abs(np-s.p)>.0002||s.p<0){s.p=Math.abs(np-t)<.0004?t:np;s.f(s.p,s.el)}
 }
 const probe=y+26;let dk=false;
 for(const d of darkSecs){const r=d.getBoundingClientRect();if(r.top<=26&&r.bottom>26){dk=true;break}}
 // hero turns light at its end
 const hs=scenes[0];if(dk&&hs.el.contains(document.elementFromPoint(W/2,26))&&hs.p>.9)dk=false;
 nav.classList.toggle('light',!dk);
 prog.style.transform=`scaleX(${y/(document.documentElement.scrollHeight-H)||0})`;
 requestAnimationFrame(frame);
}
addEventListener('resize',()=>{measure()});
addEventListener('load',measure);
measure();requestAnimationFrame(frame);

/* reveal */
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.12});
document.querySelectorAll('.rv,.tl').forEach(e=>io.observe(e));
/* loops */
const pls=[...document.querySelectorAll('#pills .pl')];let k=0;
if(!R)setInterval(()=>{if(k===pls.length){pls.forEach(p=>p.classList.remove('done'));k=0;return}pls[k++].classList.add('done')},1200);else pls.forEach(p=>p.classList.add('done'));
const ls=[...document.querySelectorAll('#langs span')].slice(0,3);let li=0;
if(!R)setInterval(()=>{ls[li].classList.remove('on');li=(li+1)%ls.length;ls[li].classList.add('on')},1500);
/* DPDP timeline: "Today" by the real date */
const t0=Date.UTC(2025,10,14),t1=Date.UTC(2027,4,14),pc=C((Date.now()-t0)/(t1-t0))*100;
$('#tl').style.setProperty('--w',pc+'%');$('#nowTag').style.left=pc+'%';
{const now=new Date(),day=864e5,fmt=d=>d.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
 $('#nowTag').textContent='Today · '+now.toLocaleDateString('en-IN',{day:'numeric',month:'short'});
 document.querySelectorAll('#tl .pt[data-d]').forEach(p=>{const d=new Date(p.dataset.d+'T00:00:00+05:30');p.classList.toggle('done',d<=now);p.classList.toggle('fut',d>now)});
 document.querySelectorAll('#tl .tlc>div').forEach(el=>{const d=new Date(el.dataset.d+'T00:00:00+05:30'),ph=el.querySelector('.ph'),n=Math.ceil((d-now)/day);
  if(n<=0){ph.textContent='In force since '+fmt(d);ph.className='ph live'}else{ph.textContent=n===1?'Starts tomorrow':n<=60?'Starts in '+n+' days':'Starts '+fmt(d);ph.className='ph'+(n<=60?' soon':'')}})}
document.querySelectorAll('#nav .links a').forEach(a=>a.addEventListener('click',()=>nav.classList.remove('open')));
window.nav=nav;

/* ---------- particle fields ---------- */
function Field(cv,build,opts){
 const ctx=cv.getContext('2d');let pts=[],w=0,h=0,dpr=Math.min(2,devicePixelRatio||1),mx=-9e3,my=-9e3,vis=false,t0=performance.now();
 this.burst=0;this.alpha=1;
 const cols=['#4F7BFF','#7C5CFF','#B15CFF','#F0559A'];
 const size=()=>{const r=cv.getBoundingClientRect();w=r.width;h=r.height;cv.width=w*dpr;cv.height=h*dpr;
  const off=document.createElement('canvas');off.width=Math.round(w);off.height=Math.round(h);const o=off.getContext('2d');
  build(o,w,h,()=>{const d=o.getImageData(0,0,off.width,off.height).data,cand=[],np=[];
   for(let y=0;y<off.height;y+=2)for(let x=0;x<off.width;x+=2)if(d[(y*off.width+x)*4+3]>120)cand.push(x,y);
   const n=Math.min(opts.n||1800,cand.length/2),cnt=cand.length/2;let minx=1e9,maxx=-1e9;
   for(let i=0;i<cnt;i++){minx=Math.min(minx,cand[i*2]);maxx=Math.max(maxx,cand[i*2])}
   for(let i=0;i<n;i++){const j=Math.floor(Math.random()*cnt),x=cand[j*2]+(Math.random()-.5)*2,y=cand[j*2+1]+(Math.random()-.5)*2,old=pts[i];
     np.push({hx:x,hy:y,x:old?old.x:Math.random()*w,y:old?old.y:Math.random()*h,vx:0,vy:0,a:Math.random()*Math.PI*2,s:(.55+Math.random()*.9)*(opts.size||1),
      c:Math.min(3,Math.floor((x-minx)/(maxx-minx+1)*4)),dr:Math.random()})}
   pts=np})};
 size();addEventListener('resize',()=>{clearTimeout(this._r);this._r=setTimeout(size,200)});
 cv.parentElement.addEventListener('pointermove',e=>{const r=cv.getBoundingClientRect();mx=e.clientX-r.left;my=e.clientY-r.top});
 cv.parentElement.addEventListener('pointerleave',()=>{mx=my=-9e3});
 new IntersectionObserver(es=>{vis=es[0].isIntersecting}).observe(cv);
 const tick=now=>{requestAnimationFrame(tick);if(!vis||this.alpha<=0.01){if(this.alpha<=.01)ctx.clearRect(0,0,cv.width,cv.height);return}
  const tt=(now-t0)/1000,beat=opts.beat?1+.06*Math.pow(Math.max(0,Math.sin(tt*Math.PI*1.25)),12)+.03*Math.pow(Math.max(0,Math.sin(tt*Math.PI*1.25-0.7)),12):1;
  const cx=w/2,cy=h*(opts.cy||.5);
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);ctx.globalAlpha=this.alpha;
  const B=this.burst;
  for(const q of pts){
   let tx=cx+(q.hx-cx)*beat, ty=cy+(q.hy-cy)*beat;
   tx+=Math.cos(q.a+tt*.6)*2.2;ty+=Math.sin(q.a+tt*.8)*2.2;
   if(B>0){const dx=q.hx-cx,dy=q.hy-cy,L=Math.hypot(dx,dy)||1;tx+=dx/L*B*(600+q.dr*900);ty+=dy/L*B*(600+q.dr*900)-B*q.dr*200}
   const ddx=q.x-mx,ddy=q.y-my,d2=ddx*ddx+ddy*ddy;
   if(d2<14400){const f=(1-Math.sqrt(d2)/120)*6;q.vx+=ddx/Math.sqrt(d2+1)*f;q.vy+=ddy/Math.sqrt(d2+1)*f}
   q.vx+=(tx-q.x)*.045;q.vy+=(ty-q.y)*.045;q.vx*=.82;q.vy*=.82;q.x+=q.vx;q.y+=q.vy;
  }
  for(let c=0;c<4;c++){ctx.fillStyle=cols[c];ctx.beginPath();
   for(const q of pts)if(q.c===c){ctx.moveTo(q.x+q.s,q.y);ctx.arc(q.x,q.y,q.s,0,6.283)}
   ctx.fill()}
 };
 if(!R)requestAnimationFrame(tick);else{this.alpha=0}
}
const markImg=new Image();markImg.src='data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2064%2064%22%3E%3Cpath%20d%3D%22M21.5%2015a4%204%200%200%201%204-4h3a4%204%200%200%201%204%204v34a4%204%200%200%201-4%204h-3a4%204%200%200%201-4-4V37.5H13a4%204%200%200%201-4-4v-3a4%204%200%200%201%204-4h8.5z%22%20fill%3D%22%232F5BFF%22/%3E%3Cpath%20d%3D%22M32%2032h5l3.2-8%204.6%2016%203.2-8h0.4%22%20fill%3D%22none%22%20stroke%3D%22%232F5BFF%22%20stroke-width%3D%224.6%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22/%3E%3Ccircle%20cx%3D%2255.2%22%20cy%3D%2232%22%20r%3D%223.3%22%20fill%3D%22%232F5BFF%22/%3E%3C/svg%3E';
const heroField=new Field(document.getElementById('heroField'),(o,w,h,done)=>{
 const go=()=>{const S=mob?Math.min(w*.72,h*.42):Math.min(w*.3,h*.32),cy=h*(mob?.55:.81);o.drawImage(markImg,(w-S)/2,cy-S/2,S,S);done()};
 markImg.complete&&markImg.naturalWidth?go():markImg.onload=go},{get cy(){return mob?.55:.81},n:mob?1500:2800});
const heartField=new Field(document.getElementById('heartField'),(o,w,h,done)=>{
 const S=Math.min(w,h)*(mob?.019:.024),cx=w/2,cy=h*.5;o.beginPath();
 for(let t=0;t<=6.3;t+=.01){const x=16*Math.pow(Math.sin(t),3),y=13*Math.cos(t)-5*Math.cos(2*t)-2*Math.cos(3*t)-Math.cos(4*t);t===0?o.moveTo(cx+x*S,cy-y*S):o.lineTo(cx+x*S,cy-y*S)}
 o.fill();done()},{n:mob?1600:2800,beat:1,size:1.25});
heartField.alpha=mob?.42:.8;
const _hero=fx.hero;let swx=0,swy=0,lastHP=0,swRAF=0;document.getElementById('hero').addEventListener('pointermove',()=>{if(swRAF)return;const go=()=>{fx.hero(lastHP);swRAF=(Math.abs(P3.mx-swx)+Math.abs(P3.my-swy)>.002)?requestAnimationFrame(go):0};swRAF=requestAnimationFrame(go)});
fx.hero=function(p,el){lastHP=p;_hero(p,el);
 const t2=E(seg(p,.05,.62));document.getElementById('hph').style.transform='translateZ(1px)';
 swx+=(P3.mx-swx)*.08;swy+=(P3.my-swy)*.08;const sway=seg(p,.5,.62);
 const ry=mix(-34,0,t2)+swx*16*sway,rx=mix(48,0,t2)-swy*10*sway,sc=mix(.86,1,t2);
 P3.wrap.style.transform=`rotateX(${rx}deg) rotateY(${ry}deg) scale(${sc})`;P3.gloss.style.setProperty('--g',(100-((ry+34)/50)*100)+'%');
 heroField._fadeOut=seg(p,.8,1);heroField.burst=E(seg(p,.1,.45));heroField.alpha=mix(mob?0:.9,.95,EO(seg(p,0,.08)))*(1-seg(p,.22,.46));};


/* ---------- real 3D body (the app's own model, loader and materials) ---------- */
const B3={ready:false,p:0};window.__B3=B3;
(()=>{
 const st=document.querySelector('#body .stage'),cv=document.getElementById('b3d'),lines=document.getElementById('b3lines');
 const ORGCOL={heart:0xB8323F,liver:0x8E3B2C,pancreas:0xD9963A,thyroid:0xB8404E,kidney:0x7E2C2C,lung:0xD99AA2,gut:0xD69580,uterus:0xD0607A};
 const LAB=[['lung','o3lung',1,.2],['liver','o3liver',-1,.3],['kidney','o3kidney',1,.4],['gut','o3gut',-1,.5]];
 let T,R,scene,cam,root,M,base={},vis=false,started=false;
 const b64buf=b=>{const s=atob(b),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u};
 async function getBin(){const src=window.UH_BODY_BIN;if(typeof src==='string'&&src.startsWith('/'))return new Response((await fetch(src)).body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  return new Response(new Blob([b64buf(src)]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()}
 async function getNames(){const n=window.UH_BODY_NAMES;return typeof n==='string'?(await fetch(n)).json():n}
 function geom(S0,p){const q=new Uint16Array(S0.buf,S0.base+p.o,p.v*3),ix=new Uint16Array(S0.buf,S0.base+p.o+p.v*6,p.i),b=p.b,pos=new Float32Array(p.v*3);
  for(let j=0;j<p.v;j++){pos[j*3]=b[0]+q[j*3]/65535*(b[3]-b[0]);pos[j*3+1]=b[1]+q[j*3+1]/65535*(b[4]-b[1]);pos[j*3+2]=b[2]+q[j*3+2]/65535*(b[5]-b[2])}
  const g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(pos,3));g.setIndex(new T.BufferAttribute(new Uint32Array(ix),1));g.computeVertexNormals();return g}
 function organKey(n){n=n.toLowerCase();
  if(/uter|ovar|fallop|placent/.test(n))return 'uterus';if(/thyroid gland|lobe of thyroid|isthmus of thyroid/.test(n))return 'thyroid';
  if(/kidney|renal (cortex|pelvis|papill|pyramid)/.test(n)&&!/arter|vein|impression/.test(n))return 'kidney';
  if(/pancrea/.test(n))return 'pancreas';if(/liver/.test(n)&&!/impression|ligament/.test(n))return 'liver';
  if(/atri|ventric|cardiac|heart|myocard|papillary|valve|leaflet|cusp|chordae|interventricular/.test(n)&&!/fourth ventricle|lateral ventricle|third ventricle|arter|vein|conduction/.test(n))return 'heart';
  if(/lung|bronch/.test(n)&&!/arter|vein/.test(n))return 'lung';
  if(/stomach|intestin|colon|jejun|ileum|duoden|cecum|caecum|rectum|esophag|oesophag|appendix|spleen|gallbladder|bladder/.test(n))return 'gut';return null}
 function merge(list){let nv=0,ni=0;list.forEach(g=>{nv+=g.attributes.position.count;ni+=g.index.count});const pos=new Float32Array(nv*3),nor=new Float32Array(nv*3),idx=new Uint32Array(ni);let vo=0,io=0;
  list.forEach(g=>{pos.set(g.attributes.position.array,vo*3);nor.set(g.attributes.normal.array,vo*3);const ix=g.index.array;for(let j=0;j<ix.length;j++)idx[io+j]=ix[j]+vo;vo+=g.attributes.position.count;io+=ix.length;g.dispose()});
  const g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(pos,3));g.setAttribute('normal',new T.BufferAttribute(nor,3));g.setIndex(new T.BufferAttribute(idx,1));g.computeBoundingBox();return g}
 async function init(){
  try{
   await (window.UH_LIBS?window.UH_LIBS():0);T=window.THREE;if(!T||!window.DecompressionStream)return;
   R=new T.WebGLRenderer({canvas:cv,antialias:true,alpha:true});R.setPixelRatio(Math.min(devicePixelRatio,1.75));R.outputEncoding=T.sRGBEncoding;R.toneMapping=T.ACESFilmicToneMapping;R.toneMappingExposure=1.0;
   scene=new T.Scene();cam=new T.PerspectiveCamera(26,1,.1,100);
   scene.add(new T.HemisphereLight(0xeef2ff,0x3a2030,.55));const k=new T.DirectionalLight(0xfff4ec,1.05);k.position.set(3,5,6);scene.add(k);
   const rim=new T.DirectionalLight(0x8fa8ff,.7);rim.position.set(-5,2,-6);scene.add(rim);const rim2=new T.DirectionalLight(0xff8fb8,.45);rim2.position.set(6,-1,-4);scene.add(rim2);
   root=new T.Group();scene.add(root);
   const [buf,names]=await Promise.all([getBin(),getNames()]);const jl=new DataView(buf).getUint32(0,true);
   const set={buf,meta:JSON.parse(new TextDecoder().decode(new Uint8Array(buf,4,jl))),base:4+jl,names};
   const skinG=[],org={};
   set.meta.parts.forEach((p,i)=>{const l=p.l??1,n=set.names[i];if(l===0){if(/^skin/i.test(n))skinG.push(geom(set,p));return}if(l!==3)return;const key=organKey(n);if(!key||key==='uterus')return;(org[key]=org[key]||[]).push(geom(set,p))});
   const skinGeo=merge(skinG);skinGeo.computeBoundingBox();
   const bb=skinGeo.boundingBox,ctr=bb.getCenter(new T.Vector3()),sz=bb.getSize(new T.Vector3());
   const body=new T.Group();body.position.set(-ctr.x,-ctr.y,-ctr.z);root.add(body);
   const skinMat=new T.ShaderMaterial({transparent:true,depthWrite:false,blending:T.AdditiveBlending,side:T.FrontSide,uniforms:{uA:{value:1},uT:{value:0}},
    vertexShader:'varying vec3 vN;varying vec3 vV;varying float vY;void main(){vec4 mv=modelViewMatrix*vec4(position,1.);vN=normalize(normalMatrix*normal);vV=normalize(-mv.xyz);vY=position.y;gl_Position=projectionMatrix*mv;}',
    fragmentShader:'uniform float uA;uniform float uT;varying vec3 vN;varying vec3 vV;varying float vY;void main(){float f=pow(1.-abs(dot(vN,vV)),2.4);float scan=smoothstep(.0,.02,abs(fract(vY*.9-uT*.25)-.5))*.0+.9+.1*sin(vY*60.-uT*3.);vec3 c=mix(vec3(.22,.32,.95),vec3(.78,.86,1.),f);gl_FragColor=vec4(c*(.05+1.15*f)*scan,1.)*uA;}'});
   const skin=new T.Mesh(skinGeo,skinMat);skin.renderOrder=2;
   const back=new T.Mesh(skinGeo,new T.MeshBasicMaterial({color:0x1E2A66,transparent:true,opacity:.18,side:T.BackSide,depthWrite:false,blending:T.AdditiveBlending}));back.renderOrder=1;
   body.add(back,skin);
   const organs={};
   const H0=sz.y;for(const k2 in org){const cs=org[k2].map(g=>{g.computeBoundingBox();return g.boundingBox.getCenter(new T.Vector3())});
    const med=new T.Vector3(...['x','y','z'].map(a=>{const v=cs.map(c=>c[a]).sort((p,q)=>p-q);return v[v.length>>1]}));
    const lim=H0*(k2==='gut'?.16:k2==='lung'?.12:.07);org[k2]=org[k2].filter((g,i)=>cs[i].distanceTo(med)<lim)}
   for(const k2 in org){if(!org[k2].length)continue;const g=merge(org[k2]);const c=new T.Vector3();g.boundingBox.getCenter(c);g.translate(-c.x,-c.y,-c.z);
    const m=new T.Mesh(g,new T.MeshPhysicalMaterial({color:new T.Color(ORGCOL[k2]).convertSRGBToLinear(),roughness:.42,metalness:0,clearcoat:.35,clearcoatRoughness:.35,transparent:true,opacity:.95,emissive:new T.Color(ORGCOL[k2]).convertSRGBToLinear(),emissiveIntensity:0}));m.position.copy(c);body.add(m);
    const s3=new T.Vector3();g.boundingBox.getSize(s3);organs[k2]={mesh:m,size:s3.length()}}
   M={skin,back,organs,height:sz.y,body};
   size();addEventListener('resize',size);
   B3.ready=true;st.classList.add('has3d');requestAnimationFrame(loop);
   loadHeart();
  }catch(e){console.warn('3D body unavailable',e)}
 }
 let HD=null,mixer=null,hclock=null;
 async function loadHeart(){try{
   if(!T.GLTFLoader||!window.MeshoptDecoder)return;await MeshoptDecoder.ready;
   const src=window.UH_HEART;const ab=typeof src==='string'&&src.startsWith('/')?await (await fetch(src)).arrayBuffer():b64buf(src).buffer;
   const L=new T.GLTFLoader();L.setMeshoptDecoder(MeshoptDecoder);
   L.parse(ab,'',g=>{const sc=g.scene;sc.traverse(o=>{if(o.isMesh){o.frustumCulled=false;const m=o.material;if(m){m.transparent=true;m.opacity=0;m.depthWrite=true}}});
    sc.updateMatrixWorld(true);const bb=new T.Box3().setFromObject(sc),c=bb.getCenter(new T.Vector3()),s1=bb.getSize(new T.Vector3());
    const hm=M.organs.heart.mesh;hm.geometry.computeBoundingBox();const s2=hm.geometry.boundingBox.getSize(new T.Vector3());
    const k=Math.max(s2.x,s2.y,s2.z)/Math.max(s1.x,s1.y,s1.z)*1.05;
    const pivot=new T.Group();sc.position.copy(c).multiplyScalar(-1);pivot.add(sc);pivot.scale.setScalar(k);pivot.position.copy(hm.position);M.body.add(pivot);
    const hb=g.animations.find(a=>a.name==='Heartbeat');if(hb){mixer=new T.AnimationMixer(sc);mixer.clipAction(hb).play()}
    HD=pivot;HD.userData.t0=performance.now();HD.userData.meshes=[];sc.traverse(o=>{if(o.isMesh)HD.userData.meshes.push(o)});hclock=performance.now()},e=>console.warn('heart',e))
  }catch(e){console.warn('heart',e)}}
 function size(){const w=st.clientWidth,h=st.clientHeight;R.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix()}
 const v=()=>new T.Vector3();let tmp,tmp2,clock=performance.now();
 function loop(now){requestAnimationFrame(loop);if(!vis)return;tmp=tmp||v();tmp2=tmp2||v();
  const p=B3.p,t=now/1000,Wd=st.clientWidth,Hd=st.clientHeight,mobile=Wd<900;
  // body enters, then turns a full circle while organs are named, then the camera flies to the heart
  const a=EO(seg(p,0,.16)),turn=E(seg(p,.04,.7)),z=E(seg(p,.7,.93));
  root.rotation.y=mix(-.9,Math.PI*2,turn)+Math.sin(t*.4)*.03*(1-z);
  root.position.y=mix(-M.height*.25,0,a);
  const fitH=M.height/(mobile?.86:.78),dist=(fitH/2)/Math.tan(13*Math.PI/180)*Math.max(1,(mobile?.62:.9)/Math.min(1,cam.aspect*1.6));
  root.updateMatrixWorld(true);
  const hm=M.organs.heart.mesh;hm.getWorldPosition(tmp);
  const bodyY=mobile?-M.height*.04:-M.height*.02;
  const hd=M.organs.heart.size*(mobile?6.2:4.3);
  cam.position.set(mix(0,tmp.x,z),mix(bodyY,tmp.y,z),mix(dist,tmp.z+hd,z));
  tmp2.set(mix(0,tmp.x,z),mix(bodyY,tmp.y,z),mix(0,tmp.z,z));cam.lookAt(tmp2);
  // materials: skin clears away near the heart; heart beats
  M.skin.material.uniforms.uA.value=mix(1,.25,z);M.skin.material.uniforms.uT.value=t;M.back.material.opacity=mix(.18,.03,z);
  const beat=1+.07*Math.pow(Math.max(0,Math.sin(t*Math.PI*2.4)),10)+.035*Math.pow(Math.max(0,Math.sin(t*Math.PI*2.4-.9)),10);
  hm.scale.setScalar(1+(beat-1)*mix(.3,1,z));
  for(const k in M.organs){const m=M.organs[k].mesh.material;let e=0;
   LAB.forEach(([key,,,st0])=>{if(key===k){const on=seg(p,st0,st0+.05)*(1-seg(p,st0+.12,st0+.16));e=on*(.35+.15*Math.sin(t*4))}});
   if(k==='heart')e=Math.max(e,z*(.25+.25*(beat-1)/.07));
   m.emissiveIntensity=.06+e;m.opacity=k==='heart'?1:mix(.95,.04,z);m.depthWrite=k==='heart'||z<.5}
  if(HD){const h=Math.min(1,(now-HD.userData.t0)/700);HD.userData.meshes.forEach(o=>{o.material.opacity=h;o.visible=true});hm.visible=h<1;hm.material.opacity=1-h;
   if(mixer){const n=performance.now();mixer.update(Math.min(.05,(n-hclock)/1000));hclock=n}}
  cv.style.opacity=a;
  R.render(scene,cam);
  // labels follow their organ on screen
  const xy=k=>{const o=M.organs[k];if(!o)return null;o.mesh.getWorldPosition(tmp);tmp.project(cam);return[(tmp.x*.5+.5)*Wd,(-tmp.y*.5+.5)*Hd]};
  drawLabels(p,t,xy,Wd,Hd,mobile);
  {const P2={};['lung','liver','kidney','gut','heart'].forEach(k=>{const o=M.organs[k];if(!o)return;o.mesh.getWorldPosition(tmp);tmp.project(cam);P2[k]=[+(tmp.x*.5+.5).toFixed(4),+(-tmp.y*.5+.5).toFixed(4)]});B3.pos=P2}
 }
 function drawLabels(p,t,xy,Wd,Hd,mobile){
  let svg='';const fade=1-seg(p,.66,.72);const PL={'1':[],'-1':[]};
  LAB.forEach(([key,id,side,st0])=>{const el=document.getElementById(id),c=xy(key);if(!c)return;
   const tt=EO(seg(p,st0,st0+.07))*fade;const [x,y]=c,off=Math.min(mobile?110:240,Wd*.26),ew=el.offsetWidth,eh=el.offsetHeight;
   let lx=x+side*off-(side<0?ew:0);lx=Math.max(8,Math.min(Wd-ew-8,lx));let ly=y-eh/2;
   const used=PL[side];for(const u of used){if(Math.abs(ly-u)<eh+10)ly=u+(ly>=u?1:-1)*(eh+10)}if(tt>.02)used.push(ly);
   el.style.opacity=tt;el.style.transform=`translate(${lx}px,${ly+(1-tt)*16}px) scale(${mix(.86,1,tt)})`;
   if(tt>.02){const ex=side>0?lx:lx+ew,ey=ly+eh/2,L=Math.hypot(ex-x,ey-y);
    svg+=`<line x1="${x}" y1="${y}" x2="${ex}" y2="${ey}" stroke="rgba(255,255,255,.5)" stroke-width="1.4" stroke-dasharray="${L}" stroke-dashoffset="${L*(1-tt)}" opacity="${tt}"/><circle cx="${x}" cy="${y}" r="${5*tt}" fill="#fff" stroke="rgba(255,255,255,.8)" stroke-width="1.6"/><circle cx="${x}" cy="${y}" r="${5+9*((t*1.3)%1)}" fill="none" stroke="rgba(142,166,255,${.5*(1-(t*1.3)%1)*tt})" stroke-width="1.5"/>`}});
  lines.innerHTML=svg;
  const hb=document.getElementById('o3heart'),hq=EO(seg(p,.86,.94)),hc=xy('heart');if(!hc)return;const [hx,hy]=hc;
  hb.style.opacity=hq;hb.style.transform=mobile?`translate(${hx-hb.offsetWidth/2}px,${Math.max(64,hy-Hd*.26)}px)`:`translate(${Math.min(Wd-hb.offsetWidth-16,hx+Wd*.12)}px,${hy-hb.offsetHeight/2}px)`;
 }
 /* phones: the same scene, pre-rendered as frames and scrubbed by scroll (smooth on any phone) */
 const SEQ=window.UH_SEQ,phone=()=>innerWidth<560||(innerWidth<900&&innerHeight>innerWidth);
 function initSeq(){
  const ctx=cv.getContext('2d'),imgs=new Array(SEQ.n);let last=-1,lastW=0;
  const load=i=>new Promise(r=>{if(imgs[i])return r();const im=new Image();im.decoding='async';im.onload=()=>{imgs[i]=im;last=-1;r()};im.onerror=()=>r();im.src=SEQ.src(i)});
  (async()=>{for(const step of [12,6,3,1]){const jobs=[];for(let i=0;i<SEQ.n;i+=step)jobs.push(load(i));await Promise.all(jobs)}})();
  const size2=()=>{const d=Math.min(2,devicePixelRatio||1);cv.width=Math.round(st.clientWidth*d);cv.height=Math.round(st.clientHeight*d);last=-1};size2();addEventListener('resize',size2);
  B3.ready=true;st.classList.add('has3d');
  const loop=now=>{requestAnimationFrame(loop);if(!vis)return;const p=B3.p,Wd=st.clientWidth,Hd=st.clientHeight,f=p*(SEQ.n-1);
   let k=Math.round(f),j=k;while(j>=0&&!imgs[j])j--;if(j<0){j=k;while(j<SEQ.n&&!imgs[j])j++}const im=imgs[j];if(!im)return;
   const s2=Math.max(cv.width/im.width,cv.height/im.height),w=im.width*s2,h=im.height*s2,x0=(cv.width-w)/2,y0=(cv.height-h)/2;
   if(j!==last||cv.width!==lastW){ctx.clearRect(0,0,cv.width,cv.height);ctx.drawImage(im,x0,y0,w,h);last=j;lastW=cv.width}
   cv.style.opacity=EO(seg(p,0,.16));
   const a0=SEQ.pos[Math.floor(f)]||{},a1=SEQ.pos[Math.min(SEQ.n-1,Math.ceil(f))]||a0,fr=f-Math.floor(f);
   const xy=key=>{const A=a0[key],B=a1[key]||A;if(!A)return null;const u=mix(A[0],B[0],fr),v=mix(A[1],B[1],fr);return[(x0+u*w)/cv.width*Wd,(y0+v*h)/cv.height*Hd]};
   drawLabels(p,now/1000,xy,Wd,Hd,true)};
  requestAnimationFrame(loop)}
 new IntersectionObserver(es=>{vis=es[0].isIntersecting;if(vis&&!started){started=true;(SEQ&&phone())?initSeq():init()}},{rootMargin:'1200px 0px'}).observe(st);
})();
const _body=fx.body;fx.body=function(p,el){B3.p=p;if(!B3.ready)return _body(p,el);
 const bt=$('#btitle'),q=seg(p,.12,.2);bt.style.opacity=1-q;bt.style.transform=`translateY(${-q*40}px)`;
 const be=$('#bend'),t=EO(seg(p,.88,.97));be.style.opacity=t;be.style.transform=`translateY(${(1-t)*30}px)`};


/* ---------- hero: live flowing light (WebGL shader) ---------- */
(()=>{const cv=document.getElementById('heroGL'),hero=document.getElementById('hero');if(R)return;
 const gl=cv.getContext('webgl',{premultipliedAlpha:false,antialias:false});if(!gl)return;
 const vs='attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}';
 const fs=`precision highp float;uniform vec2 r;uniform float t;uniform vec2 m;uniform float fade;
 float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
 float n(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),u.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),u.x),u.y);}
 float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*n(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
 void main(){vec2 uv=gl_FragCoord.xy/r;vec2 p=(gl_FragCoord.xy-.5*r)/r.y;
  vec2 q=vec2(fbm(p*1.6+t*.05),fbm(p*1.6-t*.04+3.1));
  vec2 w=vec2(fbm(p*1.3+2.*q+vec2(1.7,9.2)+t*.03+m*.6),fbm(p*1.3+2.*q+vec2(8.3,2.8)-t*.035-m*.4));
  float f=fbm(p*1.1+2.2*w);
  vec3 c=vec3(0.);
  c=mix(c,vec3(.05,.10,.55),smoothstep(.25,.75,f));
  c=mix(c,vec3(.38,.22,.95),smoothstep(.45,.9,length(w)*.9)*.75);
  c=mix(c,vec3(.95,.30,.58),smoothstep(.62,1.,w.y*1.15)*.55);
  float glow=exp(-3.5*length(p-vec2(m.x*.5,m.y*.35-.1)));c+=vec3(.25,.3,.9)*glow*.25;
  c*=smoothstep(1.25,.25,length(p*vec2(.8,1.1)));
  c*=.62*fade;
  gl_FragColor=vec4(pow(c,vec3(.95)),1.);}`;
 const sh=(type,src)=>{const o=gl.createShader(type);gl.shaderSource(o,src);gl.compileShader(o);if(!gl.getShaderParameter(o,gl.COMPILE_STATUS))throw gl.getShaderInfoLog(o);return o};
 let pr;try{pr=gl.createProgram();gl.attachShader(pr,sh(gl.VERTEX_SHADER,vs));gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);gl.useProgram(pr)}catch(e){console.warn(e);return}
 const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
 const loc=gl.getAttribLocation(pr,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
 const uR=gl.getUniformLocation(pr,'r'),uT=gl.getUniformLocation(pr,'t'),uM=gl.getUniformLocation(pr,'m'),uF=gl.getUniformLocation(pr,'fade');
 let mx=0,my=0,tx=0,ty=0,vis=true;const sc=.6;
 const size=()=>{const w=cv.clientWidth,h=cv.clientHeight,d=Math.min(1.5,devicePixelRatio||1)*sc;cv.width=w*d;cv.height=h*d;gl.viewport(0,0,cv.width,cv.height)};
 size();addEventListener('resize',size);
 hero.addEventListener('pointermove',e=>{tx=e.clientX/innerWidth-.5;ty=-(e.clientY/innerHeight-.5)});
 new IntersectionObserver(es=>{vis=es[0].isIntersecting}).observe(cv);
 hero.classList.add('gl');const t0=performance.now();
 const tick=now=>{requestAnimationFrame(tick);if(!vis)return;mx+=(tx-mx)*.04;my+=(ty-my)*.04;
  gl.uniform2f(uR,cv.width,cv.height);gl.uniform1f(uT,(now-t0)/1000);gl.uniform2f(uM,mx,my);gl.uniform1f(uF,1-(heroField._fadeOut||0));gl.drawArrays(gl.TRIANGLES,0,3)};
 requestAnimationFrame(tick)})();

/* ---------- hero phone with real thickness ---------- */
const P3=(()=>{const ph=document.getElementById('hph'),wrap=document.createElement('div');wrap.className='p3d';ph.parentNode.insertBefore(wrap,ph);
 for(let i=1;i<=12;i++){const l=document.createElement('div');l.className='ly';l.style.transform=`translateZ(${-i*.9}px)`;wrap.appendChild(l)}
 wrap.appendChild(ph);const g=document.createElement('i');g.className='gloss';ph.querySelector('.scr').appendChild(g);
 let mx=0,my=0;document.getElementById('hero').addEventListener('pointermove',e=>{mx=e.clientX/innerWidth-.5;my=e.clientY/innerHeight-.5});
 return{wrap,gloss:g,get mx(){return mx},get my(){return my}}})();


/* ---------- week-24 baby (the app's own model) ---------- */
(()=>{const cv=document.getElementById('baby3d');if(!cv)return;let started=false,vis=false;
 const go=async()=>{try{await (window.UH_LIBS?window.UH_LIBS():0);const T=window.THREE;if(!T||!T.GLTFLoader||!window.MeshoptDecoder)return;await MeshoptDecoder.ready;
  const src=window.UH_BABY;const ab=typeof src==='string'&&src.startsWith('/')?await (await fetch(src)).arrayBuffer():(()=>{const b=atob(src),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer})();
  const R2=new T.WebGLRenderer({canvas:cv,antialias:true,alpha:true});R2.setPixelRatio(Math.min(devicePixelRatio,2));R2.outputEncoding=T.sRGBEncoding;R2.toneMapping=T.ACESFilmicToneMapping;R2.toneMappingExposure=1.05;
  const sc=new T.Scene();sc.add(new T.HemisphereLight(0xfff8f2,0x8a7f78,.75));const k=new T.DirectionalLight(0xfff4ec,1.2);k.position.set(3,6,7);sc.add(k);const k2=new T.DirectionalLight(0xffc6d8,.6);k2.position.set(-6,1,4);sc.add(k2);
  const cam=new T.PerspectiveCamera(26,1,.1,100);cam.position.set(0,0,8.2);
  const L=new T.GLTFLoader();L.setMeshoptDecoder(MeshoptDecoder);
  L.parse(ab,'',g=>{const m=g.scene;m.traverse(o=>{if(o.isMesh)o.frustumCulled=false});m.updateMatrixWorld(true);const bb=new T.Box3().setFromObject(m),c=bb.getCenter(new T.Vector3()),sz=bb.getSize(new T.Vector3());
   const wrap=new T.Group();m.position.copy(c).multiplyScalar(-1);wrap.add(m);wrap.scale.setScalar(2.6/Math.max(sz.x,sz.y,sz.z));sc.add(wrap);
   const fl=g.animations.find(a=>a.name==='Float'),mx=fl?new T.AnimationMixer(m):null;if(mx)mx.clipAction(fl).play();
   const size=()=>{const w=cv.clientWidth;R2.setSize(w,w,false)};size();addEventListener('resize',size);let last=performance.now();
   const loop=now=>{requestAnimationFrame(loop);if(!vis)return;const dt=Math.min(.05,(now-last)/1000);last=now;if(mx)mx.update(dt);wrap.rotation.y=Math.sin(now/2600)*.5;R2.render(sc,cam)};requestAnimationFrame(loop)},e=>console.warn('baby',e))
 }catch(e){console.warn('baby',e)}};
 new IntersectionObserver(es=>{vis=es[0].isIntersecting;if(vis&&!started){started=true;go()}},{rootMargin:'600px'}).observe(cv)})();


/* ---------- languages: English, Telugu, Tamil ---------- */
const I18N={"te": {"Skip to content": "కంటెంట్‌కి వెళ్ళండి", "Overview": "పరిచయం", "How it works": "ఎలా పనిచేస్తుంది", "Family": "కుటుంబం", "Privacy": "గోప్యత", "FAQ": "ప్రశ్నలు", "Open app": "యాప్ తెరవండి", "Your family's health.": "మీ కుటుంబ ఆరోగ్యం.", "In one secure place.": "ఒకే సురక్షిత చోట.", "Reports, medicines, visits and emergency details for everyone you love, explained in simple words.": "మీరు ప్రేమించే అందరి రిపోర్టులు, మందులు, డాక్టర్ విజిట్‌లు, అత్యవసర వివరాలు — సులభమైన మాటల్లో.", "Get started, free": "ఉచితంగా ప్రారంభించండి", "Haemoglobin is normal": "హిమోగ్లోబిన్ సాధారణంగా ఉంది", "Blood report, read in plain words": "బ్లడ్ రిపోర్ట్, సులభమైన మాటల్లో", "Thyroid tablet reminder": "థైరాయిడ్ టాబ్లెట్ గుర్తు", "SOS ready": "SOS సిద్ధం", "Blood group B+ · 1 contact": "బ్లడ్ గ్రూప్ B+ · 1 కాంటాక్ట్", "Scroll": "స్క్రోల్", "See your health.": "మీ ఆరోగ్యాన్ని చూడండి.", "On your body.": "మీ శరీరంపైనే.", "Every report lights up where it belongs. Green is good. Amber means take care.": "ప్రతి రిపోర్ట్ శరీరంలో దాని స్థానంలో వెలుగుతుంది. ఆకుపచ్చ అంటే బాగుంది. పసుపు అంటే జాగ్రత్త.", "Lungs": "ఊపిరితిత్తులు", "Breathing well": "శ్వాస బాగుంది", "Liver": "కాలేయం", "Values in range": "విలువలు సరిగ్గా ఉన్నాయి", "Kidneys": "మూత్రపిండాలు", "Drink a little more water": "కొంచెం ఎక్కువ నీళ్ళు తాగండి", "Digestion": "జీర్ణక్రియ", "All looks good": "అంతా బాగుంది", "Heart · 72 bpm · regular": "గుండె · 72 bpm · క్రమంగా", "Every beat, understood.": "ప్రతి గుండె చప్పుడు, అర్థమయ్యేలా.", "Reports explained in plain words. Your doctor always has the final word.": "రిపోర్టులు సులభమైన మాటల్లో. తుది నిర్ణయం ఎప్పుడూ మీ డాక్టర్‌దే.", "Every detail that matters.": "ముఖ్యమైన ప్రతి వివరం.", "One hold away.": "ఒక్క నొక్కుతో.", "Blood group, allergies and the people to call, ready on your lock screen. In an emergency, help knows who you are.": "బ్లడ్ గ్రూప్, అలర్జీలు, ఫోన్ చేయాల్సిన వాళ్ళు — మీ లాక్ స్క్రీన్‌పైనే. అత్యవసరంలో సహాయం చేసేవారికి మీరెవరో తెలుస్తుంది.", "Blood group": "బ్లడ్ గ్రూప్", "Allergies": "అలర్జీలు", "Contacts": "కాంటాక్ట్‌లు", "Step 1 · Snap": "దశ 1 · ఫోటో", "Take a photo of your report.": "మీ రిపోర్ట్‌ని ఫోటో తీయండి.", "Any lab, any hospital, any city. A photo or a PDF is enough. Labs can also send reports through a secure link that you approve.": "ఏ ల్యాబ్ అయినా, ఏ ఆసుపత్రి అయినా, ఏ ఊరైనా. ఒక ఫోటో లేదా PDF చాలు. మీరు అనుమతించిన సురక్షిత లింక్ ద్వారా ల్యాబ్‌లు కూడా పంపవచ్చు.", "Like taking a picture of your homework.": "మీ హోంవర్క్‌ని ఫోటో తీసినట్టే.", "Step 2 · Understand": "దశ 2 · అర్థం చేసుకోండి", "Read in plain words.": "సులభమైన మాటల్లో చదవండి.", "Each value is explained in one sentence: what it means, whether it's in range, and a gentle suggestion.": "ప్రతి విలువను ఒక్క వాక్యంలో చెబుతాం: దాని అర్థం ఏంటి, సరిగ్గా ఉందా, ఏం చేయాలో ఒక చిన్న సూచన.", "Like a kind teacher: \"this part is fine, this needs care\".": "దయగల టీచర్ చెప్పినట్టు: \"ఇది బాగుంది, ఇది కొంచెం జాగ్రత్త\".", "Step 3 · See": "దశ 3 · చూడండి", "See it on your body.": "మీ శరీరంపై చూడండి.", "Results light up on a 3D body, so you see what's good and what to watch, at a glance.": "ఫలితాలు 3D శరీరంపై వెలుగుతాయి, ఏది బాగుందో ఏది గమనించాలో ఒక్క చూపులో తెలుస్తుంది.", "Like a map with green and amber dots.": "ఆకుపచ్చ, పసుపు చుక్కలున్న మ్యాప్‌లా.", "Step 4 · Act": "దశ 4 · ముందడుగు", "Take the next step.": "తర్వాతి అడుగు వేయండి.", "Book a test at home, meet a registered doctor, remind your parents about medicines, and keep help one hold away.": "ఇంటి వద్దే టెస్ట్ బుక్ చేయండి, రిజిస్టర్డ్ డాక్టర్‌ని కలవండి, అమ్మానాన్నలకు మందుల గుర్తు పెట్టండి, సహాయం ఒక్క నొక్కు దూరంలో.", "Like a helper who knows what to do next.": "తర్వాత ఏం చేయాలో తెలిసిన సహాయకుడిలా.", "5 values read": "5 విలువలు చదివాం", "Explained in plain words": "సులభమైన మాటల్లో వివరణ", "Your blood carries oxygen well.": "మీ రక్తం ఆక్సిజన్‌ని బాగా తీసుకెళ్తోంది.", "Thyroid is in range": "థైరాయిడ్ సరిగ్గా ఉంది", "TSH 2.1, nothing to worry about.": "TSH 2.1, ఆందోళన అవసరం లేదు.", "Vitamin D is a little low": "విటమిన్ D కొంచెం తక్కువగా ఉంది", "Morning sunlight helps. Ask your doctor about a supplement.": "ఉదయం ఎండ మంచిది. సప్లిమెంట్ గురించి మీ డాక్టర్‌ని అడగండి.", "Suggested next step": "సూచించిన తర్వాతి అడుగు", "Re-test Vitamin D in 3 months, at home.": "3 నెలల తర్వాత విటమిన్ D మళ్ళీ ఇంటి వద్దే టెస్ట్ చేయించండి.", "Lungs · good": "ఊపిరితిత్తులు · బాగున్నాయి", "Liver · good": "కాలేయం · బాగుంది", "Kidneys · care": "మూత్రపిండాలు · జాగ్రత్త", "Test at home": "ఇంటి వద్దే టెస్ట్", "Technician at your door": "టెక్నీషియన్ మీ ఇంటికే", "Tomorrow · 7:00 AM": "రేపు · ఉదయం 7:00", "See a doctor": "డాక్టర్‌ని కలవండి", "Registered doctors only": "రిజిస్టర్డ్ డాక్టర్లు మాత్రమే", "Video or in person": "వీడియోలో లేదా నేరుగా", "Medicines": "మందులు", "Reminders for family": "కుటుంబానికి గుర్తులు", "Next dose · 8:00 PM": "తర్వాతి డోస్ · రాత్రి 8:00", "Emergency": "అత్యవసరం", "One hold calls for help": "ఒక్క నొక్కుతో సహాయం", "Ready · B+ · 1 contact": "సిద్ధం · B+ · 1 కాంటాక్ట్", "Ravi is on the way": "రవి దారిలో ఉన్నారు", "Verified technician · partner lab": "ధృవీకరించిన టెక్నీషియన్ · భాగస్వామి ల్యాబ్", "min": "నిమి", "Your report is ready": "మీ రిపోర్ట్ సిద్ధం", "Haemoglobin is normal. Vitamin D is a little low.": "హిమోగ్లోబిన్ సాధారణం. విటమిన్ D కొంచెం తక్కువ.", "now": "ఇప్పుడే", "Lab at home": "ఇంటి వద్దే ల్యాబ్", "Tests at your door.": "టెస్టులు మీ ఇంటి వద్దే.", "Reports in your pocket.": "రిపోర్టులు మీ జేబులో.", "Pick a time. A trained technician from a partner lab comes home, and you can follow every step until the report arrives, already explained.": "సమయం ఎంచుకోండి. భాగస్వామి ల్యాబ్ నుండి శిక్షణ పొందిన టెక్నీషియన్ ఇంటికి వస్తారు. రిపోర్ట్ వివరణతో వచ్చే వరకు ప్రతి దశను చూడవచ్చు.", "Booked": "బుక్ అయింది", "Thyroid and vitamin profile": "థైరాయిడ్, విటమిన్ ప్రొఫైల్", "On the way": "దారిలో", "Live location, shared only during the visit": "లైవ్ లొకేషన్, విజిట్ సమయంలో మాత్రమే", "Sample collected at home": "ఇంటి వద్దే శాంపిల్ తీసుకున్నారు", "Sealed and labelled in front of you": "మీ ముందే సీల్, లేబుల్", "At the lab": "ల్యాబ్‌లో", "Tested at a partner laboratory": "భాగస్వామి ల్యాబ్‌లో పరీక్ష", "Report ready": "రిపోర్ట్ సిద్ధం", "Explained in plain words, shown on your body": "సులభమైన మాటల్లో, మీ శరీరంపై", "One family.": "ఒకే కుటుంబం.", "One secure place.": "ఒకే సురక్షిత చోటు.", "Add the people you care for. Each gets their own profile, and you decide who sees what.": "మీరు చూసుకునే వాళ్ళను చేర్చండి. ప్రతి ఒక్కరికీ సొంత ప్రొఫైల్, ఎవరు ఏం చూడాలో మీరే నిర్ణయిస్తారు.", "Meera · You": "మీరా · మీరు", "Amma": "అమ్మ", "Tablet taken": "టాబ్లెట్ వేసుకున్నారు", "Nanna": "నాన్న", "BP check due": "BP చెక్ చేయాలి", "Arjun": "అర్జున్", "All good": "అంతా బాగుంది", "Kavya, 6": "కావ్య, 6", "Vaccine in 5 days": "5 రోజుల్లో టీకా", "And the littlest ones, too.": "చిన్నారుల కోసం కూడా.", "Profiles for children are created and looked after by a parent.": "పిల్లల ప్రొఫైల్‌లను తల్లిదండ్రులే సృష్టించి చూసుకుంటారు.", "Birth": "పుట్టినప్పుడు", "Kavya's vaccines": "కావ్య టీకాలు", "Reminder sent to Meera": "మీరాకు గుర్తు పంపాం", "For kids": "పిల్లల కోసం", "Every vaccine.": "ప్రతి టీకా.", "Right on time.": "సరైన సమయానికి.", "From the first day home to the first day of school, each dose fills a ring, and a gentle reminder arrives before the next one is due.": "ఇంటికి వచ్చిన మొదటి రోజు నుండి బడికి వెళ్ళే మొదటి రోజు వరకు, ప్రతి డోస్ ఒక వలయాన్ని నింపుతుంది. తర్వాతి డోస్ ముందు మీకు గుర్తు వస్తుంది.", "At birth": "పుట్టినప్పుడు", "A safe start.": "సురక్షితమైన ఆరంభం.", "6, 10 & 14 weeks": "6, 10, 14 వారాలు", "The first big round.": "మొదటి పెద్ద విడత.", "9 to 12 months": "9 నుండి 12 నెలలు", "Growing stronger.": "మరింత బలంగా.", "16 to 24 months": "16 నుండి 24 నెలలు", "Boosters, on time.": "బూస్టర్లు, సమయానికి.", "5 to 6 years": "5 నుండి 6 ఏళ్ళు", "Ready for school.": "బడికి సిద్ధం.", "Shown as per India's Universal Immunisation Programme. Some vaccines depend on your area, and your paediatrician may suggest more.": "భారత సార్వత్రిక టీకా కార్యక్రమం ప్రకారం చూపించాం. కొన్ని టీకాలు మీ ప్రాంతాన్ని బట్టి ఉంటాయి, మీ పిల్లల డాక్టర్ మరికొన్ని సూచించవచ్చు.", "Everything your family needs.": "మీ కుటుంబానికి కావాల్సినదంతా.", "Nothing it doesn't. One secure app, from a newborn's vaccines to a grandparent's tablets.": "అనవసరమైనది ఏదీ లేదు. పసిపిల్లల టీకాల నుండి తాతయ్య మందుల వరకు, ఒకే సురక్షిత యాప్.", "Medical ID": "మెడికల్ ID", "Help that knows who you are.": "మీరెవరో తెలిసిన సహాయం.", "On your lock screen, even offline.": "మీ లాక్ స్క్రీన్‌పై, ఇంటర్నెట్ లేకపోయినా.", "A trained technician comes home. Reports land in your pocket.": "శిక్షణ పొందిన టెక్నీషియన్ ఇంటికి వస్తారు. రిపోర్టులు మీ జేబులోకి.", "Never miss a dose.": "ఏ డోస్ మిస్ కాకుండా.", "Reminders for you, and for Amma and Nanna, even from far away.": "మీకూ, దూరంలో ఉన్న అమ్మానాన్నలకూ గుర్తులు.", "Thyroid · 1 tablet": "థైరాయిడ్ · 1 టాబ్లెట్", "7:00 AM · before food": "ఉదయం 7:00 · భోజనానికి ముందు", "Vitamin D · weekly": "విటమిన్ D · వారానికి ఒకసారి", "1:00 PM · after lunch": "మధ్యాహ్నం 1:00 · భోజనం తర్వాత", "BP · 1 tablet": "BP · 1 టాబ్లెట్", "8:00 PM · after dinner": "రాత్రి 8:00 · భోజనం తర్వాత", "Insurance": "ఇన్సూరెన్స్", "Know your cover.": "మీ కవరేజ్ తెలుసుకోండి.", "Cards ready at the hospital desk, and a quick check for Ayushman Bharat or your state's scheme.": "ఆసుపత్రి కౌంటర్ వద్ద కార్డులు సిద్ధం, ఆయుష్మాన్ భారత్ లేదా మీ రాష్ట్ర పథకానికి త్వరిత తనిఖీ.", "Visits": "విజిట్‌లు", "Doctor visits, without the wait.": "వేచి ఉండకుండా డాక్టర్ విజిట్‌లు.", "The hospital confirms your time, and you see a live token on the day.": "ఆసుపత్రి మీ సమయాన్ని నిర్ధారిస్తుంది, ఆ రోజు లైవ్ టోకెన్ చూడవచ్చు.", "Pregnancy & kids": "గర్భధారణ & పిల్లలు", "From first scan to first steps.": "మొదటి స్కాన్ నుండి మొదటి అడుగుల వరకు.", "Week-by-week guidance, then vaccines with gentle reminders.": "వారం వారం మార్గదర్శనం, ఆ తర్వాత టీకాల గుర్తులు.", "Week 24 of 40": "40 లో 24వ వారం", "About the size of a corn cob": "దాదాపు మొక్కజొన్న కంకి అంత", "Your language": "మీ భాష", "Speaks like home.": "ఇంటి భాషలోనే.", "Read and listen in the language your family is most comfortable with.": "మీ కుటుంబానికి సౌకర్యమైన భాషలో చదవండి, వినండి.", "More Indian languages coming": "మరిన్ని భారతీయ భాషలు త్వరలో", "Hold for one second.": "ఒక్క సెకను నొక్కి పట్టండి.", "That's all it takes to reach the people who matter.": "మీ వాళ్ళను చేరుకోవడానికి అంతే చాలు.", "Calls 112": "112కి కాల్", "Alerts your family": "కుటుంబానికి సమాచారం", "Shares where you are": "మీరెక్కడున్నారో పంపుతుంది", "Shows your Medical ID": "మీ మెడికల్ ID చూపిస్తుంది", "If you can, always call 112 directly in an emergency. For an ambulance, call 108.": "వీలైతే, అత్యవసరంలో నేరుగా 112కి కాల్ చేయండి. అంబులెన్స్ కోసం 108.", "On your phone.": "మీ ఫోన్‌లో.", "And on your desk.": "మీ కంప్యూటర్‌లోనూ.", "The same secure view in any browser. Nothing to install.": "ఏ బ్రౌజర్‌లోనైనా అదే సురక్షిత వీక్షణ. ఏమీ ఇన్‌స్టాల్ చేయనక్కర్లేదు.", "Locked. And kept in India.": "భద్రంగా. భారత్‌లోనే.", "Your health is yours. We collect only what helps you, ask before we use it, and let you take it back.": "మీ ఆరోగ్యం మీదే. మీకు ఉపయోగపడేదే సేకరిస్తాం, వాడే ముందు అడుగుతాం, కావాలంటే తిరిగి తీసుకోవచ్చు.", "Kept in India": "భారత్‌లోనే", "Health records are stored in data centres in Mumbai, on Google Cloud.": "ఆరోగ్య రికార్డులు ముంబైలోని Google Cloud డేటా సెంటర్లలో భద్రపరుస్తాం.", "Your data doesn't travel abroad.": "మీ డేటా విదేశాలకు వెళ్ళదు.", "Encrypted": "ఎన్‌క్రిప్ట్ చేయబడింది", "Everything travels over HTTPS and is encrypted where it is stored.": "అంతా HTTPS ద్వారా వెళ్తుంది, భద్రపరిచే చోట ఎన్‌క్రిప్ట్ చేస్తాం.", "Like a letter in a locked box.": "తాళం వేసిన పెట్టెలో ఉత్తరంలా.", "Consent first": "ముందు మీ అనుమతి", "You choose what the app may use, and can change it anytime. Each consent is recorded with time and purpose.": "యాప్ ఏం వాడాలో మీరే ఎంచుకుంటారు, ఎప్పుడైనా మార్చవచ్చు. ప్రతి అనుమతి సమయం, ఉద్దేశంతో నమోదవుతుంది.", "We always ask before we touch.": "తాకే ముందు ఎప్పుడూ అడుగుతాం.", "You decide who sees": "ఎవరు చూడాలో మీ నిర్ణయం", "Share a report with a doctor for a set time, and it closes by itself. You can see everyone with access.": "డాక్టర్‌తో నిర్ణీత సమయం వరకు రిపోర్ట్ పంచుకోండి, తర్వాత అదే మూసుకుంటుంది. యాక్సెస్ ఉన్న అందరినీ చూడవచ్చు.", "Like lending a book and getting it back.": "పుస్తకం ఇచ్చి తిరిగి తీసుకున్నట్టు.", "Strong sign-in for our team": "మా టీమ్‌కి బలమైన సైన్-ఇన్", "Staff use an authenticator app, roles limit what each person can open, and access is written to an audit log.": "సిబ్బంది ఆథెంటికేటర్ యాప్ వాడతారు, ఒక్కొక్కరు ఏం తెరవగలరో పరిమితం, ప్రతి యాక్సెస్ ఆడిట్ లాగ్‌లో నమోదవుతుంది.", "Only the right people hold the keys.": "తాళాలు సరైన వాళ్ళ దగ్గరే.", "No ads. No selling.": "ప్రకటనలు లేవు. అమ్మకం లేదు.", "We do not sell personal data or use health records for advertising.": "వ్యక్తిగత డేటాను అమ్మము, ఆరోగ్య రికార్డులను ప్రకటనలకు వాడము.", "Your secrets are not for sale.": "మీ రహస్యాలు అమ్మకానికి కాదు.", "Questions": "ప్రశ్నలు", "Asked by families like yours.": "మీలాంటి కుటుంబాలు అడిగినవి.", "Is Urban Health free to use?": "Urban Health ఉచితమా?", "Creating your account and adding your family is free. Lab tests, consultations and medicines you choose to book are paid to the provider, and the price is always shown before you confirm.": "ఖాతా తెరవడం, కుటుంబాన్ని చేర్చడం ఉచితం. మీరు బుక్ చేసే ల్యాబ్ టెస్టులు, సంప్రదింపులు, మందులకు సేవ అందించేవారికి చెల్లిస్తారు, నిర్ధారించే ముందే ధర చూపిస్తాం.", "In simple words: Starting is free. You see every price before you pay.": "సులభంగా చెప్పాలంటే: ప్రారంభం ఉచితం. చెల్లించే ముందే ప్రతి ధర చూస్తారు.", "Does it replace my doctor?": "ఇది నా డాక్టర్‌కి బదులా?", "No. Urban Health helps you understand and organise your health information. Diagnosis and treatment always come from a registered doctor.": "కాదు. మీ ఆరోగ్య సమాచారాన్ని అర్థం చేసుకోవడానికి, సర్దుకోవడానికి Urban Health సహాయపడుతుంది. రోగనిర్ధారణ, చికిత్స ఎప్పుడూ రిజిస్టర్డ్ డాక్టర్ నుండే.", "In simple words: It explains. Your doctor decides.": "సులభంగా చెప్పాలంటే: ఇది వివరిస్తుంది. నిర్ణయం మీ డాక్టర్‌ది.", "Where is my data stored?": "నా డేటా ఎక్కడ ఉంటుంది?", "Health records are stored in India, in Google Cloud data centres in Mumbai. We do not sell personal data or use it for advertising.": "ఆరోగ్య రికార్డులు భారత్‌లో, ముంబైలోని Google Cloud డేటా సెంటర్లలో ఉంటాయి. వ్యక్తిగత డేటాను అమ్మము, ప్రకటనలకు వాడము.", "In simple words: Your data stays in India.": "సులభంగా చెప్పాలంటే: మీ డేటా భారత్‌లోనే.", "Can I look after my parents and children?": "అమ్మానాన్నలను, పిల్లలను చూసుకోవచ్చా?", "Yes. Add profiles for the people you care for. Parents can use a simple mode with larger text, children's profiles are managed by a parent or guardian, and you decide who can see what.": "అవును. మీరు చూసుకునే వాళ్ళకు ప్రొఫైల్‌లు చేర్చండి. పెద్దలు పెద్ద అక్షరాలతో సులభ మోడ్ వాడవచ్చు, పిల్లల ప్రొఫైల్‌లను తల్లిదండ్రులు లేదా సంరక్షకులు చూసుకుంటారు, ఎవరు ఏం చూడాలో మీరే నిర్ణయిస్తారు.", "In simple words: One app for the whole family.": "సులభంగా చెప్పాలంటే: కుటుంబమంతటికీ ఒకే యాప్.", "Which languages are available?": "ఏ భాషలు ఉన్నాయి?", "English, Telugu and Tamil today, with more Indian languages on the way.": "ప్రస్తుతం ఇంగ్లీష్, తెలుగు, తమిళం. మరిన్ని భారతీయ భాషలు త్వరలో.", "In simple words: Three languages now, more coming.": "సులభంగా చెప్పాలంటే: ఇప్పుడు మూడు భాషలు, మరిన్ని త్వరలో.", "How do I delete my data?": "నా డేటాను ఎలా తొలగించాలి?", "You can delete your account from Settings at any time. Personal data is erased after a short grace period, except what the law requires us to keep.": "సెట్టింగ్స్ నుండి ఎప్పుడైనా ఖాతాను తొలగించవచ్చు. చట్టం ఉంచమన్నది తప్ప, వ్యక్తిగత డేటా కొద్ది వ్యవధి తర్వాత తొలగిపోతుంది.", "In simple words: You can leave whenever you like, and your data leaves with you.": "సులభంగా చెప్పాలంటే: మీకు నచ్చినప్పుడు వెళ్ళవచ్చు, మీ డేటా కూడా మీతోనే వెళ్తుంది.", "What happens when I press SOS?": "SOS నొక్కితే ఏమవుతుంది?", "Holding SOS for one second alerts your emergency contacts with your location and Medical ID, and helps you call 112. If you can, always call 112 directly in an emergency.": "SOSని ఒక్క సెకను నొక్కి పట్టితే మీ అత్యవసర కాంటాక్ట్‌లకు మీ లొకేషన్, మెడికల్ IDతో సమాచారం వెళ్తుంది, 112కి కాల్ చేయడంలో సహాయపడుతుంది. వీలైతే, అత్యవసరంలో నేరుగా 112కి కాల్ చేయండి.", "In simple words: Hold for a second, and your people know.": "సులభంగా చెప్పాలంటే: ఒక్క సెకను నొక్కండి, మీ వాళ్ళకు తెలుస్తుంది.", "Care for everyone": "మీరు ప్రేమించే", "you love.": "అందరినీ చూసుకోండి.", "Securely.": "సురక్షితంగా.", "Set up your family in two minutes. Works on any phone, in your browser.": "రెండు నిమిషాల్లో మీ కుటుంబాన్ని చేర్చండి. ఏ ఫోన్‌లోనైనా, బ్రౌజర్‌లోనే పనిచేస్తుంది.", "Open Urban Health": "Urban Health తెరవండి", "Urban Health helps you understand and organise health information. It does not replace a doctor's advice, diagnosis or treatment.": "ఆరోగ్య సమాచారాన్ని అర్థం చేసుకోవడానికి, సర్దుకోవడానికి Urban Health సహాయపడుతుంది. ఇది డాక్టర్ సలహా, రోగనిర్ధారణ లేదా చికిత్సకు బదులు కాదు.", "In an emergency, call 112, or 108 for an ambulance.": "అత్యవసరంలో 112కి, అంబులెన్స్ కోసం 108కి కాల్ చేయండి.", "Your family's health, in one secure place. Made in India, for families across India.": "మీ కుటుంబ ఆరోగ్యం, ఒకే సురక్షిత చోట. భారత్‌లో తయారైంది, భారత కుటుంబాల కోసం.", "Explore": "అన్వేషించండి", "Features": "ఫీచర్లు", "Open the app": "యాప్ తెరవండి", "Trust": "నమ్మకం", "Privacy & security": "గోప్యత & భద్రత", "Compliance": "నిబంధనలు", "Privacy policy": "గోప్యతా విధానం", "Terms of use": "వినియోగ నిబంధనలు", "Contact": "సంప్రదించండి", "Grievance Officer: same address, subject \"Grievance\"": "ఫిర్యాదుల అధికారి: అదే చిరునామా, విషయం \"Grievance\"", "Urban Health. All rights reserved.": "Urban Health. అన్ని హక్కులూ ప్రత్యేకించబడ్డాయి.", "India": "భారత్", "Ravi has arrived": "రవి వచ్చారు", "Sample collected": "శాంపిల్ తీసుకున్నారు", "14 weeks": "14 వారాలు", "9 months": "9 నెలలు", "18 months": "18 నెలలు", "5 years": "5 ఏళ్ళు", "Next: 6 weeks": "తర్వాత: 6 వారాలు", "Next: 9 months": "తర్వాత: 9 నెలలు", "Next: 16 months": "తర్వాత: 16 నెలలు", "Next: 5 years": "తర్వాత: 5 ఏళ్ళు", "All caught up": "అన్నీ పూర్తి"}, "ta": {"Skip to content": "உள்ளடக்கத்திற்குச் செல்லவும்", "Overview": "அறிமுகம்", "How it works": "எப்படி வேலை செய்கிறது", "Family": "குடும்பம்", "Privacy": "தனியுரிமை", "FAQ": "கேள்விகள்", "Open app": "ஆப்பைத் திறக்கவும்", "Your family's health.": "உங்கள் குடும்பத்தின் ஆரோக்கியம்.", "In one secure place.": "ஒரே பாதுகாப்பான இடத்தில்.", "Reports, medicines, visits and emergency details for everyone you love, explained in simple words.": "நீங்கள் நேசிக்கும் அனைவரின் ரிப்போர்ட்டுகள், மருந்துகள், மருத்துவர் வருகைகள், அவசரத் தகவல்கள் — எளிய வார்த்தைகளில்.", "Get started, free": "இலவசமாகத் தொடங்குங்கள்", "Haemoglobin is normal": "ஹீமோகுளோபின் சரியாக உள்ளது", "Blood report, read in plain words": "இரத்தப் பரிசோதனை, எளிய வார்த்தைகளில்", "Thyroid tablet reminder": "தைராய்டு மாத்திரை நினைவூட்டல்", "SOS ready": "SOS தயார்", "Blood group B+ · 1 contact": "இரத்த வகை B+ · 1 தொடர்பு", "Scroll": "ஸ்க்ரோல்", "See your health.": "உங்கள் ஆரோக்கியத்தைப் பாருங்கள்.", "On your body.": "உங்கள் உடலிலேயே.", "Every report lights up where it belongs. Green is good. Amber means take care.": "ஒவ்வொரு ரிப்போர்ட்டும் உடலில் அதன் இடத்தில் ஒளிரும். பச்சை என்றால் நலம். மஞ்சள் என்றால் கவனம்.", "Lungs": "நுரையீரல்", "Breathing well": "சுவாசம் நன்றாக உள்ளது", "Liver": "கல்லீரல்", "Values in range": "அளவுகள் சரியாக உள்ளன", "Kidneys": "சிறுநீரகங்கள்", "Drink a little more water": "கொஞ்சம் கூடுதலாகத் தண்ணீர் குடியுங்கள்", "Digestion": "செரிமானம்", "All looks good": "எல்லாம் நன்றாக உள்ளது", "Heart · 72 bpm · regular": "இதயம் · 72 bpm · சீராக", "Every beat, understood.": "ஒவ்வொரு துடிப்பும், புரியும்படி.", "Reports explained in plain words. Your doctor always has the final word.": "ரிப்போர்ட்டுகள் எளிய வார்த்தைகளில். இறுதி முடிவு எப்போதும் உங்கள் மருத்துவருடையது.", "Every detail that matters.": "முக்கியமான ஒவ்வொரு விவரமும்.", "One hold away.": "ஒரே அழுத்தத்தில்.", "Blood group, allergies and the people to call, ready on your lock screen. In an emergency, help knows who you are.": "இரத்த வகை, ஒவ்வாமைகள், அழைக்க வேண்டியவர்கள் — உங்கள் லாக் ஸ்கிரீனிலேயே. அவசரத்தில் உதவுபவருக்கு நீங்கள் யார் என்று தெரியும்.", "Blood group": "இரத்த வகை", "Allergies": "ஒவ்வாமைகள்", "Contacts": "தொடர்புகள்", "Step 1 · Snap": "படி 1 · புகைப்படம்", "Take a photo of your report.": "உங்கள் ரிப்போர்ட்டை புகைப்படம் எடுங்கள்.", "Any lab, any hospital, any city. A photo or a PDF is enough. Labs can also send reports through a secure link that you approve.": "எந்த லேபும், எந்த மருத்துவமனையும், எந்த ஊரும். ஒரு புகைப்படம் அல்லது PDF போதும். நீங்கள் அனுமதிக்கும் பாதுகாப்பான இணைப்பின் மூலம் லேப்களும் அனுப்பலாம்.", "Like taking a picture of your homework.": "உங்கள் வீட்டுப்பாடத்தைப் புகைப்படம் எடுப்பது போல.", "Step 2 · Understand": "படி 2 · புரிந்துகொள்ளுங்கள்", "Read in plain words.": "எளிய வார்த்தைகளில் படியுங்கள்.", "Each value is explained in one sentence: what it means, whether it's in range, and a gentle suggestion.": "ஒவ்வொரு அளவையும் ஒரே வாக்கியத்தில் விளக்குகிறோம்: அதன் அர்த்தம், சரியான அளவில் உள்ளதா, ஒரு மென்மையான பரிந்துரை.", "Like a kind teacher: \"this part is fine, this needs care\".": "அன்பான ஆசிரியர் சொல்வது போல: \"இது சரி, இதில் கவனம் தேவை\".", "Step 3 · See": "படி 3 · பாருங்கள்", "See it on your body.": "உங்கள் உடலில் பாருங்கள்.", "Results light up on a 3D body, so you see what's good and what to watch, at a glance.": "முடிவுகள் 3D உடலில் ஒளிரும், எது நலம், எதைக் கவனிக்க வேண்டும் என்று ஒரே பார்வையில் தெரியும்.", "Like a map with green and amber dots.": "பச்சை, மஞ்சள் புள்ளிகள் உள்ள வரைபடம் போல.", "Step 4 · Act": "படி 4 · அடுத்த படி", "Take the next step.": "அடுத்த அடியை எடுங்கள்.", "Book a test at home, meet a registered doctor, remind your parents about medicines, and keep help one hold away.": "வீட்டிலேயே பரிசோதனை பதிவு செய்யுங்கள், பதிவு பெற்ற மருத்துவரைச் சந்தியுங்கள், பெற்றோருக்கு மருந்து நினைவூட்டுங்கள், உதவி ஒரே அழுத்தத்தில்.", "Like a helper who knows what to do next.": "அடுத்து என்ன செய்ய வேண்டும் என்று தெரிந்த உதவியாளர் போல.", "5 values read": "5 அளவுகள் படிக்கப்பட்டன", "Explained in plain words": "எளிய வார்த்தைகளில் விளக்கம்", "Your blood carries oxygen well.": "உங்கள் இரத்தம் ஆக்சிஜனை நன்றாகக் கொண்டு செல்கிறது.", "Thyroid is in range": "தைராய்டு சரியான அளவில் உள்ளது", "TSH 2.1, nothing to worry about.": "TSH 2.1, கவலைப்பட ஒன்றுமில்லை.", "Vitamin D is a little low": "வைட்டமின் D கொஞ்சம் குறைவாக உள்ளது", "Morning sunlight helps. Ask your doctor about a supplement.": "காலை வெயில் உதவும். சப்ளிமெண்ட் பற்றி உங்கள் மருத்துவரிடம் கேளுங்கள்.", "Suggested next step": "பரிந்துரைக்கப்பட்ட அடுத்த படி", "Re-test Vitamin D in 3 months, at home.": "3 மாதங்களில் வைட்டமின் D-ஐ வீட்டிலேயே மீண்டும் பரிசோதியுங்கள்.", "Lungs · good": "நுரையீரல் · நலம்", "Liver · good": "கல்லீரல் · நலம்", "Kidneys · care": "சிறுநீரகங்கள் · கவனம்", "Test at home": "வீட்டிலேயே பரிசோதனை", "Technician at your door": "டெக்னீஷியன் உங்கள் வீட்டுக்கே", "Tomorrow · 7:00 AM": "நாளை · காலை 7:00", "See a doctor": "மருத்துவரைப் பாருங்கள்", "Registered doctors only": "பதிவு பெற்ற மருத்துவர்கள் மட்டும்", "Video or in person": "வீடியோ அல்லது நேரில்", "Medicines": "மருந்துகள்", "Reminders for family": "குடும்பத்துக்கான நினைவூட்டல்கள்", "Next dose · 8:00 PM": "அடுத்த டோஸ் · இரவு 8:00", "Emergency": "அவசரம்", "One hold calls for help": "ஒரே அழுத்தத்தில் உதவி", "Ready · B+ · 1 contact": "தயார் · B+ · 1 தொடர்பு", "Ravi is on the way": "ரவி வந்துகொண்டிருக்கிறார்", "Verified technician · partner lab": "சரிபார்க்கப்பட்ட டெக்னீஷியன் · கூட்டாளர் லேப்", "min": "நிமி", "Your report is ready": "உங்கள் ரிப்போர்ட் தயார்", "Haemoglobin is normal. Vitamin D is a little low.": "ஹீமோகுளோபின் சரி. வைட்டமின் D கொஞ்சம் குறைவு.", "now": "இப்போது", "Lab at home": "வீட்டிலேயே லேப்", "Tests at your door.": "பரிசோதனைகள் உங்கள் வீட்டு வாசலில்.", "Reports in your pocket.": "ரிப்போர்ட்டுகள் உங்கள் பாக்கெட்டில்.", "Pick a time. A trained technician from a partner lab comes home, and you can follow every step until the report arrives, already explained.": "நேரத்தைத் தேர்வு செய்யுங்கள். கூட்டாளர் லேபிலிருந்து பயிற்சி பெற்ற டெக்னீஷியன் வீட்டுக்கு வருவார். விளக்கத்துடன் ரிப்போர்ட் வரும் வரை ஒவ்வொரு படியையும் பார்க்கலாம்.", "Booked": "பதிவானது", "Thyroid and vitamin profile": "தைராய்டு, வைட்டமின் பரிசோதனை", "On the way": "வழியில்", "Live location, shared only during the visit": "நேரடி இருப்பிடம், வருகையின் போது மட்டும்", "Sample collected at home": "வீட்டிலேயே மாதிரி எடுக்கப்பட்டது", "Sealed and labelled in front of you": "உங்கள் முன்பே சீல், லேபிள்", "At the lab": "லேபில்", "Tested at a partner laboratory": "கூட்டாளர் லேபில் பரிசோதனை", "Report ready": "ரிப்போர்ட் தயார்", "Explained in plain words, shown on your body": "எளிய வார்த்தைகளில், உங்கள் உடலில்", "One family.": "ஒரே குடும்பம்.", "One secure place.": "ஒரே பாதுகாப்பான இடம்.", "Add the people you care for. Each gets their own profile, and you decide who sees what.": "நீங்கள் கவனித்துக்கொள்பவர்களைச் சேருங்கள். ஒவ்வொருவருக்கும் தனி ப்ரொஃபைல், யார் எதைப் பார்க்கலாம் என்று நீங்களே முடிவு செய்யுங்கள்.", "Meera · You": "மீரா · நீங்கள்", "Amma": "அம்மா", "Tablet taken": "மாத்திரை எடுத்தாயிற்று", "Nanna": "அப்பா", "BP check due": "BP பரிசோதனை வேண்டும்", "Arjun": "அர்ஜுன்", "All good": "எல்லாம் நலம்", "Kavya, 6": "காவ்யா, 6", "Vaccine in 5 days": "5 நாட்களில் தடுப்பூசி", "And the littlest ones, too.": "குழந்தைகளுக்கும் தான்.", "Profiles for children are created and looked after by a parent.": "குழந்தைகளின் ப்ரொஃபைல்களை பெற்றோரே உருவாக்கி கவனித்துக்கொள்கிறார்கள்.", "Birth": "பிறப்பு", "Kavya's vaccines": "காவ்யாவின் தடுப்பூசிகள்", "Reminder sent to Meera": "மீராவுக்கு நினைவூட்டல் அனுப்பப்பட்டது", "For kids": "குழந்தைகளுக்கு", "Every vaccine.": "ஒவ்வொரு தடுப்பூசியும்.", "Right on time.": "சரியான நேரத்தில்.", "From the first day home to the first day of school, each dose fills a ring, and a gentle reminder arrives before the next one is due.": "வீட்டுக்கு வந்த முதல் நாளிலிருந்து பள்ளியின் முதல் நாள் வரை, ஒவ்வொரு டோஸும் ஒரு வளையத்தை நிரப்பும். அடுத்த டோஸுக்கு முன் நினைவூட்டல் வரும்.", "At birth": "பிறக்கும் போது", "A safe start.": "பாதுகாப்பான தொடக்கம்.", "6, 10 & 14 weeks": "6, 10, 14 வாரங்கள்", "The first big round.": "முதல் பெரிய சுற்று.", "9 to 12 months": "9 முதல் 12 மாதங்கள்", "Growing stronger.": "இன்னும் வலிமையாக.", "16 to 24 months": "16 முதல் 24 மாதங்கள்", "Boosters, on time.": "பூஸ்டர்கள், சரியான நேரத்தில்.", "5 to 6 years": "5 முதல் 6 வயது", "Ready for school.": "பள்ளிக்குத் தயார்.", "Shown as per India's Universal Immunisation Programme. Some vaccines depend on your area, and your paediatrician may suggest more.": "இந்தியாவின் உலகளாவிய நோய்த்தடுப்புத் திட்டத்தின்படி காட்டப்பட்டுள்ளது. சில தடுப்பூசிகள் உங்கள் பகுதியைப் பொறுத்தது, உங்கள் குழந்தை மருத்துவர் மேலும் பரிந்துரைக்கலாம்.", "Everything your family needs.": "உங்கள் குடும்பத்துக்குத் தேவையான அனைத்தும்.", "Nothing it doesn't. One secure app, from a newborn's vaccines to a grandparent's tablets.": "தேவையற்றது எதுவும் இல்லை. பச்சிளம் குழந்தையின் தடுப்பூசி முதல் தாத்தாவின் மாத்திரை வரை, ஒரே பாதுகாப்பான ஆப்.", "Medical ID": "மருத்துவ ID", "Help that knows who you are.": "நீங்கள் யார் என்று தெரிந்த உதவி.", "On your lock screen, even offline.": "உங்கள் லாக் ஸ்கிரீனில், இணையம் இல்லாவிட்டாலும்.", "A trained technician comes home. Reports land in your pocket.": "பயிற்சி பெற்ற டெக்னீஷியன் வீட்டுக்கு வருவார். ரிப்போர்ட்டுகள் உங்கள் பாக்கெட்டுக்கு.", "Never miss a dose.": "எந்த டோஸையும் தவறவிடாதீர்கள்.", "Reminders for you, and for Amma and Nanna, even from far away.": "உங்களுக்கும், தொலைவில் உள்ள அம்மா அப்பாவுக்கும் நினைவூட்டல்கள்.", "Thyroid · 1 tablet": "தைராய்டு · 1 மாத்திரை", "7:00 AM · before food": "காலை 7:00 · உணவுக்கு முன்", "Vitamin D · weekly": "வைட்டமின் D · வாரம் ஒருமுறை", "1:00 PM · after lunch": "மதியம் 1:00 · மதிய உணவுக்குப் பின்", "BP · 1 tablet": "BP · 1 மாத்திரை", "8:00 PM · after dinner": "இரவு 8:00 · இரவு உணவுக்குப் பின்", "Insurance": "காப்பீடு", "Know your cover.": "உங்கள் காப்பீட்டை அறியுங்கள்.", "Cards ready at the hospital desk, and a quick check for Ayushman Bharat or your state's scheme.": "மருத்துவமனை கவுண்டரில் கார்டுகள் தயார், ஆயுஷ்மான் பாரத் அல்லது உங்கள் மாநிலத் திட்டத்துக்கு விரைவான சரிபார்ப்பு.", "Visits": "வருகைகள்", "Doctor visits, without the wait.": "காத்திருப்பு இல்லாத மருத்துவர் வருகைகள்.", "The hospital confirms your time, and you see a live token on the day.": "மருத்துவமனை உங்கள் நேரத்தை உறுதி செய்யும், அன்று நேரடி டோக்கனைப் பார்க்கலாம்.", "Pregnancy & kids": "கர்ப்பம் & குழந்தைகள்", "From first scan to first steps.": "முதல் ஸ்கேன் முதல் முதல் அடிகள் வரை.", "Week-by-week guidance, then vaccines with gentle reminders.": "வாரவாரியான வழிகாட்டல், பிறகு தடுப்பூசி நினைவூட்டல்கள்.", "Week 24 of 40": "40-இல் 24வது வாரம்", "About the size of a corn cob": "சுமார் ஒரு சோளக்கதிர் அளவு", "Your language": "உங்கள் மொழி", "Speaks like home.": "வீட்டு மொழியிலேயே.", "Read and listen in the language your family is most comfortable with.": "உங்கள் குடும்பத்துக்கு வசதியான மொழியில் படியுங்கள், கேளுங்கள்.", "More Indian languages coming": "மேலும் இந்திய மொழிகள் விரைவில்", "Hold for one second.": "ஒரு வினாடி அழுத்திப் பிடியுங்கள்.", "That's all it takes to reach the people who matter.": "உங்களுக்கு முக்கியமானவர்களை அடைய அது போதும்.", "Calls 112": "112-ஐ அழைக்கும்", "Alerts your family": "குடும்பத்துக்குத் தகவல்", "Shares where you are": "நீங்கள் எங்கே என்று பகிரும்", "Shows your Medical ID": "உங்கள் மருத்துவ ID-ஐக் காட்டும்", "If you can, always call 112 directly in an emergency. For an ambulance, call 108.": "முடிந்தால், அவசரத்தில் நேரடியாக 112-ஐ அழையுங்கள். ஆம்புலன்ஸுக்கு 108.", "On your phone.": "உங்கள் போனில்.", "And on your desk.": "உங்கள் கணினியிலும்.", "The same secure view in any browser. Nothing to install.": "எந்த பிரௌசரிலும் அதே பாதுகாப்பான பார்வை. எதையும் நிறுவத் தேவையில்லை.", "Locked. And kept in India.": "பூட்டப்பட்டு. இந்தியாவிலேயே.", "Your health is yours. We collect only what helps you, ask before we use it, and let you take it back.": "உங்கள் ஆரோக்கியம் உங்களுடையது. உங்களுக்கு உதவுவதை மட்டும் சேகரிக்கிறோம், பயன்படுத்தும் முன் கேட்கிறோம், நீங்கள் திரும்பப் பெறலாம்.", "Kept in India": "இந்தியாவிலேயே", "Health records are stored in data centres in Mumbai, on Google Cloud.": "சுகாதாரப் பதிவுகள் மும்பையில் உள்ள Google Cloud தரவு மையங்களில் சேமிக்கப்படுகின்றன.", "Your data doesn't travel abroad.": "உங்கள் தரவு வெளிநாட்டுக்குச் செல்லாது.", "Encrypted": "குறியாக்கம் செய்யப்பட்டது", "Everything travels over HTTPS and is encrypted where it is stored.": "அனைத்தும் HTTPS வழியாகச் செல்லும், சேமிக்கும் இடத்தில் குறியாக்கம் செய்யப்படும்.", "Like a letter in a locked box.": "பூட்டிய பெட்டியில் உள்ள கடிதம் போல.", "Consent first": "முதலில் உங்கள் ஒப்புதல்", "You choose what the app may use, and can change it anytime. Each consent is recorded with time and purpose.": "ஆப் எதைப் பயன்படுத்தலாம் என்று நீங்களே தேர்வு செய்யுங்கள், எப்போது வேண்டுமானாலும் மாற்றலாம். ஒவ்வொரு ஒப்புதலும் நேரம், நோக்கத்துடன் பதிவாகும்.", "We always ask before we touch.": "தொடும் முன் எப்போதும் கேட்கிறோம்.", "You decide who sees": "யார் பார்க்கலாம் என்பது உங்கள் முடிவு", "Share a report with a doctor for a set time, and it closes by itself. You can see everyone with access.": "மருத்துவருடன் குறிப்பிட்ட நேரத்துக்கு ரிப்போர்ட்டைப் பகிருங்கள், பிறகு தானாக மூடிவிடும். அணுகல் உள்ள அனைவரையும் பார்க்கலாம்.", "Like lending a book and getting it back.": "புத்தகத்தைக் கொடுத்து திரும்பப் பெறுவது போல.", "Strong sign-in for our team": "எங்கள் குழுவுக்கு வலுவான உள்நுழைவு", "Staff use an authenticator app, roles limit what each person can open, and access is written to an audit log.": "ஊழியர்கள் அங்கீகாரச் செயலியைப் பயன்படுத்துகிறார்கள், ஒவ்வொருவரும் எதைத் திறக்கலாம் என்பது வரம்புக்குட்பட்டது, ஒவ்வொரு அணுகலும் தணிக்கைப் பதிவில் பதிவாகும்.", "Only the right people hold the keys.": "சாவிகள் சரியானவர்களிடம் மட்டும்.", "No ads. No selling.": "விளம்பரம் இல்லை. விற்பனை இல்லை.", "We do not sell personal data or use health records for advertising.": "தனிப்பட்ட தரவை விற்பதில்லை, சுகாதாரப் பதிவுகளை விளம்பரத்துக்குப் பயன்படுத்துவதில்லை.", "Your secrets are not for sale.": "உங்கள் ரகசியங்கள் விற்பனைக்கு அல்ல.", "Questions": "கேள்விகள்", "Asked by families like yours.": "உங்களைப் போன்ற குடும்பங்கள் கேட்டவை.", "Is Urban Health free to use?": "Urban Health இலவசமா?", "Creating your account and adding your family is free. Lab tests, consultations and medicines you choose to book are paid to the provider, and the price is always shown before you confirm.": "கணக்கு தொடங்குவதும் குடும்பத்தைச் சேர்ப்பதும் இலவசம். நீங்கள் பதிவு செய்யும் லேப் பரிசோதனைகள், ஆலோசனைகள், மருந்துகளுக்கு சேவை வழங்குநருக்குச் செலுத்துவீர்கள், உறுதி செய்யும் முன்பே விலை காட்டப்படும்.", "In simple words: Starting is free. You see every price before you pay.": "எளிமையாகச் சொன்னால்: தொடக்கம் இலவசம். செலுத்தும் முன்பே ஒவ்வொரு விலையையும் பார்ப்பீர்கள்.", "Does it replace my doctor?": "இது என் மருத்துவருக்கு மாற்றா?", "No. Urban Health helps you understand and organise your health information. Diagnosis and treatment always come from a registered doctor.": "இல்லை. உங்கள் சுகாதாரத் தகவல்களைப் புரிந்துகொள்ளவும் ஒழுங்குபடுத்தவும் Urban Health உதவுகிறது. நோய் கண்டறிதலும் சிகிச்சையும் எப்போதும் பதிவு பெற்ற மருத்துவரிடமிருந்தே.", "In simple words: It explains. Your doctor decides.": "எளிமையாகச் சொன்னால்: இது விளக்கும். முடிவு உங்கள் மருத்துவருடையது.", "Where is my data stored?": "என் தரவு எங்கே சேமிக்கப்படுகிறது?", "Health records are stored in India, in Google Cloud data centres in Mumbai. We do not sell personal data or use it for advertising.": "சுகாதாரப் பதிவுகள் இந்தியாவில், மும்பையில் உள்ள Google Cloud தரவு மையங்களில் சேமிக்கப்படுகின்றன. தனிப்பட்ட தரவை விற்பதில்லை, விளம்பரத்துக்குப் பயன்படுத்துவதில்லை.", "In simple words: Your data stays in India.": "எளிமையாகச் சொன்னால்: உங்கள் தரவு இந்தியாவிலேயே.", "Can I look after my parents and children?": "பெற்றோரையும் குழந்தைகளையும் கவனிக்கலாமா?", "Yes. Add profiles for the people you care for. Parents can use a simple mode with larger text, children's profiles are managed by a parent or guardian, and you decide who can see what.": "ஆம். நீங்கள் கவனிப்பவர்களுக்கு ப்ரொஃபைல்கள் சேருங்கள். பெரியவர்கள் பெரிய எழுத்துகளுடன் எளிய முறையைப் பயன்படுத்தலாம், குழந்தைகளின் ப்ரொஃபைல்களை பெற்றோர் அல்லது பாதுகாவலர் நிர்வகிப்பார்கள், யார் எதைப் பார்க்கலாம் என்று நீங்களே முடிவு செய்யுங்கள்.", "In simple words: One app for the whole family.": "எளிமையாகச் சொன்னால்: முழு குடும்பத்துக்கும் ஒரே ஆப்.", "Which languages are available?": "எந்த மொழிகள் உள்ளன?", "English, Telugu and Tamil today, with more Indian languages on the way.": "இப்போது ஆங்கிலம், தெலுங்கு, தமிழ். மேலும் இந்திய மொழிகள் விரைவில்.", "In simple words: Three languages now, more coming.": "எளிமையாகச் சொன்னால்: இப்போது மூன்று மொழிகள், மேலும் வரவுள்ளன.", "How do I delete my data?": "என் தரவை எப்படி நீக்குவது?", "You can delete your account from Settings at any time. Personal data is erased after a short grace period, except what the law requires us to keep.": "அமைப்புகளில் எப்போது வேண்டுமானாலும் கணக்கை நீக்கலாம். சட்டம் வைத்திருக்கச் சொல்வதைத் தவிர, தனிப்பட்ட தரவு குறுகிய காலத்துக்குப் பின் அழிக்கப்படும்.", "In simple words: You can leave whenever you like, and your data leaves with you.": "எளிமையாகச் சொன்னால்: நீங்கள் விரும்பும் போது விலகலாம், உங்கள் தரவும் உங்களுடனே செல்லும்.", "What happens when I press SOS?": "SOS அழுத்தினால் என்ன நடக்கும்?", "Holding SOS for one second alerts your emergency contacts with your location and Medical ID, and helps you call 112. If you can, always call 112 directly in an emergency.": "SOS-ஐ ஒரு வினாடி அழுத்தினால் உங்கள் அவசரத் தொடர்புகளுக்கு உங்கள் இருப்பிடம், மருத்துவ ID-யுடன் தகவல் செல்லும், 112-ஐ அழைக்க உதவும். முடிந்தால், அவசரத்தில் நேரடியாக 112-ஐ அழையுங்கள்.", "In simple words: Hold for a second, and your people know.": "எளிமையாகச் சொன்னால்: ஒரு வினாடி அழுத்துங்கள், உங்களவர்களுக்குத் தெரியும்.", "Care for everyone": "நீங்கள் நேசிக்கும்", "you love.": "அனைவரையும் கவனியுங்கள்.", "Securely.": "பாதுகாப்பாக.", "Set up your family in two minutes. Works on any phone, in your browser.": "இரண்டு நிமிடங்களில் உங்கள் குடும்பத்தை அமையுங்கள். எந்த போனிலும், பிரௌசரிலேயே வேலை செய்யும்.", "Open Urban Health": "Urban Health-ஐத் திறக்கவும்", "Urban Health helps you understand and organise health information. It does not replace a doctor's advice, diagnosis or treatment.": "சுகாதாரத் தகவல்களைப் புரிந்துகொள்ளவும் ஒழுங்குபடுத்தவும் Urban Health உதவுகிறது. இது மருத்துவரின் ஆலோசனை, நோய் கண்டறிதல் அல்லது சிகிச்சைக்கு மாற்று அல்ல.", "In an emergency, call 112, or 108 for an ambulance.": "அவசரத்தில் 112-ஐ அழையுங்கள், ஆம்புலன்ஸுக்கு 108.", "Your family's health, in one secure place. Made in India, for families across India.": "உங்கள் குடும்பத்தின் ஆரோக்கியம், ஒரே பாதுகாப்பான இடத்தில். இந்தியாவில் உருவானது, இந்தியக் குடும்பங்களுக்காக.", "Explore": "ஆராயுங்கள்", "Features": "அம்சங்கள்", "Open the app": "ஆப்பைத் திறக்கவும்", "Trust": "நம்பிக்கை", "Privacy & security": "தனியுரிமை & பாதுகாப்பு", "Compliance": "விதிமுறைகள்", "Privacy policy": "தனியுரிமைக் கொள்கை", "Terms of use": "பயன்பாட்டு விதிமுறைகள்", "Contact": "தொடர்பு", "Grievance Officer: same address, subject \"Grievance\"": "குறைதீர் அலுவலர்: அதே முகவரி, தலைப்பு \"Grievance\"", "Urban Health. All rights reserved.": "Urban Health. அனைத்து உரிமைகளும் பாதுகாக்கப்பட்டவை.", "India": "இந்தியா", "Ravi has arrived": "ரவி வந்துவிட்டார்", "Sample collected": "மாதிரி எடுக்கப்பட்டது", "14 weeks": "14 வாரங்கள்", "9 months": "9 மாதங்கள்", "18 months": "18 மாதங்கள்", "5 years": "5 வயது", "Next: 6 weeks": "அடுத்து: 6 வாரங்கள்", "Next: 9 months": "அடுத்து: 9 மாதங்கள்", "Next: 16 months": "அடுத்து: 16 மாதங்கள்", "Next: 5 years": "அடுத்து: 5 வயது", "All caught up": "அனைத்தும் முடிந்தது"}},I18W={"te": "చదవలేని రిపోర్టులు. మరిచిపోయే మందులు. ఆసుపత్రుల్లో, ఫైళ్ళలో, ఫోన్లలో చెల్లాచెదురుగా రికార్డులు. కుటుంబ ఆరోగ్యం చూసుకోవడం ఇంత కష్టంగా ఉండకూడదు. *అందుకే *దాన్ని *సులభం *చేశాం.", "ta": "படிக்க முடியாத ரிப்போர்ட்டுகள். தவறவிடும் மருந்துகள். மருத்துவமனைகள், கோப்புகள், போன்களில் சிதறிய பதிவுகள். குடும்பத்தின் ஆரோக்கியத்தைக் கவனிப்பது இவ்வளவு கடினமாக இருக்கக்கூடாது. *அதனால் *நாங்கள் *எளிதாக்கினோம்."},I18N_NOTE={"te": "చట్టపరమైన సారాంశాలు ఇంగ్లీష్‌లో ఉన్నాయి.", "ta": "சட்டச் சுருக்கங்கள் ஆங்கிலத்தில் உள்ளன."};
const tr=t=>{const L=document.documentElement.lang;return (L!=='en'&&I18N[L]&&I18N[L][t])||t};window.__tr=tr;
const ORIG=new WeakMap();
function setLang(L){if(!['en','te','ta'].includes(L))L='en';document.documentElement.lang=L;try{localStorage.setItem('uh-site-lang',L)}catch(_){}
 document.querySelectorAll('.lang button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.l===L));
 const skip=n=>n.closest('svg,script,style,.paper,#india .comp,#india .tl,#policy .acc,#intro,.lang,#wtxt');
 const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
 while(n=w.nextNode()){if(!n.parentElement||skip(n.parentElement))continue;if(!ORIG.has(n))ORIG.set(n,n.textContent);const o=ORIG.get(n),t=o.trim();if(!t)continue;
  const v=L==='en'?t:(I18N[L][t]||t);n.textContent=o.replace(t,v)}
 document.querySelectorAll('[data-note]').forEach(e=>e.textContent=L==='en'?'':I18N_NOTE[L]);
 // the scroll-lit paragraph is rebuilt word by word in the new language
 const src=L==='en'?WT_EN:I18W[L];
 wt.innerHTML=src.split(/\s+/).map(x=>x.startsWith('*')?`<span class="hl">${x.replace(/\*/g,'')}</span>`:`<span>${x}</span>`).join(' ');
 words=[...wt.children];words.forEach(x=>x.setAttribute('aria-hidden','true'));const sr=document.querySelector('.sr');if(sr)sr.textContent=src.replace(/\*/g,'');
 kPrev=-1;scenes.forEach(x=>x.p=-1)}
document.querySelectorAll('.lang button').forEach(b=>b.addEventListener('click',()=>setLang(b.dataset.l)));
{const q=new URLSearchParams(location.search).get('lang');let st=null;try{st=localStorage.getItem('uh-site-lang')}catch(_){}const L=q||st;if(L&&L!=='en')setLang(L)}


/* ---------- people photos: section appears only when all four real photos load (?photos=draft shows the frames) ---------- */
(()=>{const sec=document.getElementById('people');if(!sec)return;const draft=new URLSearchParams(location.search).get('photos')==='draft';
 if(draft){sec.hidden=false;sec.classList.add('draft');return}
 if(location.protocol==='file:')return;
 // people/ready.json is added together with the four photos; until then nothing is requested
 fetch('/s/preview/people/ready.json',{cache:'no-cache'}).then(r=>r.ok?r.json():null).then(j=>{if(!j||!j.ready)return;
  sec.querySelectorAll('img[data-src]').forEach(im=>im.src=im.dataset.src);sec.hidden=false}).catch(()=>{});
})();

/* intro done */
setTimeout(()=>document.body.classList.add('ready'),R?0:1300);

})();
