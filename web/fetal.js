/* Urban Health · baby in the womb, week by week.
   One scene for both the pregnancy page (baby.html) and the home screen:
   - the week's baby model, bent at its joints by small CPU skinning (weights come from /a/pbr-wNN.*.json),
   - only the movements a baby makes at that week,
   - the placenta set into a cut-away womb wall (the cut always faces the camera), and the cord to the belly.
   UHFetal.create(THREE, gltf, rig, {renderer}) -> {group, radius, update(dt,camera), play(i), list, now, onmove, setStill} */
(function(){
'use strict';
const ease=t=>t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;
const env=(t,a,h,b)=>t<a?ease(t/a):t<a+h?1:t<a+h+b?1-ease((t-a-h)/b):0;
const kf=(t,K)=>{if(t<=K[0][0])return Object.assign({},K[0][1]);for(let i=1;i<K.length;i++)if(t<=K[i][0]){const A=K[i-1],B=K[i],u=ease((t-A[0])/(B[0]-A[0])),o={};for(const k of new Set([...Object.keys(A[1]),...Object.keys(B[1])]))o[k]=(A[1][k]||0)*(1-u)+(B[1][k]||0)*u;return o}return Object.assign({},K[K.length-1][1])};
const add=(a,b)=>{for(const k in b)a[k]=(a[k]||0)+b[k];return a};
const scale=(P,k)=>{const o={};for(const x in P)o[x]=(x==='roll'||x==='drift')?P[x]:P[x]*k;return o};

/* What a baby does, and from which week. a = how big the movement is (less room near the end). */
const MOVES=[
 {k:'twitch',n:'Tiny twitches',from:6,to:8,d:4.2,tx:()=>'Tiny twitches and startles. Far too small to feel, but they can be seen on a scan.',
  f:t=>{let j=0;for(const s of[.5,1.9,3.1]){const u=t-s;if(u>0&&u<.45)j=Math.max(j,u<.06?u/.06:Math.exp(-(u-.06)*10))}return{jolt:.8*j,sway:6*j}}},
 {k:'startle',n:'Startle',from:9,to:14,d:3.4,tx:()=>'A startle: arms and legs jerk out together, then settle. One of the first movements a baby makes.',
  f:t=>{const e=kf(t,[[0,{}],[.35,{elL:-34,elR:-34,shL:-12,shR:-12,spL:10,spR:10,kneeL:-18,kneeR:-18,nod:-6,jolt:.6}],[.6,{elL:-30,elR:-30,shL:-10,shR:-10,kneeL:-15,kneeR:-15}],[2.2,{}]]);return e}},
 {k:'limbs',n:'Arms and legs',from:9,to:16,d:4.6,tx:w=>w<12?'Moving arms and legs. From about 9 weeks they can move one at a time.':'Moving arms and legs one at a time, bending and straightening.',
  f:t=>{const e=env(t,.4,3.8,.4),s=Math.sin(t*2.6),c=Math.sin(t*2.6+1.6);return{elL:-16*s*e,elR:16*c*e,kneeL:-14*c*e,kneeR:-14*s*e,hipL:-6*c*e,hipR:-6*s*e}}},
 {k:'stretch',n:'Stretch',from:10,to:40,d:4.2,tx:()=>'Stretching out arms and legs, then curling back up. Babies stretch many times a day.',
  f:t=>{const e=env(t,1.3,.7,1.8);return{kneeL:-22*e,kneeR:-22*e,hipL:-14*e,hipR:-14*e,elL:-38*e,elR:-38*e,shL:-14*e,shR:-14*e,spL:10*e,spR:10*e,nod:-12*e,chest:.6*e}}},
 {k:'hic',n:'Hiccups',from:10,to:40,d:6.2,tx:w=>w<23?'Hiccups: quick, rhythmic little jolts. They are normal, and still too small to feel.':'Hiccups: quick, rhythmic little jolts. They are normal and can last a few minutes. You may feel them as gentle tapping.',
  f:t=>{let j=0;for(let i=0;i<5;i++){const u=t-.4-i*1.15;if(u>0&&u<.5)j=Math.max(j,u<.07?u/.07:Math.exp(-(u-.07)*9))}return{jolt:j,nod:3*j,chest:-.5*j,elL:-4*j,elR:-4*j,kneeL:-5*j,kneeR:-5*j}}},
 {k:'face',n:'Hand to face',from:11,to:14,d:5,tx:()=>'Bringing a hand up to the face. Babies touch their face and head a lot.',
  f:(t,_,IK)=>kf(t,[[0,{}],[.9,{elR:-40,shR:16,spR:8}],[2.2,{shR:IK.sh*.8,spR:IK.sp*.8,elR:IK.el*.8+4,nod:2}],[3.8,{shR:IK.sh*.8,spR:IK.sp*.8,elR:IK.el*.8+4,nod:2}],[5,{}]])},
 {k:'thumb',n:'Thumb to mouth',from:15,to:40,d:6.8,cam:-.5,tx:()=>'Bringing the thumb to the mouth and sucking. Practice for feeding after birth.',
  f:(t,_,IK)=>{const away={elR:-55,shR:22,spR:10,elL:-24,shL:10},ik={shR:IK.sh,spR:IK.sp,elR:IK.el,elL:-26,shL:10,nod:3,turn:-5};
   const P=kf(t,[[0,{}],[1.0,away],[2.5,ik],[5.4,ik],[6.8,{}]]);const s=t>2.6&&t<5.3?Math.min(1,(t-2.6)/.3,(5.3-t)/.3):0,w=Math.sin((t-2.6)*Math.PI*2*1.5);
   return add(P,{elR:1.4*w*s,nod:1.1*w*s,chest:.15*w*s})}},
 {k:'kick',n:'Kick',from:16,to:40,d:3.6,cam:.25,tx:w=>w<18?'A kick. Most mothers first feel movement between 18 and 22 weeks, sooner in a later pregnancy.':w<28?'A kick. Many mothers feel kicks by now, often more when resting or after a meal.':w<34?'A strong kick. Kicks get stronger now, and you get to know your baby’s pattern.':'A jab. There is less room now, so kicks become pushes and jabs.',
  f:t=>{const k=u=>u<0?0:u<.16?ease(u/.16):u<1?1-ease((u-.16)/.84):0;const a=k(t-.3),b=k(t-1.6)*.75;return{kneeL:-34*a,hipL:-12*a,kneeR:-30*b,hipR:-10*b,jolt:.25*(a+b)}}},
 {k:'turn',n:'Turn around',from:10,to:33,d:7.6,tx:w=>w<20?'Turning right around. There is lots of room, so babies tumble and turn freely.':'Pushing off and turning right around. There is still room to roll and somersault, so babies change position many times a day.',
  f:t=>kf(t,[[0,{}],[.5,{kneeL:-26,kneeR:-26,hipL:-10,hipR:-10}],[1.1,{drift:.03,hipL:6,hipR:6,nod:6}],[3.9,{drift:.03,hipL:6,hipR:6,nod:6,roll:180}],[4.9,{drift:.03,hipL:6,hipR:6,nod:6,roll:180,turn:10}],[7.0,{drift:.01,roll:0}],[7.6,{}]])},
 {k:'look',n:'Look around',from:12,to:40,d:4.6,tx:()=>'Turning the head from side to side. Babies move their heads and faces a lot.',
  f:t=>{const e=env(t,.2,4.2,.2);return{turn:22*Math.sin(t/4.6*Math.PI*2)*e,tilt:5*Math.sin(t/4.6*Math.PI*2+1)*e,nod:-6*e,elL:-22*e,elR:-22*e,shL:8*e,shR:8*e}}},
 {k:'breathe',n:'Practise breathing',from:20,to:40,d:6,tx:()=>'Practising breathing. The chest rises and falls with fluid, not air, building strength for the first breath.',
  f:t=>{const e=env(t,.4,5.2,.4),c=.5-.5*Math.cos(t/2*Math.PI*2);return{chest:.9*e*c,nod:-1.5*e*c}}},
 {k:'wriggle',n:'Wriggle',from:34,to:40,d:4.4,tx:()=>'Less room now: smaller wriggles and shifts instead of big turns. Many babies settle head-down from now.',
  f:t=>{const e=env(t,.5,3.4,.5),s=Math.sin(t*2.1);return{roll:9*s*e,hipL:-8*e*Math.max(0,s),hipR:-8*e*Math.max(0,-s),kneeL:-10*e*Math.max(0,s),kneeR:-10*e*Math.max(0,-s),nod:4*e}}}];
const amp=(m,w)=>w>=34&&/^(stretch|kick|look)$/.test(m.k)?.6:w<=12&&m.k==='turn'?1:1;
function movesFor(w){return MOVES.filter(m=>w>=m.from&&w<=m.to)}

const b64=(x,T)=>{const b=atob(x),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new T(u.buffer)};

function create(THREE,gltf,rig,opt){
 opt=opt||{};const w=rig&&rig.w||20,still=!!opt.still;
 const V3=a=>new THREE.Vector3().fromArray(a),lin=h=>new THREE.Color(h).convertSRGBToLinear();
 const group=new THREE.Group(),world=new THREE.Group(),body=new THREE.Group();body.matrixAutoUpdate=false;world.add(body);group.add(world);
 /* the baby: positions baked in model space (as the rig data was made), so the Float animation never moves it */
 let src=null;gltf.scene.traverse(o=>{if(o.isMesh&&!src)src=o});
 const chain=[];for(let q=src;q&&q!==gltf.scene;q=q.parent)chain.unshift(q);
 const M0=new THREE.Matrix4();chain.forEach(q=>{if(q.name==='Baby')return;q.updateMatrix();M0.multiply(q.matrix)});
 const sg=src.geometry,n=sg.attributes.position.count,v=new THREE.Vector3(),nm=new THREE.Matrix3().getNormalMatrix(M0);
 const BASE=new Float32Array(n*3),BASEN=new Float32Array(n*3);
 for(let i=0;i<n;i++){v.fromBufferAttribute(sg.attributes.position,i).applyMatrix4(M0);v.toArray(BASE,i*3);v.fromBufferAttribute(sg.attributes.normal,i).applyMatrix3(nm).normalize();v.toArray(BASEN,i*3)}
 const G=new THREE.BufferGeometry();G.setAttribute('position',new THREE.BufferAttribute(BASE.slice(),3));G.setAttribute('normal',new THREE.BufferAttribute(BASEN.slice(),3));
 if(sg.attributes.uv)G.setAttribute('uv',sg.attributes.uv);G.setIndex(sg.index);
 const baby=new THREE.Mesh(G,src.material);baby.frustumCulled=false;baby.userData=Object.assign({},(src.parent&&src.parent.userData)||{});baby.name='Baby';body.add(baby);
 G.computeBoundingBox();const CEN=G.boundingBox.getCenter(new THREE.Vector3()),SIZE=G.boundingBox.getSize(new THREE.Vector3());
 world.position.copy(CEN).negate();
 const radius=SIZE.length()*.5;
 /* skinning */
 const ok=!!(rig&&rig.wb&&rig.n===n);let RG=null,VB,VW,AX={},PA;
 if(ok){RG={names:rig.names,bones:rig.bones,w:{}};for(const k of rig.names)RG.w[k]=b64(rig.wb[k],Uint8Array);
  for(const s of['L','R']){const B=rig.bones,sh=V3(B['upper'+s].pivot),el=V3(B['fore'+s].pivot),hp=V3(B['thigh'+s].pivot),kn=V3(B['shin'+s].pivot),ht=V3(rig.tips.hand[s]),ft=V3(rig.tips.foot[s]);
   AX['arm'+s]=new THREE.Vector3().crossVectors(el.clone().sub(sh),ht.clone().sub(el)).normalize();AX['leg'+s]=new THREE.Vector3().crossVectors(kn.clone().sub(hp),ft.clone().sub(kn)).normalize()}
  PA=rig.names.filter(k=>k!=='chest');VB=new Uint8Array(n*3);VW=new Float32Array(n*3);
  for(let i=0;i<n;i++){let a=[];for(let j=0;j<PA.length;j++){const x=RG.w[PA[j]][i];if(x)a.push([x,j])}a.sort((p,q)=>q[0]-p[0]);a=a.slice(0,3);const s=a.reduce((p,q)=>p+q[0],0)||1;a.forEach((x,j)=>{VB[i*3+j]=x[1];VW[i*3+j]=x[0]/s})}}
 const IK=(rig&&rig.ik)||{sh:0,sp:0,el:0};
 const X=new THREE.Vector3(1,0,0),Y=new THREE.Vector3(0,1,0),Z=new THREE.Vector3(0,0,1);
 const rotAbout=(p,axis,deg,out)=>{const m=new THREE.Matrix4().makeTranslation(p.x,p.y,p.z).multiply(new THREE.Matrix4().makeRotationAxis(axis,deg*Math.PI/180)).multiply(new THREE.Matrix4().makeTranslation(-p.x,-p.y,-p.z));return out?out.multiply(m):m};
 let lastKey='';
 function skin(P){const g=k=>P[k]||0;
  if(!ok)return;const B=RG.bones,mats={torso:new THREE.Matrix4()};
  const hp=V3(B.head.pivot);const h=rotAbout(hp,Y,g('turn'));rotAbout(hp,X,g('nod'),h);rotAbout(hp,Z,g('tilt'),h);mats.head=h;
  for(const s of['L','R']){const sg=s==='L'?1:-1,sp=V3(B['upper'+s].pivot),u=rotAbout(sp,Y,sg*g('sp'+s));rotAbout(sp,AX['arm'+s],g('sh'+s),u);mats['upper'+s]=u;
   mats['fore'+s]=rotAbout(V3(B['fore'+s].pivot),AX['arm'+s],g('el'+s),u.clone());
   const hq=V3(B['thigh'+s].pivot),th=rotAbout(hq,AX['leg'+s],-g('hip'+s));mats['thigh'+s]=th;mats['shin'+s]=rotAbout(V3(B['shin'+s].pivot),AX['leg'+s],-g('knee'+s),th.clone())}
  const E=PA.map(k=>mats[k].elements),pos=G.attributes.position.array,nor=G.attributes.normal.array,cw=RG.w.chest,cc=V3(B.chest.pivot),ck=.05*g('chest');
  for(let i=0;i<n;i++){const o=i*3,x=BASE[o],y=BASE[o+1],z=BASE[o+2],nx=BASEN[o],ny=BASEN[o+1],nz=BASEN[o+2];let X1=0,Y1=0,Z1=0,NX=0,NY=0,NZ=0;
   for(let j=0;j<3;j++){const ww=VW[o+j];if(!ww)continue;const e=E[VB[o+j]];
    X1+=ww*(e[0]*x+e[4]*y+e[8]*z+e[12]);Y1+=ww*(e[1]*x+e[5]*y+e[9]*z+e[13]);Z1+=ww*(e[2]*x+e[6]*y+e[10]*z+e[14]);NX+=ww*(e[0]*nx+e[4]*ny+e[8]*nz);NY+=ww*(e[1]*nx+e[5]*ny+e[9]*nz);NZ+=ww*(e[2]*nx+e[6]*ny+e[10]*nz)}
   const c=cw[i];if(c&&ck){const k=ck*c/255;X1+=(x-cc.x)*k;Y1+=(y-cc.y)*k*.5;Z1+=(z-cc.z)*k}
   pos[o]=X1;pos[o+1]=Y1;pos[o+2]=Z1;const l=Math.hypot(NX,NY,NZ)||1;nor[o]=NX/l;nor[o+1]=NY/l;nor[o+2]=NZ/l}
  G.attributes.position.needsUpdate=true;G.attributes.normal.needsUpdate=true}
 /* womb, placenta, cord */
 let CUT=null,WC=null;const clip=[];
 if(rig&&rig.womb&&!opt.bare){const W=rig.womb;if(opt.renderer)opt.renderer.localClippingEnabled=true;CUT=new THREE.Plane();clip.push(CUT);WC=V3(W.c);
  const ig=new THREE.SphereGeometry(1,112,84);ig.scale(W.r[0],W.r[1],W.r[2]);ig.translate(W.c[0],W.c[1],W.c[2]);
  const cA=lin(0xEFB9C2),cB=lin(0x8E3442),col=new Float32Array(ig.attributes.position.count*3),pv=new THREE.Vector3(),pc=W.pc?V3(W.pc):null;
  for(let i=0;i<ig.attributes.position.count;i++){let k=0;if(pc){pv.fromBufferAttribute(ig.attributes.position,i);const t=Math.max(0,Math.min(1,1-(pv.distanceTo(pc)-W.pr*.95)/(W.pr*.3)));k=t*t*(3-2*t)}col[i*3]=cA.r+(cB.r-cA.r)*k;col[i*3+1]=cA.g+(cB.g-cA.g)*k;col[i*3+2]=cA.b+(cB.b-cA.b)*k}
  ig.setAttribute('color',new THREE.BufferAttribute(col,3));
  const inner=new THREE.Mesh(ig,new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.48,clearcoat:.45,clearcoatRoughness:.35,side:THREE.BackSide,clippingPlanes:clip}));inner.frustumCulled=false;inner.userData.nopick=1;world.add(inner);
  const og=new THREE.SphereGeometry(1,112,84);og.scale(W.r[0]*1.11,W.r[1]*1.11,W.r[2]*1.11);og.translate(W.c[0],W.c[1],W.c[2]);
  const outer=new THREE.Mesh(og,new THREE.MeshPhysicalMaterial({color:lin(0xD98D99),roughness:.6,clearcoat:.25,side:THREE.DoubleSide,clippingPlanes:clip}));outer.frustumCulled=false;outer.userData.nopick=1;world.add(outer)}
 if(rig&&rig.placenta&&!opt.bare){const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(b64(rig.placenta.p,Float32Array),3));pg.setIndex(new THREE.BufferAttribute(b64(rig.placenta.i,Uint16Array),1));pg.computeVertexNormals();
  const pm=new THREE.Mesh(pg,new THREE.MeshPhysicalMaterial({color:lin(0x7A2633),roughness:.36,clearcoat:.65,clearcoatRoughness:.3,side:THREE.DoubleSide,clippingPlanes:clip}));pm.frustumCulled=false;pm.name='Placenta';
  pm.userData={display_name:'Placenta',description:'The placenta grows on the wall of the womb. Through it, and the cord, the baby gets oxygen and food and gets rid of waste.'};world.add(pm)}
 let cord=null;const C0=!opt.bare&&rig&&rig.cord;
 const cordMat=new THREE.MeshPhysicalMaterial({color:lin(0xC9C3D3),roughness:.36,clearcoat:.6,clearcoatRoughness:.3});
 if(C0){/* soft spiral stripes, like the vessels twisting inside the cord */
  try{const cv=document.createElement('canvas');cv.width=64;cv.height=64;const x=cv.getContext('2d');x.fillStyle='#d4cede';x.fillRect(0,0,64,64);x.strokeStyle='rgba(150,120,160,.45)';x.lineWidth=7;
   for(let i=-64;i<128;i+=22){x.beginPath();x.moveTo(i,0);x.lineTo(i+64,64);x.stroke()}const tx=new THREE.CanvasTexture(cv);tx.wrapS=tx.wrapT=THREE.RepeatWrapping;tx.repeat.set(10,1);tx.encoding=THREE.sRGBEncoding;cordMat.map=tx;cordMat.color=new THREE.Color(0xffffff)}catch(_){}
  cord=new THREE.Mesh(new THREE.BufferGeometry(),cordMat);cord.frustumCulled=false;cord.name='Umbilical_Cord';cord.userData={display_name:'Umbilical cord',description:'Two arteries and one vein, twisted in a spiral, carry blood between the baby and the placenta.'};world.add(cord)}
 const tmp=new THREE.Vector3();
 function cordUpdate(M){if(!cord)return;const nv=V3(C0.navel).applyMatrix4(M),c1=V3(C0.c1).applyMatrix4(M),c2=V3(C0.c2),en=V3(C0.ins);
  const cu=new THREE.CubicBezierCurve3(nv,c1,c2,en);cord.geometry.dispose();cord.geometry=new THREE.TubeGeometry(cu,90,C0.r,10,false)}
 /* body pose (roll, drift, jolt) */
 const Mb=new THREE.Matrix4();
 function place(P){const g=k=>P[k]||0,th=g('roll')*Math.PI/180,sw=g('sway')*Math.PI/180,dz=g('drift')*SIZE.y/.23,dy=.0035*g('jolt')*SIZE.y/.23;
  Mb.makeTranslation(CEN.x,CEN.y+dy,CEN.z+dz).multiply(new THREE.Matrix4().makeRotationY(th)).multiply(new THREE.Matrix4().makeRotationZ(sw)).multiply(new THREE.Matrix4().makeTranslation(-CEN.x,-CEN.y,-CEN.z));
  body.matrix.copy(Mb);body.matrixWorldNeedsUpdate=true;cordUpdate(Mb)}
 /* timeline */
 const list=movesFor(w);let ci=-1,ct=0,gap=0,auto=true,isStill=still,cbs=[];
 function play(i,tap){if(!list.length)return;ci=((i%list.length)+list.length)%list.length;ct=0;gap=0;if(tap)auto=!isStill;cbs.forEach(f=>{try{f(api.now())}catch(_){}})}
 function pose(P){const key=JSON.stringify(P);if(key===lastKey)return;lastKey=key;skin(P);place(P)}
 pose({});
 const api={group,radius,size:SIZE.clone(),list,baby,
  dispose(){group.traverse(o=>{if(o.isMesh&&o!==baby){o.geometry.dispose();if(o.material.map&&o.material.map.isCanvasTexture)o.material.map.dispose();o.material.dispose()}});G.dispose()},
  now(){return ci>=0&&list[ci]?{i:ci,k:list[ci].k,n:list[ci].n,tx:list[ci].tx(w),cam:list[ci].cam||0,p:Math.min(1,ct/list[ci].d)}:null},
  onmove(f){cbs.push(f)},play(i){play(i,true)},
  setStill(s){isStill=!!s;if(isStill){auto=false;pose({})}},
  update(dt,camera){
   if(CUT&&camera){group.updateMatrixWorld(true);const c=world.localToWorld(WC.clone()),nn=c.clone().sub(camera.getWorldPosition(tmp)).normalize();CUT.setFromNormalAndCoplanarPoint(nn,c.addScaledVector(nn,-.012*radius/.16))}
   if(isStill||!list.length)return;
   if(ci<0){play(0);return}
   const m=list[ci];ct+=dt;
   if(ct<=m.d+dt)pose(scale(m.f(Math.min(ct,m.d),w,IK),amp(m,w)));
   if(ct>=m.d&&auto){gap+=dt;if(gap>1.6)play(ci+1)}}};
 if(still)pose({});
 return api}
window.UHFetal={create,movesFor,MOVES};
})();
