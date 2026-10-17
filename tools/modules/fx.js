// ===================== procedural embryo / fetus v2 (SDF + surface nets + AO) =====================
// Proportions follow standard fetal biometry expressed as ratios of crown–rump length (CRL):
// BPD/CRL, femur/CRL, foot/CRL, abdominal diameter/CRL. Embryo weeks follow Carnegie stages.
const FX=(()=>{
const V3=(x,y,z)=>({x,y,z});let AN={};
const sub=(a,b)=>V3(a.x-b.x,a.y-b.y,a.z-b.z),add=(a,b)=>V3(a.x+b.x,a.y+b.y,a.z+b.z),mul=(a,s)=>V3(a.x*s,a.y*s,a.z*s),dot=(a,b)=>a.x*b.x+a.y*b.y+a.z*b.z,len=a=>Math.sqrt(dot(a,a)),nrm=a=>mul(a,1/(len(a)||1));
const cross=(a,b)=>V3(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x),mix=(a,b,t)=>a+(b-a)*t,mixV=(a,b,t)=>V3(mix(a.x,b.x,t),mix(a.y,b.y,t),mix(a.z,b.z,t)),cl=(x,a,b)=>x<a?a:x>b?b:x;
const ss=(a,b,x)=>{const t=cl((x-a)/(b-a),0,1);return t*t*(3-2*t)};
const lerpT=(tab,w)=>{const ks=Object.keys(tab).map(Number).sort((a,b)=>a-b);if(w<=ks[0])return tab[ks[0]];if(w>=ks[ks.length-1])return tab[ks[ks.length-1]];for(let i=0;i<ks.length-1;i++)if(w<=ks[i+1]){const t=(w-ks[i])/(ks[i+1]-ks[i]);return tab[ks[i]]+(tab[ks[i+1]]-tab[ks[i]])*t}};
// ---------- primitives ----------
// t0 ellipsoid (optional orthonormal basis B=[ex,ey,ez]); t1 round cone. s=1 → smooth subtraction.
function ell(c,r,col,k,B){return{t:0,c,r:typeof r==='number'?V3(r,r,r):r,col,k:k??.03,B}}
function cap(a,b,ra,rb,col,k){const ab=sub(b,a);return{t:1,a,b,ra,rb:rb??ra,ab,l2:Math.max(1e-9,dot(ab,ab)),col,k:k??.03}}
function dPrim(P,x,y,z){if(P.t===0){let px=x-P.c.x,py=y-P.c.y,pz=z-P.c.z;if(P.B){const B=P.B,a=px*B[0].x+py*B[0].y+pz*B[0].z,b=px*B[1].x+py*B[1].y+pz*B[1].z,c=px*B[2].x+py*B[2].y+pz*B[2].z;px=a;py=b;pz=c}
  const rx=P.r.x,ry=P.r.y,rz=P.r.z,k0=Math.sqrt((px/rx)**2+(py/ry)**2+(pz/rz)**2),k1=Math.sqrt((px/rx/rx)**2+(py/ry/ry)**2+(pz/rz/rz)**2);return k1<1e-9?-Math.min(rx,ry,rz):k0*(k0-1)/k1}
 const px=x-P.a.x,py=y-P.a.y,pz=z-P.a.z;let h=(px*P.ab.x+py*P.ab.y+pz*P.ab.z)/P.l2;h=h<0?0:h>1?1:h;const dx=px-P.ab.x*h,dy=py-P.ab.y*h,dz=pz-P.ab.z*h;return Math.sqrt(dx*dx+dy*dy+dz*dz)-(P.ra+(P.rb-P.ra)*h)}
function smin(a,b,k){if(k<=0)return Math.min(a,b);const h=Math.max(k-Math.abs(a-b),0)/k;return Math.min(a,b)-h*h*k*.25}
function smax(a,b,k){return -smin(-a,-b,k)}
// ---------- skin tone by week: thin, red and translucent early; pinker and more opaque late ----------
function skin(w){const T={5:[.86,.44,.40],7:[.88,.47,.41],9:[.92,.55,.44],12:[.94,.6,.48],18:[.94,.62,.52],24:[.93,.62,.5],30:[.94,.66,.54],36:[.95,.69,.57],40:[.95,.71,.59]};const ks=Object.keys(T).map(Number);let a=ks[0],b=ks[ks.length-1];for(let i=0;i<ks.length-1;i++)if(w>=ks[i]&&w<=ks[i+1]){a=ks[i];b=ks[i+1];break}if(w>=b)a=b;const t=b===a?0:cl((w-a)/(b-a),0,1);return T[a].map((v,i)=>v+(T[b][i]-v)*t)}
const tint=(c,r,g,b)=>[cl(c[0]*r,0,1),cl(c[1]*g,0,1),cl(c[2]*b,0,1)];
// =====================================================================================
// EMBRYO  (weeks 5–7, Carnegie stages ~10–17): C-shaped body, tail, heart bulge, arches, buds
// =====================================================================================
function embryo(w,S,PT){const sk=skin(w),e=w<5.5?0:w<6.5?1:2;// 0: week 5, 1: week 6, 2: week 7
 const R=[.95,.40,.37][e],th0=[25,-62,-80][e]*Math.PI/180,th1=[118,228,240][e]*Math.PI/180;
 const C=s=>{const t=th0+(th1-th0)*s;return V3(0,R*Math.cos(t),-R*Math.sin(t))};// dorsal side faces outwards, ventral faces the centre
 const out=s=>nrm(C(s)),tan=s=>nrm(sub(C(Math.min(1,s+.01)),C(Math.max(0,s-.01))));
 const rad=s=>{const b=[.115,.13,.14][e];return Math.max(.018,b*(1-ss(.55,1,s)*.86))*(1+.12*Math.sin(s*Math.PI))};
 const n=48;for(let i=0;i<=n;i++){const s=i/n;S.push(ell(C(s),rad(s),sk,.07))}
 // tail tip
 const tl=C(1),tt=add(tl,mul(tan(1),.06));S.push(cap(tl,tt,rad(1),.012,sk,.03));
 // head: forebrain (front, folded down over the heart) and midbrain (crown of the curve)
 const hb=[.17,.21,.26][e],fb=add(C(.03),mul(out(.03),-.04)),mb=add(C(.13),mul(out(.13),.035));
 S.push(ell(fb,V3(hb*.92,hb,hb),sk,.1));S.push(ell(mb,V3(hb*.82,hb*.86,hb*.86),sk,.1));
 if(e===0){for(let i=0;i<14;i++){const s0=i/14,s1=(i+1)/14;[-1,1].forEach(sd=>S.push(cap(add(add(C(s0),mul(out(s0),rad(s0)*.7)),V3(sd*rad(s0)*.55,0,0)),add(add(C(s1),mul(out(s1),rad(s1)*.7)),V3(sd*rad(s1)*.55,0,0)),rad(s0)*.42,rad(s1)*.42,sk,.03)))}}
 if(e===0){// open neural folds at the head end (anterior neuropore) and along the back
  [-1,1].forEach(sd=>{S.push(cap(add(C(.0),V3(sd*.05,0,0)),add(C(.25),V3(sd*.045,0,0)),.04,.035,sk,.04))});
  PT.push({p:cap(add(C(.0),mul(out(.0),.18)),add(C(.6),mul(out(.6),.12)),.02,.012),col:tint(sk,.7,.55,.6),a:.7,f:.03})}
 // hindbrain roof: thin, translucent diamond (4th ventricle)
 if(e>=1)PT.push({p:ell(add(C(.24),mul(out(.24),rad(.24)*.9)),V3(.07,.09,.04)),col:tint(sk,.93,.75,.8),a:.6,f:.03});
 // somites: paired blocks either side of the dorsal midline
 for(let s=.18;s<.95;s+=.034){const p=C(s),o=out(s),r=rad(s),sz=r*(e===0?.32:.46);[-1,1].forEach(sd=>{const q=add(add(p,mul(o,r*(e===0?.62:.86))),V3(sd*r*(e===0?.5:.3),0,0));S.push(ell(q,V3(sz*.85,sz*.62,sz*.62),tint(sk,1.04,1.02,1.02),.012));PT.push({p:ell(q,sz*.3),col:tint(sk,.82,.72,.75),a:.35,f:sz*.6})})}
 // heart prominence (ventral, large) and liver bulge below it
 const hcS=e===0?.3:.34,hpos=add(C(hcS),mul(out(hcS),-(rad(hcS)+[.04,.07,.07][e])));S.push(ell(hpos,V3(.13,.13,.12).x?V3([.11,.13,.13][e],[.11,.14,.13][e],[.1,.12,.12][e]):0,[.86,.36,.38],.08));
 if(e>=1){const lp=add(C(.5),mul(out(.5),-(rad(.5)+.03)));S.push(ell(lp,V3(.12,.11,.1),[.84,.45,.44],.08))}
 // pharyngeal arches below the head
 const na=e===0?2:e===1?4:3;for(let k=0;k<na;k++){const s=.17+k*.035;[-1,1].forEach(sd=>S.push(ell(add(add(C(s),mul(out(s),-rad(s)*.45)),V3(sd*rad(s)*.7,0,0)),V3(.045,.03-.004*k,.055),tint(sk,.98,.95,.95),.025)))}
 // eye: optic vesicle (week 6), pigmented ring (week 7); otic pit; nasal pit
 const eyeP=add(fb,V3(hb*.78,-hb*.18,hb*.25));
 if(e>=1){[-1,1].forEach(sd=>{const p=V3(sd*eyeP.x,eyeP.y,eyeP.z);S.push(ell(p,.05,sk,.03));PT.push({p:ell(add(p,V3(sd*.045,0,0)),e===2?.042:.04),col:e===2?[.2,.11,.12]:tint(sk,.86,.72,.75),a:e===2?1:.6,f:.012})})}
 if(e>=1)[-1,1].forEach(sd=>PT.push({p:ell(add(C(.21),V3(sd*(rad(.21)+.0),.0,0)),.025),col:tint(sk,.8,.62,.66),a:.7,f:.01}));
 if(e===2)[-1,1].forEach(sd=>PT.push({p:ell(add(fb,V3(sd*hb*.35,-hb*.62,hb*.62)),.022),col:tint(sk,.72,.5,.55),a:.8,f:.01}));
 // limb buds: arm bud from week 6, leg bud slightly later; paddles (hand/foot plates) in week 7
 const bud=(s,sd,isArm)=>{const p=C(s),o=out(s),r=rad(s),root=add(add(p,V3(sd*r*.8,0,0)),mul(o,-r*.2));
  if(e===1){S.push(ell(add(root,V3(sd*.035,0,0)),isArm?V3(.05,.07,.055):V3(.042,.06,.05),sk,.05));return}
  const dir=nrm(add(V3(sd*.7,0,0),mul(o,-.55))),tip=add(root,mul(dir,isArm?.11:.09));S.push(cap(root,tip,isArm?.05:.045,isArm?.04:.036,sk,.05));
  const b1=nrm(cross(dir,V3(0,1,0))),b2=nrm(cross(dir,b1));S.push(ell(add(tip,mul(dir,.03)),isArm?V3(.07,.026,.06):V3(.058,.024,.05),sk,.04,[b1,b2,dir]))};
 if(e>=1){[-1,1].forEach(sd=>{bud(.33,sd,true);bud(.66,sd,false)})}
 // translucent embryo (video, month 2): dark neural tube / brain vesicles along the back, red heart chambers and vessels inside
 if(e>=1){for(let s=0;s<.9;s+=.03){const r=rad(s),p=add(C(s),mul(out(s),r*.42));PT.push({p:ell(p,V3(r*.98,r*.26,r*.26)),col:[.32,.07,.1],a:.6,f:r*.35})}
  [[fb,hb*.6],[mb,hb*.55]].forEach(([p,r])=>PT.push({p:ell(add(p,mul(out(.05),hb*.15)),V3(r*1.55,r*.55,r*.7)),col:[.26,.05,.08],a:.7,f:hb*.8}));
  [[-.03,.0],[.04,-.04],[0,.05]].forEach(([dx,dy])=>PT.push({p:ell(add(hpos,V3(dx,dy,.0)),.045),col:[.9,.12,.08],a:.75,f:.12}));
  for(let k=0;k<3;k++){let prev=add(hpos,V3(0,0,0));for(let s=.36+k*.04;s<.85;s+=.05){const q=add(C(s),mul(out(s),-rad(s)*(.25+.15*Math.sin(s*20+k))));PT.push({p:cap(prev,q,.006),col:[.8,.1,.07],a:.6,f:.05});prev=q}}}
 const nav=add(C(.55),mul(out(.55),-(rad(.55)+.02)));
 AN={head:fb,heart:hpos,tail:C(.97),navel:nav,arm:e>=1?add(C(.33),V3(rad(.33),0,0)):null,leg:e>=1?add(C(.66),V3(rad(.66),0,0)):null,eye:e>=1?V3(eyeP.x+.05,eyeP.y,eyeP.z):null};
}
// =====================================================================================
// FETUS (week 8–40). Units: CRL ≈ 1. y up, z ventral (face side), x = baby's left/right.
// =====================================================================================
function fetus(w,S,PT){const sk=skin(w),fat=ss(22,38,w),early=w<10,lip=tint(sk,.97,.8,.82),dk=f=>tint(sk,f,f*.86,f*.9);
 // ---- biometry (ratios to CRL) ----
 const bpd=lerpT({8:.52,9:.5,10:.46,11:.43,12:.40,14:.36,16:.33,20:.30,24:.295,28:.29,32:.28,36:.272,40:.265},w);
 const hw=bpd/2,hl=hw*lerpT({8:1.08,12:1.18,20:1.24,40:1.26},w),hh=hw*lerpT({8:1.0,16:1.06,40:1.08},w);
 const fl=lerpT({8:.075,9:.09,10:.11,11:.13,12:.15,14:.17,16:.185,20:.20,24:.215,28:.22,32:.22,36:.215,40:.21},w);
 const foot=lerpT({8:.08,10:.12,12:.15,16:.18,20:.20,30:.21,40:.215},w)*.95;
 const tw=lerpT({8:.15,10:.15,12:.148,16:.142,20:.145,28:.158,34:.175,40:.185},w);// half trunk width
 const ua=fl*lerpT({8:1.15,12:1.0,20:.95,40:.95},w),fa=fl*.86,hand=foot*.62;
 const th=fl*1.05,sh=fl*.95;
 const rArm=ua*lerpT({8:.34,12:.28,20:.22,28:.24,34:.27,40:.29},w),rLeg=th*lerpT({8:.38,12:.32,20:.27,28:.31,34:.36,40:.39},w);
 // ---- spine / trunk ----
 const y0=-.45,curl=lerpT({8:.6,10:.75,14:.9,24:1,34:1.08,40:1.12},w);
 // spine = circular arc, convex towards the back; its upper end leans forward
 const Lt=lerpT({8:.46,10:.5,12:.56,16:.6,20:.62,40:.64},w),arc=curl*1.6,Rs=Lt/(2*Math.sin(arc/2)),zc=Rs*Math.cos(arc/2)-.03;
 const SP=t=>{const p=(t-.5)*arc;return V3(0,y0+Lt/2+Rs*Math.sin(p),zc-Rs*Math.cos(p))};
 const flex=arc*.32+lerpT({8:.0,12:.05,20:.08,40:.1},w);// head flexion: chin towards the chest
 const ez=nrm(V3(0,-Math.sin(flex),Math.cos(flex))),ey=nrm(V3(0,Math.cos(flex),Math.sin(flex))),ex=V3(1,0,0),HB=[ex,ey,ez];
 const Nk=SP(1),hc=add(add(Nk,mul(ey,hh*.66)),mul(ez,hl*.12));
 const F=(x,y,z)=>add(hc,add(add(mul(ex,x*hw),mul(ey,y*hh)),mul(ez,z*hl)));// head-local → model
 const G=(P,g)=>{P.g=g;S.push(P);return P};
 // buttocks, abdomen (liver makes it round early), chest, shoulders, neck
 const bt=SP(.12),ab=SP(.40),ch=SP(.70),shY=SP(.86);
 G(ell(add(bt,V3(0,0,-.01)),V3(tw*1.0,Lt*.17,tw*.92),sk,.12),0);
 G(ell(add(ab,V3(0,0,tw*(.22+.18*(early?1:0)+.08*fat))),V3(tw*(1.0+.06*fat),Lt*.24,tw*(1.0+.1*(early?1:0)+.08*fat)),sk,.12),0);
 G(ell(add(ch,V3(0,0,tw*.12)),V3(tw*.98,Lt*.22,tw*.9),sk,.12),0);
 G(cap(add(shY,V3(-tw*.78,0,-.005)),add(shY,V3(tw*.78,0,-.005)),tw*.42,tw*.42,sk,.1),0);
 G(cap(add(shY,V3(0,0,.0)),F(0,-.55,-.15),hw*.5,hw*.55,sk,.1),0);
 // back: gentle paravertebral ridges + vertebrae visible through thin skin (≈11–22 weeks)
 if(w>=11&&w<=22){for(let t=.08;t<=.9;t+=.055){const p=SP(t),bk=add(p,V3(0,0,-tw*.86));PT.push({p:ell(bk,V3(.012,.008,.01)),col:dk(.86),a:.55*(1-ss(16,22,w)),f:.012})}}
 // ---- head ----
 const cro=lerpT({8:.02,12:.06,20:.12,30:.16,40:.18},w);G(ell(F(0,cro,-cro*.8),V3(hw,hh*.98,hl*.97),sk,.06,HB),1);
 G(ell(F(0,.18,-.22),V3(hw*.94,hh*.86,hl*.78),sk,.08,HB),1);// occiput
 // ---- face: lower face hangs below/in front of the large cranium and grows relative to it with age ----
 const fm=lerpT({8:.72,10:.8,12:.86,20:.94,40:1.0},w),fsc=lerpT({8:.86,12:.94,20:1.04,30:1.12,40:1.16},w),Fo=F,FF=(x,y,z)=>Fo(x*fsc,-.45+(y+.45)*fsc,z+(fsc-1)*.25*(1-Math.abs(y+.45))),FC=(x,y,z,r,col,k)=>G(ell(FF(x,y,z),V3(hw*r[0]*fsc,hh*r[1]*fsc,hl*r[2]*fsc),col||sk,k??.03,HB),1);
 FC(0,-.47,.5,[.5*fm,.42*fm,.56],sk,hw*.4);// maxilla / mid-face
 FC(0,-.76,.52,[.36*fm,.22*fm,.38],sk,hw*.3);// mandible
 FC(0,-.82,.72,[.17,.12,.15],sk,.04);// chin
 [-1,1].forEach(s=>FC(s*.38,-.46,.6,[.26+.07*fat,.24+.06*fat,.3+.05*fat],sk,hw*.3));// cheeks (buccal fat from ~24 weeks)
 // eyes: wide-set, dark and lidless at 8–9 weeks; lids fused ~10–26 weeks; open from ~27 weeks
 const eX=lerpT({8:.47,10:.42,14:.37,20:.34,40:.33},w),eY=-.13,eZ=.83,open=w>=27,lidless=w<10;
 [-1,1].forEach(s=>{FC(s*eX,eY,eZ,[.15,.1,.09],sk,hw*.12);// puffy lids over the eyeball
  if(lidless)PT.push({p:ell(FF(s*eX,eY,eZ+.08),V3(hw*.11,hh*.085,hl*.12),HB),col:[.16,.09,.1],a:1,f:hw*.03});
  else if(open){PT.push({p:ell(FF(s*eX,eY,eZ+.08),V3(hw*.11,hh*.05,hl*.12),HB),col:[.9,.86,.84],a:.9,f:hw*.012});PT.push({p:ell(FF(s*eX,eY-.005,eZ+.09),V3(hw*.075,hh*.06,hl*.12),HB),col:[.14,.1,.1],a:1,f:hw*.01});PT.push({p:cap(FF(s*(eX-.13),eY+.05,eZ+.06),FF(s*(eX+.12),eY+.06,eZ+.04),hw*.01),col:dk(.6),a:.8,f:hw*.02})}
  else{PT.push({p:cap(FF(s*(eX-.13),eY-.01,eZ+.09),FF(s*(eX+.13),eY+.0,eZ+.06),hw*.01),col:dk(.55),a:.95,f:hw*.022});PT.push({p:ell(FF(s*eX,eY+.04,eZ+.07),V3(hw*.14,hh*.06,hl*.1),HB),col:tint(sk,.97,.86,.9),a:.4,f:hw*.03})}
  if(w>=26)PT.push({p:cap(FF(s*(eX-.12),eY+.2,eZ+.02),FF(s*(eX+.14),eY+.18,eZ-.04),hw*.012),col:dk(.8),a:.45*ss(26,34,w),f:hw*.03})});
 // nose: flat early, button nose later
 const nb=lerpT({8:.45,12:.7,20:.9,40:1},w);
 G(cap(FF(0,-.12,.97),FF(0,-.33,1.02+.05*nb),hw*.05,hw*.075*nb+hw*.02,sk,.03),1);
 FC(0,-.36,1.02+.06*nb,[.1,.085,.08],sk,.025);
 [-1,1].forEach(s=>FC(s*.1,-.39,.98+.05*nb,[.065,.055,.06],sk,.02));
 [-1,1].forEach(s=>PT.push({p:ell(FF(s*.055,-.425,1.02+.05*nb),V3(hw*.028,hh*.02,hl*.04),HB),col:dk(.45),a:.95,f:hw*.012}));
 // lips and mouth
 FC(0,-.55,.98,[.18,.06,.08],lip,.025);FC(0,-.66,.94,[.15,.055,.075],lip,.025);
 S.push({...cap(FF(-.1,-.605,1.0),FF(.1,-.605,1.0),hw*.009),col:sk,k:.01,s:1});
 PT.push({p:cap(FF(-.15,-.605,1.0),FF(.15,-.605,1.0),hw*.008),col:dk(.5),a:.95,f:hw*.022});
 PT.push({p:ell(FF(0,-.6,.97),V3(hw*.2,hh*.13,hl*.1),HB),col:tint(sk,.98,.76,.78),a:.5,f:hw*.03});
 // ears: start low on the neck and rise to eye level by ~20 weeks
 const eyY=lerpT({8:-.62,10:-.55,12:-.45,16:-.25,20:-.12,40:-.08},w),er=hh*lerpT({8:.12,10:.15,14:.2,20:.24,40:.27},w);
 [-1,1].forEach(s=>{const ec=F(s*.94,eyY,-.04),n=V3(s,0,0),u=ey,f=nrm(cross(n,u));
  G(ell(ec,V3(er*.28,er,er*.7),sk,.025,[ex,ey,ez]),1);
  for(let i=0;i<12;i++){const a=-.6+i/11*Math.PI*1.45,p=add(add(ec,mul(u,Math.cos(a)*er*.82)),mul(ez,-Math.sin(a)*er*.55));G(ell(add(p,mul(n,er*.08)),er*.13,sk,.02),1)}
  S.push({...ell(add(add(ec,mul(n,er*.3)),mul(u,-er*.1)),V3(er*.22,er*.38,er*.28),sk,.03),s:1});
  PT.push({p:ell(add(ec,mul(n,er*.2)),V3(er*.2,er*.42,er*.3)),col:dk(.8),a:.6,f:er*.1})});
 // scalp hair from ~28 weeks (colour only)
 if(w>=26)PT.push({p:ell(F(0,.42,-.28),V3(hw*1.02,hh*.78,hl*.95),HB),col:[.5,.34,.28],a:.45*ss(26,38,w),f:hw*.3});
 if(w<13){const tr=1-ss(9,13,w);for(let t=.05;t<.95;t+=.06)PT.push({p:ell(add(SP(t),V3(0,0,tw*-.2)),tw*.28),col:[.3,.07,.1],a:.5*tr,f:tw*.5})}
 // early fetal skin is thin: brain shows as a dark cap, heart/liver as a red glow (fades by ~16 weeks)
 if(w<17){const tr=1-ss(10,17,w);PT.push({p:ell(F(0,.22,-.12),V3(hw*.86,hh*.78,hl*.82),HB),col:[.2,.04,.09],a:.85*tr,f:hw*.6});
  PT.push({p:ell(add(ch,V3(0,0,tw*.3)),V3(tw*.6,Lt*.16,tw*.5)),col:[.8,.18,.16],a:.45*tr,f:tw*.5});PT.push({p:ell(add(ab,V3(0,0,tw*.3)),V3(tw*.7,Lt*.18,tw*.6)),col:[.72,.2,.18],a:.35*tr,f:tw*.5})}
 // ---- arms: flexed, hands at the face (right fist near the mouth, left open by the cheek) ----
 const handDat=[];
 if(!(typeof self!=="undefined"&&self.FXDBG&&self.FXDBG.noarms))[1,-1].forEach(s=>{const g=s>0?2:3,Sh=add(shY,V3(s*tw*.86,0,.0)),udir=nrm(V3(s*.34,-.55,.76)),E=add(Sh,mul(udir,ua));
  const tgt=s>0?F(.62,-1.0,.7):F(-.8,-.62,.62),fd=nrm(sub(tgt,E)),Wr=add(E,mul(fd,Math.min(fa,len(sub(tgt,E))*.98)));
  G(cap(Sh,E,rArm*1.05,rArm*.8,sk,rArm*.9),g);G(cap(E,Wr,rArm*.8,rArm*.62,sk,rArm*.5),g);
  // hand frame: hd along forearm, pn = palm normal (towards face), sideways = finger spread axis
  const toFace=nrm(sub(F(0,-.3,.6),Wr)),pn=nrm(sub(toFace,mul(fd,dot(toFace,fd)))),sw=nrm(cross(fd,pn));
  const hd=nrm(add(fd,mul(pn,.15))),pc=add(Wr,mul(hd,hand*.38)),fist=false;
  G(ell(pc,V3(hand*.34,hand*.13,hand*.4),sk,.025,[sw,pn,hd]),g);// palm
  const fr=hand*lerpT({8:.13,12:.125,20:.12,40:.13},w),fingers=w>=9;
  if(!fingers){// week 8: hand plate with digital rays (notched paddle)
   G(ell(add(pc,mul(hd,hand*.3)),V3(hand*.42,hand*.12,hand*.32),sk,.03,[sw,pn,hd]),g);
   for(let d=0;d<4;d++)PT.push({p:cap(add(pc,mul(sw,(d-1.5)*hand*.18)),add(add(pc,mul(sw,(d-1.5)*hand*.2)),mul(hd,hand*.55)),hand*.04),col:dk(.88),a:.6,f:hand*.05})}
  else for(let d=0;d<4;d++){const off=(d-1.5)*hand*.19,b0=add(add(pc,mul(hd,hand*.36)),mul(sw,off)),L=hand*(.36-.05*Math.abs(d-1.2)),c1=s>0?.6:.35,
    m1=add(b0,mul(nrm(add(hd,mul(pn,c1*.6))),L*.5)),t1=add(m1,mul(nrm(add(mul(hd,1-c1),mul(pn,c1*1.1))),L*.45));
   G(cap(b0,m1,fr,fr*.95,sk,.012),g);G(cap(m1,t1,fr*.95,fr*.85,sk,.01),g);if(w>=20)PT.push({p:ell(t1,fr*.7),col:tint(sk,1.05,1.08,1.08),a:.35,f:fr*.4})}
  if(fingers){const tb=add(pc,add(mul(sw,-s*0+(-1)*hand*.3*(1)),mul(pn,hand*.08))),tt=add(tb,mul(nrm(add(add(hd,mul(pn,fist?.9:.4)),mul(sw,fist?.6:-.2))),hand*.38));G(cap(add(pc,mul(sw,-hand*.22)),tt,fr*1.15,fr*.95,sk,.015),g)}
  handDat.push({pc,Sh})});
 // ---- legs: hips and knees flexed, shins folded back, feet crossed in front of the buttocks ----
 const footDat=[];
 [1,-1].forEach(s=>{const g=s>0?4:5,H=add(SP(.16),V3(s*tw*.62,0,tw*.35)),tdir=nrm(V3(s*.26,lerpT({8:.45,12:.75,20:.92,40:.98},w),lerpT({8:.8,12:.6,20:.45,40:.4},w))),K=add(H,mul(tdir,th));
  const sdir=nrm(V3(-s*.3,-.92,lerpT({8:.3,14:.2,30:.12},w))),A=add(K,mul(sdir,sh));
  G(cap(H,K,rLeg*1.08,rLeg*.8,sk,rLeg*1.2),g);G(cap(K,A,rLeg*.78,rLeg*.56,sk,rLeg*.5),g);
  // calf bulge late
  if(w>=24)G(ell(add(mixV(K,A,.35),V3(0,0,-rLeg*.25)),V3(rLeg*.55,sh*.25,rLeg*.5),sk,.05),g);
  const fdir=nrm(V3(-s*.55,lerpT({8:.1,20:.4},w),.72)),up=nrm(cross(fdir,V3(s,0,0))).y>0?nrm(cross(fdir,V3(s,0,0))):mul(nrm(cross(fdir,V3(s,0,0))),-1),fs=nrm(cross(up,fdir));
  const heel=add(A,mul(up,-rLeg*.25)),toeB=add(heel,mul(fdir,foot*.78));
  G(ell(add(heel,mul(fdir,foot*.08)),V3(foot*.17,foot*.17,foot*.2),sk,.04,[fs,up,fdir]),g);G(cap(add(heel,mul(fdir,foot*.1)),toeB,foot*.17,foot*.19,sk,.05),g);// heel + foot body
  G(ell(add(mixV(heel,toeB,.45),mul(up,foot*.06)),V3(foot*.17,foot*.12,foot*.34),sk,.04,[fs,up,fdir]),g);
  if(w>=9)for(let t=0;t<5;t++){const big=t===0,o=s*(t*.085-.17)*foot*(1.0),tp=add(add(toeB,mul(fdir,foot*(big?.12:.1-.012*t))),mul(fs,-o));G(ell(tp,foot*(big?.085:.06-.004*t),sk,.012),g)}
  else G(ell(add(toeB,mul(fdir,foot*.06)),V3(foot*.24,foot*.08,foot*.12),sk,.03,[fs,up,fdir]),g);
  footDat.push({toe:toeB,H})});
 // ---- umbilicus: physiological midgut herniation into the cord base until ~11 weeks ----
 const nv=add(ab,V3(0,-Lt*.02,tw*(1.18+.18*(early?1:0)+.1*fat)));
 if(w<12)G(ell(add(nv,V3(0,0,tw*.15)),tw*lerpT({8:.42,10:.38,11:.28,12:.1},w),tint(sk,1.0,.9,.92),.04),0);
 G(ell(nv,tw*.12,tint(sk,.97,.85,.87),.03),0);
 // small tail remnant at week 8
 if(w<9)G(cap(add(SP(.0),V3(0,0,-tw*.5)),add(SP(-.05),V3(0,-.03,.02)),tw*.22,tw*.08,sk,.05),0);
 // vernix caseosa in creases, ~24–37 weeks
 if(w>=24&&w<=38){const a=.5*ss(24,30,w)*(1-ss(36,38,w));[F(0,-.6,-.6),add(SP(.6),V3(0,0,-tw*.9)),add(SP(.2),V3(tw*.9,0,0)),add(SP(.2),V3(-tw*.9,0,0)),F(.9,-.4,-.2),F(-.9,-.4,-.2)].forEach(p=>PT.push({p:ell(p,tw*.35),col:[.97,.95,.88],a,f:tw*.25,noise:1}))}
 AN={head:hc,heart:add(ch,V3(0,0,tw*.7)),navel:nv,eye:F(eX,eY,eZ+.05),hand:handDat[1]?handDat[1].pc:hc,foot:footDat[0].toe,spine:SP(.6),mouth:F(0,-.48,1.0),ear:F(.99,eyY,-.04),
  piv:{1:SP(.95),2:handDat[0]?handDat[0].Sh:hc,3:handDat[1]?handDat[1].Sh:hc,4:footDat[0].H,5:footDat[1].H}};
}
function model(w){const S=[],PT=[];if(w<8)embryo(Math.max(5,w),S,PT);else fetus(w,S,PT);return{S,PT}}
// ---------- evaluation + surface nets ----------
function build(w,res){const{S:SA,PT}=model(w),S=SA.filter(p=>!p.s),SB=SA.filter(p=>p.s);let mn=V3(1e9,1e9,1e9),mx=V3(-1e9,-1e9,-1e9);
 S.forEach(P=>{const pts=P.t===0?[[P.c,Math.max(P.r.x,P.r.y,P.r.z)]]:[[P.a,P.ra],[P.b,P.rb]];pts.forEach(([c,r])=>{mn=V3(Math.min(mn.x,c.x-r),Math.min(mn.y,c.y-r),Math.min(mn.z,c.z-r));mx=V3(Math.max(mx.x,c.x+r),Math.max(mx.y,c.y+r),Math.max(mx.z,c.z+r))})});
 const pad=.06;mn=sub(mn,V3(pad,pad,pad));mx=add(mx,V3(pad,pad,pad));const ext=sub(mx,mn),step=Math.max(ext.x,ext.y,ext.z)/res,nx=Math.ceil(ext.x/step)+1,ny=Math.ceil(ext.y/step)+1,nz=Math.ceil(ext.z/step)+1;
 const bnd=P=>{if(P.t===0){P.bc=P.c;P.br=Math.max(P.r.x,P.r.y,P.r.z)}else{P.bc=mul(add(P.a,P.b),.5);P.br=Math.sqrt(P.l2)*.5+Math.max(P.ra,P.rb)}};S.forEach(bnd);SB.forEach(bnd);PT.forEach(o=>bnd(o.p));
 const sdU=(x,y,z)=>{let d=1e9;for(let i=0;i<S.length;i++){const P=S[i],lb=Math.hypot(x-P.bc.x,y-P.bc.y,z-P.bc.z)-P.br;if(lb>d+(P.k||0))continue;const q=dPrim(P,x,y,z);d=P.k?smin(d,q,P.k):Math.min(d,q)}return d};
 const sd=(x,y,z)=>{let d=sdU(x,y,z);for(let i=0;i<SB.length;i++){const P=SB[i],lb=Math.hypot(x-P.bc.x,y-P.bc.y,z-P.bc.z)-P.br;if(lb>(P.k||0))continue;d=smax(d,-dPrim(P,x,y,z),P.k)}return d};
 const val=new Float32Array(nx*ny*nz),CS=4,cnx=Math.ceil((nx-1)/CS)+1,cny=Math.ceil((ny-1)/CS)+1,cnz=Math.ceil((nz-1)/CS)+1,cv0=new Float32Array(cnx*cny*cnz),cst=step*CS;
 for(let k=0;k<cnz;k++)for(let j=0;j<cny;j++)for(let i=0;i<cnx;i++)cv0[i+cnx*(j+cny*k)]=sd(mn.x+i*cst,mn.y+j*cst,mn.z+k*cst);
 const lim=cst*1.25;for(let k=0;k<nz;k++){const ck=Math.min(cnz-2,Math.floor(k/CS)),fk=k/CS-ck;for(let j=0;j<ny;j++){const cj=Math.min(cny-2,Math.floor(j/CS)),fj=j/CS-cj;for(let i=0;i<nx;i++){const ci=Math.min(cnx-2,Math.floor(i/CS)),fi=i/CS-ci,b=ci+cnx*(cj+cny*ck),Cv=(di,dj,dk2)=>cv0[b+di+cnx*(dj+cny*dk2)];
  const de=((Cv(0,0,0)*(1-fi)+Cv(1,0,0)*fi)*(1-fj)+(Cv(0,1,0)*(1-fi)+Cv(1,1,0)*fi)*fj)*(1-fk)+((Cv(0,0,1)*(1-fi)+Cv(1,0,1)*fi)*(1-fj)+(Cv(0,1,1)*(1-fi)+Cv(1,1,1)*fi)*fj)*fk;
  val[i+nx*(j+ny*k)]=Math.abs(de)>lim?de:sd(mn.x+i*step,mn.y+j*step,mn.z+k*step)}}}
 const cv=new Int32Array(nx*ny*nz).fill(-1),pos=[],ix=[];
 const E=[[0,1],[2,3],[4,5],[6,7],[0,2],[1,3],[4,6],[5,7],[0,4],[1,5],[2,6],[3,7]],c=new Float32Array(8);
 for(let k=0;k<nz-1;k++)for(let j=0;j<ny-1;j++)for(let i=0;i<nx-1;i++){let m=0;for(let b=0;b<8;b++){c[b]=val[(i+(b&1))+nx*((j+(b>>1&1))+ny*(k+(b>>2&1)))];if(c[b]<0)m|=1<<b}if(m===0||m===255)continue;
  let sx=0,sy=0,sz=0,n=0;for(const[a,b]of E){if((c[a]<0)!==(c[b]<0)){const t=c[a]/(c[a]-c[b]);sx+=(a&1)+((b&1)-(a&1))*t;sy+=(a>>1&1)+((b>>1&1)-(a>>1&1))*t;sz+=(a>>2&1)+((b>>2&1)-(a>>2&1))*t;n++}}
  cv[i+nx*(j+ny*k)]=pos.length/3;pos.push(mn.x+(i+sx/n)*step,mn.y+(j+sy/n)*step,mn.z+(k+sz/n)*step)}
 const C=(i,j,k)=>cv[i+nx*(j+ny*k)];
 for(let k=0;k<nz;k++)for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const v0=val[i+nx*(j+ny*k)];
  for(let a=0;a<3;a++){const di=a===0,dj=a===1,dk=a===2,i1=i+di,j1=j+dj,k1=k+dk;if(i1>=nx||j1>=ny||k1>=nz)continue;const v1=val[i1+nx*(j1+ny*k1)];if((v0<0)===(v1<0))continue;
   let q;if(a===0){if(j<1||k<1||j>ny-2||k>nz-2)continue;q=[C(i,j-1,k-1),C(i,j,k-1),C(i,j,k),C(i,j-1,k)]}else if(a===1){if(i<1||k<1||i>nx-2||k>nz-2)continue;q=[C(i-1,j,k-1),C(i-1,j,k),C(i,j,k),C(i,j,k-1)]}else{if(i<1||j<1||i>nx-2||j>ny-2)continue;q=[C(i-1,j-1,k),C(i,j-1,k),C(i,j,k),C(i-1,j,k)]}
   if(q.some(x=>x<0))continue;if(v0<0)ix.push(q[0],q[1],q[2],q[0],q[2],q[3]);else ix.push(q[0],q[2],q[1],q[0],q[3],q[2])}}
 // project vertices onto the true surface (one Newton step) for crisper detail
 const nv=pos.length/3,nor=new Float32Array(nv*3),col=new Float32Array(nv*3),grp=new Uint8Array(nv),gw=new Float32Array(nv),h=step*.5;
 for(let v=0;v<nv;v++){let x=pos[v*3],y=pos[v*3+1],z=pos[v*3+2];const d=sd(x,y,z);let gx=sd(x+h,y,z)-sd(x-h,y,z),gy=sd(x,y+h,z)-sd(x,y-h,z),gz=sd(x,y,z+h)-sd(x,y,z-h);let l=Math.hypot(gx,gy,gz)||1;gx/=l;gy/=l;gz/=l;
  const mv=cl(d,-step*.5,step*.5);x-=gx*mv;y-=gy*mv;z-=gz*mv;pos[v*3]=x;pos[v*3+1]=y;pos[v*3+2]=z;nor[v*3]=gx;nor[v*3+1]=gy;nor[v*3+2]=gz;
  // colour: blend of nearby primitive colours
  let sum=0,cr=0,cg=0,cb=0;const gd=[9,9,9,9,9,9];for(const P of S){const lb=Math.hypot(x-P.bc.x,y-P.bc.y,z-P.bc.z)-P.br;const g=P.g||0;if(lb>.12&&lb>gd[g])continue;const dd=dPrim(P,x,y,z);if(dd<gd[g])gd[g]=dd;const wgt=1/Math.pow(Math.max(dd,1e-3)+.015,4);sum+=wgt;cr+=P.col[0]*wgt;cg+=P.col[1]*wgt;cb+=P.col[2]*wgt}
  let R=cr/sum,Gc=cg/sum,B=cb/sum;
  // thin early skin: fine red vessels
  if(w<24){const vn=Math.abs(Math.sin(x*41+Math.sin(y*29)*2.2)*Math.sin(z*37+Math.sin(x*23)*2.4));const kk=Math.max(0,(vn-.95)/.05)*(1-ss(12,24,w))*.22;R*=1-kk*.15;Gc*=1-kk*.5;B*=1-kk*.4}
  // subtle mottling
  const mo=Math.sin(x*61+y*13)*Math.sin(y*57-z*21)*Math.sin(z*49+x*17)*.035;R+=mo;Gc+=mo*.8;B+=mo*.8;
  for(const o of PT){const P=o.p,lb=Math.hypot(x-P.bc.x,y-P.bc.y,z-P.bc.z)-P.br;const of=Math.max(o.f,step*1.1);if(lb>of)continue;const dd=dPrim(P,x,y,z);let a=o.a*(1-ss(0,of,dd));if(o.noise)a*=ss(.2,.8,.5+.5*Math.sin(x*90+Math.sin(y*70)*3)*Math.sin(z*80+y*40));if(a<=0)continue;R+=(o.col[0]-R)*a;Gc+=(o.col[1]-Gc)*a;B+=(o.col[2]-B)*a}
  // ambient occlusion from the distance field
  let occ=0,wt=1;for(let s2=1;s2<=5;s2++){const hh=step*1.6*s2;occ+=(hh-Math.max(-hh,sd(x+gx*hh,y+gy*hh,z+gz*hh)))*wt;wt*=.62}
  const ao=cl(1-occ/(step*1.6*2.6),.45,1),aoc=.62+.38*ao;
  col[v*3]=cl(R*(.7+.3*ao)*aoc+(1-ao)*.04,0,1);col[v*3+1]=cl(Gc*aoc*ao**.15,0,1);col[v*3+2]=cl(B*aoc*ao**.1,0,1);
  let bg=0,bd=gd[0];for(let g=1;g<6;g++)if(gd[g]<bd){bd=gd[g];bg=g}grp[v]=bg;gw[v]=bg?Math.min(1,Math.max(0,(gd[0]-bd)/.05+.5)):0}
 return{pos:new Float32Array(pos),idx:new Uint32Array(ix),nor,col,grp,gw,min:mn,max:mx,anch:Object.assign({},AN)}}
return{build,lerpT,skin,model}})();
