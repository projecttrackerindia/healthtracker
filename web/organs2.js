/* Organs 2 (approved 18 Nov 2026, canvas "Urban Health · Organs").
   - Natural look: studio light (Poly Haven HDRI, CC0), wet tissue, true tissue colours, soft shadows in folds (SSAO) on capable phones.
   - Every label sits on its own part (a point on the part's front surface, not the file's label point).
   - Take apart, breathing at your own rate, follow a drop (urine), follow a red cell (blood).
   - New: eyes, bones and joints (knee, spine, hip, shoulder, hand), teeth and mouth, prostate (adult man, himself only),
     and the nervous system (whole body, follow a signal, nerves in the feet).
   Loaded after body.html's main script; it shares that script's globals. */
const O2A={eye:'/a/organ-eye.7a4a5814.glb',teeth:'/a/organ-teeth.ce05eba8.glb',prostate:'/a/organ-male_reproductive.70fcbed3.glb',
 knee:'/a/organ-knee.ec530d5e.glb',spine:'/a/organ-spine.db5489b4.glb',hip:'/a/organ-hip.e836e480.glb',shoulder:'/a/organ-shoulder.8c1fd5f0.glb',hand:'/a/organ-hand.21b70443.glb',
 urine:'/a/tour-urine.20cbc96d.glb',bloodtour:'/a/tour-blood.6d57cae5.glb'};
const O2NEW=new Set(['eye','teeth','prostate','bones','urine','bloodtour']);
const O2=window.O2={bone:'knee',mode:{},ao:null,env:null,muscles:false};
const O2BONES=[['knee','Knee'],['spine','Spine'],['hip','Hip'],['shoulder','Shoulder'],['hand','Hand']];
const O2BEND={knee:'Bend the knee',hip:'Lift the leg',shoulder:'Raise the arm',hand:'Bend the wrist'};

/* plain words for every label we show (the model files' own texts are not always right) */
const O2D={'Right lung':'Has three lobes. Air reaches it through the right main airway.','Left lung':'Has two lobes, leaving room for the heart.','Windpipe':'The trachea carries air from the throat down to the lungs.','Bronchus':'One of the two main airways branching from the windpipe into each lung.',
 'Right kidney':'The two kidneys filter about 180 litres of blood a day and make urine.','Left kidney':'The two kidneys filter about 180 litres of blood a day and make urine.','Adrenal gland':'Sits on top of each kidney and makes hormones such as adrenaline and cortisol.','Renal artery':'Brings blood to the kidney to be filtered.','Ureter':'A thin tube that carries urine from the kidney down to the bladder.',
 'Liver':'Clears toxins, stores energy and makes bile to digest fat.','Gallbladder':'Stores bile and squeezes it into the gut after a fatty meal.','Bile duct':'Carries bile from the liver to the gut.',
 'Stomach':'Holds food and starts digesting it with acid.','Food pipe':'The oesophagus carries food from the mouth to the stomach.','Duodenum':'The first part of the small intestine.',
 'Large intestine':'Absorbs water and forms stool.','Small intestine':'Absorbs most of the nutrients from food.','Appendix':'A small pouch off the start of the large intestine.',
 'Pancreas':'Makes insulin, which keeps blood sugar in range, and juices that digest food.','Pancreatic duct':'Carries digestive juices into the gut.','Spleen':'Filters old red blood cells and helps fight infection.','Splenic artery':'Brings blood to the spleen.',
 'Bladder':'Stores urine until you pass it.','Urethra':'Carries urine out of the body.',
 'Frontal lobe':'Planning, decisions, speech and movement.','Occipital lobe':'Makes sense of what the eyes see.','Cerebellum':'Sits at the back, under the brain. It keeps your balance and makes movements smooth.','Brainstem':'Controls breathing, heart rate and sleep, and links the brain to the spinal cord.',
 'Uterus':'The womb, where a baby grows.','Ovary':'Makes eggs and the hormones oestrogen and progesterone.','Fallopian tube':'Carries the egg from the ovary to the uterus.','Cervix':'The neck of the uterus. A Pap smear checks it.',
 'Iris':'The coloured ring of muscle. It makes the pupil smaller in bright light and when you look at something near.','Tear gland':'Makes tears that keep the front of the eye wet and clean.','Optic nerve':'Carries what the eye sees to the brain.','Eye muscle':'Six small muscles turn each eye so both look at the same point.',
 'Front tooth':'Incisors cut food. Enamel, the hardest substance in the body, covers every tooth.','Molar':'Back teeth with broad tops that grind food.','Gums':'Soft tissue that seals around each tooth. Bleeding gums are often the first sign of gum disease.','Tongue':'A muscle that moves food, tastes it and helps you speak.','Lower jaw':'The mandible, the only skull bone that moves. It holds the lower teeth.',
 'Thigh bone':'The femur, the longest and strongest bone in the body.','Kneecap':'The patella, a small bone in front of the knee that helps the thigh muscle straighten the leg.','Shin bone':'The tibia carries the body’s weight from the knee to the ankle.','Fibula':'The thin bone beside the shin bone. It steadies the ankle.',
 'Neck (C1)':'The atlas, the top vertebra. It holds the skull and lets you nod.','Upper back':'Twelve thoracic vertebrae; each holds a pair of ribs.','Lower back':'Five lumbar vertebrae carry most of the body’s weight, so back pain often starts here.','Sacrum':'Five vertebrae joined into one bone that links the spine to the hips.','Disc':'A cushion between two vertebrae that absorbs shocks.',
 'Hip bone':'Forms the socket where the thigh bone turns.','Upper arm bone':'The humerus. Its round head turns in the shoulder socket.','Shoulder blade':'The scapula, a flat bone that holds the shoulder socket and anchors the shoulder muscles.','Collarbone':'The clavicle, a strut that holds the shoulder away from the chest.',
 'Thumb':'Two bones and a mobile base joint let the thumb touch each finger.','Palm bones':'Five metacarpals form the palm.','Wrist bones':'Eight small carpal bones in two rows make the wrist flexible.','Forearm bone':'The radius turns around the ulna when you turn your palm up or down.',
 'Prostate':'A walnut-sized gland under the bladder, around the tube that carries urine out. It often grows with age.','Seminal vesicle':'Small glands behind the bladder that add fluid to semen.',
 'Urine drop':'Follow it from the kidney down to the bladder.','Red blood cell':'Carries oxygen from the lungs to every part of the body.','Right atrium':'Collects blood returning from the body.','Left ventricle':'The strongest chamber. It pumps oxygen-rich blood to the whole body.','Aorta':'The body’s main artery.'};
Object.assign(OGL,{
 lung:[[/^Trachea/,'Windpipe'],[/^Right upper lobe/,'Right lung'],[/^Left upper lobe$/,'Left lung'],[/^Left main bronchus$/,'Bronchus']],
 eye:[[/^Right iris$/,'Iris'],[/^Right lacrimal gland$/,'Tear gland'],[/^Right optic nerve$/,'Optic nerve'],[/^Right lateral rectus$/,'Eye muscle']],
 teeth:[[/^Right tooth \(upper central secondary incisor\)$/,'Front tooth'],[/^Left tooth \(upper first secondary molar\)$/,'Molar'],[/^Gingiva \(gums\) \(upper jaw\)$/,'Gums'],[/^Tongue$/,'Tongue']],
 prostate:[[/^Prostate gland$/,'Prostate'],[/^Urinary bladder$/,'Bladder'],[/^Left seminal vesicle/,'Seminal vesicle']],
 urine:[[/^Right kidney$/,'Right kidney'],[/^Right ureter$/,'Ureter'],[/^Urinary bladder$/,'Bladder'],[/^Urine drop$/,'Urine drop']],
 bloodtour:[[/^Red blood cell$/,'Red blood cell'],[/^Right atrium/,'Right atrium'],[/^Left ventricle/,'Left ventricle'],[/^Arch of the aorta/,'Aorta']]});
const O2BL={knee:[[/^Right femur$/,'Thigh bone'],[/^Right patella$/,'Kneecap'],[/^Right tibia$/,'Shin bone'],[/^Right fibula$/,'Fibula']],
 spine:[[/^Atlas$/,'Neck (C1)'],[/^Thoracic vertebra \(sixth\)$/,'Upper back'],[/^Lumbar vertebra \(fourth\)$/,'Lower back'],[/^Sacrum$/,'Sacrum']],
 hip:[[/^Right hip bone$/,'Hip bone'],[/^Right femur$/,'Thigh bone'],[/^Lumbar vertebra \(fifth\)$/,'Lower back']],
 shoulder:[[/^Right humerus$/,'Upper arm bone'],[/^Right scapula$/,'Shoulder blade'],[/^Right clavicle$/,'Collarbone']],
 hand:[[/^Right phalanx \(distal thumb\)$/,'Thumb'],[/^Right metacarpal \(third\)$/,'Palm bones'],[/^Right lunate$/,'Wrist bones'],[/^Right radius$/,'Forearm bone']]};
Object.assign(ORGI,{eye:ORGI.eye||['Eyes','Your eyes','Your eyes focus light onto the retina and send what you see to the brain.'],
 urine:['Kidneys','Follow a drop','How urine is made and leaves the body.'],bloodtour:['Heart','Follow a red cell','One trip round the body takes about a minute.'],
 nerves:['Nervous system','Brain, spinal cord and nerves','Your nerves carry messages between the brain and every part of the body.']});

/* which file an organ opens */
const _ogf=ogf;
ogf=function(o){if(o==='bones')return O2A[O2.bone]||O2A.knee;if(o==='prostate')return DATA&&DATA.person&&DATA.person.priv&&STATE.base!=='female'?O2A.prostate:null;if(O2A[o])return O2A[o];return _ogf(o)};

/* ---------- natural look ---------- */
function o2Env(){if(O2.env)return Promise.resolve(O2.env);if(O2.envP)return O2.envP;
 O2.envP=new Promise(res=>{const go=()=>new THREE.RGBELoader().setDataType(THREE.UnsignedByteType).load('/a/studio.166ca6b8.hdr',tx=>{try{const pm=new THREE.PMREMGenerator(R);O2.env=pm.fromEquirectangular(tx).texture;tx.dispose();pm.dispose()}catch(_){O2.env=null}res(O2.env)},undefined,()=>res(null));
  if(THREE.RGBELoader)return go();const s=document.createElement('script');s.src='/a/rgbe.268414b5.js';s.onload=go;s.onerror=()=>res(null);document.head.appendChild(s)});return O2.envP}
const O2TINT={lung:[.95,.72,.70],kidney:[.86,.6,.56],liver:[.78,.5,.46],heart:[.85,.62,.58],brain:[.9,.76,.74],stomach:[.9,.7,.66],gut:[.9,.7,.66],pancreas:[.92,.8,.7],spleen:[.8,.55,.55],bladder:[.9,.75,.68],uterus:[.9,.68,.66],eye:[1,.96,.95],bones:[.98,.93,.86],teeth:[1,.97,.94],prostate:[.9,.7,.66],urine:[.86,.6,.56],bloodtour:[.85,.62,.58]};
const O2DRY=new Set(['bones','teeth']);
function o2Name(n){let e=n;while(e){if(e.userData&&e.userData.display_name)return e.userData.display_name;e=e.parent}return''}
function o2Kind(n){let e=n;while(e){if(e.userData&&e.userData.anatomy_kind)return e.userData.anatomy_kind;e=e.parent}return''}
async function o2Nat(root,key){const env=await o2Env();const tint=new THREE.Color(...(O2TINT[key]||[.9,.72,.68])),dry=O2DRY.has(key);
 root.traverse(n=>{if(!n.isMesh||n.userData.o2nat)return;const m0=n.material,nm=o2Name(n);if(!m0||!m0.color)return;
  const m=new THREE.MeshPhysicalMaterial({map:m0.map||null,normalMap:m0.normalMap||null,roughnessMap:m0.roughnessMap||null,color:m0.color.clone().multiply(/blood cell|urine drop/i.test(nm)?new THREE.Color(1,1,1):tint),vertexColors:m0.vertexColors,
   roughness:Math.min(1,(m0.roughness??.6)*(dry?1:.8)),metalness:0,clearcoat:dry?.2:.38,clearcoatRoughness:dry?.5:.32,sheen:new THREE.Color(dry?0x30281c:0x5a1c14),
   envMap:env,envMapIntensity:env?.55:0,transparent:m0.transparent,opacity:m0.opacity,side:m0.side,depthWrite:m0.depthWrite,morphTargets:m0.morphTargets,morphNormals:m0.morphNormals,skinning:m0.skinning});
  if(m0.normalScale&&m.normalMap)m.normalScale.copy(m0.normalScale).multiplyScalar(1.4);
  const sss=dry?.15:.35;m.onBeforeCompile=sh=>{sh.fragmentShader=sh.fragmentShader.replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\nfloat o2fr=pow(1.0-abs(dot(normalize(vViewPosition),normal)),2.0);totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.0,0.55,0.45)*o2fr*'+sss.toFixed(2)+';')};
  if(key==='eye'){if(/iris/i.test(nm)){m.color.setRGB(.2,.1,.035);m.vertexColors=false;m.map=null}if(/vitreous|retina|choroid/i.test(nm)){m.color.setRGB(.05,.02,.02);m.vertexColors=false;m.map=null}if(/^Right lens/i.test(nm)){m.color.setRGB(.06,.05,.04);m.vertexColors=false;m.map=null}
   if(/cornea|chamber/i.test(nm)){m.transparent=true;m.opacity=.1;m.depthWrite=false;m.clearcoat=.6;m.clearcoatRoughness=.05}}
  if(m0.userData&&m0.userData.o2glass){m.transparent=true;m.opacity=.18;m.depthWrite=false}
  n.material=m;n.userData.o2nat=1});o2AoWanted(true)}

/* soft shadows in the folds (screen-space ambient occlusion), only where the phone can afford it */
function o2Strong(){const mem=navigator.deviceMemory||4,cpu=navigator.hardwareConcurrency||4;return !U.still&&mem>=4&&cpu>=6&&!/[?&]noao\b/.test(location.search)||/[?&]ao=1\b/.test(location.search)}
function o2AoWanted(on){if(!on){if(O2.ao)O2.ao.on=false;return}if(!o2Strong()||O2.aoOff)return;if(O2.ao){O2.ao.on=true;return}if(O2.aoP)return;
 O2.aoP=new Promise(res=>{const s=document.createElement('script');s.src='/a/ao.93f0b553.js';s.onload=()=>{try{const pr=Math.min(devicePixelRatio,1.5),w=innerWidth,h=innerHeight;const comp=new THREE.EffectComposer(R);comp.setPixelRatio(pr);comp.setSize(w,h);
  const sp=new THREE.SSAOPass(scene,cam,w,h);sp.kernelSize=12;sp.output=THREE.SSAOPass.OUTPUT.Default;const ro=sp.renderOverride.bind(sp);
  sp.renderOverride=function(){const keep=[];for(const l in LAY){keep.push([LAY[l],LAY[l].visible]);LAY[l].visible=false}try{ro(...arguments)}finally{keep.forEach(([m,v])=>m.visible=v)}};
  comp.addPass(sp);O2.ao={comp,sp,on:true,t:[]};addEventListener('resize',()=>{if(O2.ao){O2.ao.comp.setSize(innerWidth,innerHeight)}})}catch(_){O2.aoOff=true}res()};s.onerror=()=>{O2.aoOff=true;res()};document.head.appendChild(s)})}
const _o2render=R.render.bind(R);let O2IN=false,O2LT=0;
R.render=function(sc,cm){const A=O2.ao;if(A&&A.on&&!O2IN&&sc===scene&&(OG||H3)){
  const now=performance.now();if(O2LT){A.t.push(now-O2LT);if(A.t.length>90){const avg=A.t.reduce((a,b)=>a+b,0)/A.t.length;A.t=[];if(avg>30){A.on=false;O2.aoOff=true}}}O2LT=now;
  const root=(OG&&OG.root)||(H3&&H3.root),bb=_b3.setFromObject(root),s=bb.getSize(_v3).length(),span=(cam.far-cam.near)||100;
  A.sp.kernelRadius=s*.06;A.sp.maxDistance=Math.min(.1,s*.25/span);A.sp.minDistance=A.sp.maxDistance/200;
  O2IN=true;try{A.comp.render()}finally{O2IN=false}return}
 O2LT=0;return _o2render(sc,cm)};

/* ---------- labels on the part itself ---------- */
const O2Q=new THREE.Vector3();
function o2Denorm(a,i,out){out.fromBufferAttribute(a,i);if(a.normalized){const t=a.array,k=t instanceof Int16Array?32767:t instanceof Uint16Array?65535:t instanceof Int8Array?127:t instanceof Uint8Array?255:1;out.multiplyScalar(1/k);if(k===32767||k===127)out.set(Math.max(out.x,-1),Math.max(out.y,-1),Math.max(out.z,-1))}return out}
function o2Spot(n,piv){const ms=[];n.traverse(m=>{if(m.isMesh)ms.push(m)});if(!ms.length)return null;piv.updateMatrixWorld(true);const inv=new THREE.Matrix4().copy(piv.matrixWorld).invert(),b=new THREE.Box3();
 ms.forEach(m=>b.expandByObject(m));b.applyMatrix4(inv);const c=b.getCenter(new THREE.Vector3()),sz=b.getSize(new THREE.Vector3()),r=Math.max(1e-6,Math.min(sz.x,sz.y)*.3);
 let best=null,bz=-Infinity,near=null,nd=Infinity;const p=new THREE.Vector3();
 for(const m of ms){const a=m.geometry&&m.geometry.attributes.position;if(!a)continue;const st=Math.max(1,Math.floor(a.count/6000));
  for(let i=0;i<a.count;i+=st){o2Pos(m,i,p);m.localToWorld(p);p.applyMatrix4(inv);const dx=p.x-c.x,dy=p.y-c.y,d2=dx*dx+dy*dy;
   if(d2<r*r&&p.z>bz){bz=p.z;best={m,i}}const d3=d2+(p.z-c.z)**2;if(d3<nd){nd=d3;near={m,i}}}}
 return best||near}
const O2SI=new THREE.Vector4(),O2SW=new THREE.Vector4(),O2BP=new THREE.Vector3(),O2TV=new THREE.Vector3(),O2MX=new THREE.Matrix4();
function o2Pos(m,i,out){const g=m.geometry;o2Denorm(g.attributes.position,i,out);if(!(m.isSkinnedMesh&&m.skeleton&&g.attributes.skinIndex))return out;
 const sw=g.attributes.skinWeight,si=g.attributes.skinIndex;O2SI.fromBufferAttribute(si,i);O2SW.fromBufferAttribute(sw,i);const tot=O2SW.x+O2SW.y+O2SW.z+O2SW.w||1;O2SW.multiplyScalar(1/tot);
 O2BP.copy(out).applyMatrix4(m.bindMatrix);out.set(0,0,0);for(let j=0;j<4;j++){const wt=O2SW.getComponent(j);if(!wt)continue;const bi=O2SI.getComponent(j),bn=m.skeleton.bones[bi];if(!bn)continue;O2MX.multiplyMatrices(bn.matrixWorld,m.skeleton.boneInverses[bi]);out.addScaledVector(O2TV.copy(O2BP).applyMatrix4(O2MX),wt)}
 return out.applyMatrix4(m.bindMatrixInverse)}
function o2Anch(l,out){if(!OG)return false;if(l.av===undefined)l.av=o2Spot(l.n,OG.piv||OG.root);if(!l.av)return false;o2Pos(l.av.m,l.av.i,out);l.av.m.localToWorld(out);return true}
function o2Text(u){const k=(OG&&OG.labels||[]).find(l=>l.n.userData===u),lab=k&&k.lab;if(lab&&O2D[lab])return{n:lab,d:O2D[lab]};
 let d=u.description||'',n=u.display_name||'';const kind=u.anatomy_kind||'';
 if(kind==='Muscle'&&/\bbone\b/i.test(d))d='A muscle that moves this joint.';
 if(/pulmonary (trunk|arter)/i.test(n)&&/oxygen-rich|with oxygen|fresh blood/i.test(d))d='Carries oxygen-poor blood from the heart to the lungs.';
 if(/gingiva|gums/i.test(n)&&/\bbone\b/i.test(d))d=O2D.Gums;return{n,d}}
const _ogName=ogName;ogName=function(u){return o2Text(u)};

/* ---------- the organ view ---------- */
const _vOrgan=vOrgan;
vOrgan=async function(o){o2Clean();if(o==='nerves')return o2Nerves();if(o==='bones')OGL.bones=O2BL[O2.bone];
 await _vOrgan(o);if(!OG||!VIEW||VIEW.o!==o)return;o2After(o)};
async function o2After(o){const g=OGC[ogf(o)];OG.g=g;document.body.classList.add('o2lab');
 if(O2NEW.has(o)){for(const l in LAY)LAY[l].visible=false}
 OG.root.traverse(n=>{if(!n.isMesh)return;const nm=o2Name(n),k=o2Kind(n);let hide=false;
  if(o==='eye')hide=(k==='Artery'||k==='Nerve')&&!/optic nerve/i.test(nm)||/chiasm|optic tract|lamina terminalis/i.test(nm);
  if(o==='bones')hide=!(k==='Bone'||(O2.muscles&&k==='Muscle'));
  if(o==='prostate')hide=/penis|glans|testis|epididymis|corpus|deferens/i.test(nm);
  if(o==='urine'&&STATE.base==='female')hide=/deferens|seminal|prostate/i.test(nm);
  if(o==='bloodtour'&&/lobe|atrium|ventricle|auricle/i.test(nm)){n.material.userData.o2glass=1;n.material.transparent=true;n.material.opacity=.18;n.material.depthWrite=false}
  n.visible=!hide});
 if(o==='urine'||o==='bloodtour'||o==='eye'||o==='bones'){const act=OG.mix.existingAction(OG.g.animations.find(a=>a.name!=='Explode'));if(act){act.stop();OG.mix.uncacheAction(act._clip)}}
 const front={eye:/^Right cornea$/,teeth:/upper central secondary incisor/,prostate:/^Prostate gland$/}[o];if(front)o2Face(front);
 o2Bar(o);o2Sheet(o);if(O2NEW.has(o))o2Fit(o);else if(LAY[0]){const m=LAY[0].material;m.transparent=true;m.opacity=.06;m.depthWrite=false}
 o2Nat(OG.root,o).catch(()=>{});
 if(o==='lung')o2Breath(false);if(o==='urine'||o==='bloodtour')o2Tour(o);if(o==='bones')o2Bend(0)}
/* size and centre a standalone model by its visible parts; the camera keeps it above the sheet */
function o2Fit(o){const root=OG.root,piv=OG.piv;piv.updateMatrixWorld(true);const inv=new THREE.Matrix4().copy(piv.matrixWorld).invert(),b=new THREE.Box3();
 root.traverse(n=>{if(n.isMesh&&n.visible){let v=true,e=n;while(e){if(e.visible===false){v=false;break}e=e.parent}if(v)b.expandByObject(n)}});if(b.isEmpty())return;b.applyMatrix4(inv);
 const s=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3()),T=.4,k=T/Math.max(s.x,s.y,s.z*.7);let holder=root.parent;if(holder===piv){holder=new THREE.Group();piv.remove(root);holder.add(root);piv.add(holder)}const p0=holder.position.clone();holder.scale.multiplyScalar(k);holder.position.copy(c.sub(p0).multiplyScalar(-k));
 piv.updateMatrixWorld(true);const w=new THREE.Vector3();piv.getWorldPosition(w);const ws=s.clone().multiplyScalar(k*body.scale.y);o2Frame(w,ws);OG.labels.forEach(l=>l.av=undefined)}
/* frame a box: its height fills about 40% of the screen (the part above the sheet), its width at most 78%, centred about a third down */
function o2Frame(c,sz){const H=innerHeight,cd=$('#card'),bar=$('#o2bar')&&!$('#o2bar').hidden?$('#o2bar'):$('#orgbar');
 const top=bar?bar.getBoundingClientRect().bottom+12:90,bot=cd&&cd.classList.contains('on')?H-8-cd.offsetHeight-12:H-24,fill=Math.max(.2,(bot-top)/H*.82),ndc=1-(top+bot)/H;
 const t=Math.tan(THREE.MathUtils.degToRad(cam.fov/2)),d=Math.max(sz.y/2/(t*fill),sz.x/2/(t*cam.aspect*.8))+sz.z/2;
 CAM(d,c.y-ndc*d*t,0);camZ=goalZ;camY=goalY}
/* turn the model so a named front part (the cornea, the front teeth) faces the viewer */
function o2Face(re){const root=OG.root,piv=OG.piv,c0=new THREE.Box3(),f=new THREE.Box3();root.updateMatrixWorld(true);c0.setFromObject(root);root.traverse(n=>{if(n.isMesh&&re.test(o2Name(n)))f.expandByObject(n)});if(f.isEmpty())return;
 const inv=new THREE.Matrix4().copy(piv.matrixWorld).invert(),a=c0.getCenter(new THREE.Vector3()).applyMatrix4(inv),b=f.getCenter(new THREE.Vector3()).applyMatrix4(inv),d=b.sub(a);d.y=0;if(d.lengthSq()<1e-12)return;d.normalize();
 const q=new THREE.Quaternion().setFromUnitVectors(d,new THREE.Vector3(0,0,1)),g=new THREE.Group();piv.remove(root);g.quaternion.copy(q);g.add(root);piv.add(g);OG.labels.forEach(l=>l.av=undefined)}
function o2Clean(){const b=$('#o2bar');if(b)b.remove();const c=$('#o2cap');if(c)c.remove();document.body.classList.remove('o2lab');if(O2.tick)cancelAnimationFrame(O2.tick);O2.tick=0;
 if(O2.nv){O2.nv.forEach(m=>body.remove(m));O2.nv=null}if(O2.ntm)clearInterval(O2.ntm);O2.ntm=0;const t=$('#o2tags');if(t)t.remove();O2.mode={};o2AoWanted(false)}
const _ogOff=ogOff;ogOff=function(){_ogOff();o2Clean()};
const _h3Off=h3Off;h3Off=function(){_h3Off();o2AoWanted(false)};

function o2Seg(items,on,fn){return`<div class="h3seg o2seg">${items.map(([k,t])=>`<button class="${k===on?'on':''}" onclick="${fn}('${k}')">${esc(t)}</button>`).join('')}</div>`}
function o2Bar(o){let b=$('#o2bar');if(!b){b=document.createElement('div');b.id='o2bar';document.body.appendChild(b)}const m=O2.mode[o]||'';let h='';
 const ex=OG&&OG.g&&OG.g.animations.find(a=>a.name==='Explode');
 if(o==='lung')h=o2Seg([['','Breathing'],['apart','Take apart']],m,'o2Mode')+(m?'':`<button class="chip o2c ${O2.slow?'on':''}" onclick="o2Breath(!O2.slow)">${O2.slow?'Breathing with you':'Breathe with me'}</button>`);
 else if(o==='kidney')h=o2Seg([['','Kidneys'],['drop','Follow a drop'],['apart','Take apart']],m,'o2Mode');
 else if(o==='eye')h=o2Seg([['','Outside'],['focus','Watch it focus']],m,'o2Mode');
 else if(o==='bones')h=`<div class="o2chips">${O2BONES.map(([k,t])=>`<button class="chip ${O2.bone===k?'on':''}" onclick="o2Bone('${k}')">${t}</button>`).join('')}<button class="chip ${O2.muscles?'on':''}" onclick="O2.muscles=!O2.muscles;vshow(VIEW,true)">Muscles</button></div>`;
 else if(o==='urine'||o==='bloodtour')h=`<button class="chip o2c on" onclick="o2Replay()">Replay</button><button class="chip o2c ${O2.slowT?'on':''}" onclick="O2.slowT=!O2.slowT;o2TourRate();o2Bar('${o}')">${O2.slowT?'Normal speed':'Slow'}</button>`;
 else if(o==='prostate')h='';
 else if(ex)h=o2Seg([['','Outside'],['apart','Take apart']],m,'o2Mode');
 const sl=(m==='apart'&&ex)?`<label class="o2sl"><span>Together</span><input type="range" min="0" max="100" value="${O2.exv||0}" oninput="o2Explode(this.value/100)" aria-label="Take apart"><span>Apart</span></label>`
  :(o==='bones'&&O2BEND[O2.bone])?`<label class="o2sl"><span>${O2BEND[O2.bone]}</span><input type="range" min="0" max="100" value="${Math.round((O2.bend||0)*100)}" oninput="o2Bend(this.value/100)" aria-label="${O2BEND[O2.bone]}"></label>`:'';
 b.innerHTML=h+sl;b.hidden=!b.innerHTML}
function o2Mode(k){const o=OG&&OG.o;if(!o)return;if(o==='kidney'&&k==='drop')return vgo({k:'organ',o:'urine'},'Kidneys');O2.mode[o]=k;
 if(k!=='apart'&&OG.ex){OG.ex.stop();OG.ex=null;O2.exv=0}if(o==='eye')o2Focus(k==='focus');o2Bar(o)}
function o2Explode(v){if(!OG||!OG.g)return;const c=OG.g.animations.find(a=>a.name==='Explode');if(!c)return;O2.exv=Math.round(v*100);
 if(!OG.ex){OG.ex=OG.mix.clipAction(c);OG.ex.setLoop(THREE.LoopOnce);OG.ex.clampWhenFinished=true;OG.ex.play();OG.ex.paused=true}OG.ex.time=v*c.duration;OG.mix.update(0);OG.labels.forEach(l=>l.av=undefined)}
function o2Bone(k){O2.bone=k;O2.bend=0;OGL.bones=O2BL[k];vshow(VIEW,true)}
function o2Bend(v){if(!OG||!OG.g)return;O2.bend=v;const c=OG.g.animations.find(a=>a.name!=='Explode');if(!c)return;if(!OG.bd){OG.bd=OG.mix.clipAction(c);OG.bd.play();OG.bd.paused=true}OG.bd.time=v*c.duration/2;OG.mix.update(0)}
function o2Cap(t){let c=$('#o2cap');if(!c){c=document.createElement('div');c.id='o2cap';document.body.appendChild(c)}c.hidden=!t;if(t&&c.textContent!==t)c.textContent=t;const cd=$('#card');c.style.bottom=(cd&&cd.classList.contains('on')?innerHeight-cd.getBoundingClientRect().top+10:24)+'px'}
/* lungs breathe at the person's own rate (from their last vital), or slowly with the person */
function o2Breath(slow){if(!OG||OG.o!=='lung')return;O2.slow=slow;const c=OG.g.animations.find(a=>a.name==='Breathing'),act=c&&OG.mix.existingAction(c);if(!act)return;const rr=+(DATA.vitals&&DATA.vitals.rr)||15;
 act.timeScale=U.still?0:slow?6/15:rr/15;o2Bar('lung');if(O2.tick)cancelAnimationFrame(O2.tick);
 const step=()=>{if(!OG||OG.o!=='lung')return;const ph=(act.time%c.duration)/c.duration;o2Cap(slow?(ph<.42?'Breathe in…':'Breathe out…'):`Breathing ${rr} times a minute${DATA.vitals&&DATA.vitals.rr?' · from your last check':''}`);O2.tick=requestAnimationFrame(step)};step()}
/* eye: the first half of the clip is looking near (pupil small, lens thicker), the second half far */
function o2Focus(on){if(!OG||OG.o!=='eye')return;const c=OG.g.animations.find(a=>a.name==='PupilAndFocus');if(!c)return;let act=OG.mix.existingAction(c);if(!act){act=OG.mix.clipAction(c)}
 if(!on){act.stop();o2Cap('');if(O2.tick)cancelAnimationFrame(O2.tick);return}act.timeScale=U.still?0:.5;act.play();
 const step=()=>{if(!OG||OG.o!=='eye')return;const ph=(act.time%c.duration)/c.duration;o2Cap(ph<.5?'Looking near · the pupil gets smaller and the lens thicker':'Looking far · the pupil widens and the lens flattens');O2.tick=requestAnimationFrame(step)};step()}

/* journeys: a drop of urine, a red blood cell */
const O2STEPS={urine:[[0,'Renal artery brings blood to the kidney'],[1,'The kidney’s million tiny filters clean the blood and make urine'],[1.63,'The ureter carries urine down to the bladder'],[8.24,'The bladder stores urine'],[8.91,'The urethra carries urine out of the body']],
 bloodtour:[[0,'Used blood from the upper body arrives in the superior vena cava',0],[.58,'It enters the right atrium',0],[.95,'Through the tricuspid valve',0],[1.28,'The right ventricle pumps it to the lungs',0],[2.2,'Up the pulmonary trunk',0],[3.94,'In the lungs the blood drops off carbon dioxide and picks up oxygen',1],[4.74,'Oxygen-rich blood returns in the pulmonary veins',1],[5.34,'Into the left atrium',1],[5.81,'Through the mitral valve',1],[5.98,'The left ventricle, the strongest chamber, pumps it to the whole body',1],[6.88,'Out through the aorta',1],[8.42,'Down the descending aorta to the organs and legs',1],[12.23,'The body uses the oxygen; blood comes back in the veins',0],[15.42,'Up the inferior vena cava',0],[16,'Back to the right atrium. One full loop takes about a minute.',0]]};
function o2Tour(o){const c=OG.g.animations.find(a=>a.name!=='Explode');if(!c)return;const act=OG.mix.clipAction(c);act.reset();act.setLoop(THREE.LoopRepeat);act.play();OG.tour=act;o2TourRate();
 const cell=[];OG.root.traverse(n=>{if(n.isMesh&&/red blood cell|urine drop/i.test(o2Name(n)))cell.push(n)});const S=O2STEPS[o];let last=-1;
 const step=()=>{if(!OG||OG.o!==o)return;const t=act.time%c.duration;let i=0;for(let k=0;k<S.length;k++)if(t>=S[k][0])i=k;
  if(i!==last){last=i;const el=$('#o2step');if(el){el.querySelector('.o2n').textContent=`STEP ${i+1} OF ${S.length}`;el.querySelector('.o2t').textContent=S[i][1];el.querySelectorAll('.o2d i').forEach((d,j)=>d.className=j<i?'d':j===i?'on':'')}
   if(o==='bloodtour')cell.forEach(m=>{const col=S[i][2]?0xC8102E:0x6A1530;if(m.material.color){m.material.vertexColors=false;m.material.map=null;m.material.color.set(col);m.material.needsUpdate=true}})}
  O2.tick=requestAnimationFrame(step)};if(O2.tick)cancelAnimationFrame(O2.tick);step()}
function o2TourRate(){if(OG&&OG.tour)OG.tour.timeScale=U.still?0:O2.slowT?.4:1}
function o2Replay(){if(OG&&OG.tour){OG.tour.reset();OG.tour.play()}}

/* the sheet under the organ, for the new organs and journeys (the usual results sheet stays for the others) */
function o2Find(re){return latest().find(f=>re.test(String(f.code||'')+' '+f.test))}
function o2Row(lab,f,unit){return`<div class="o2r"><span>${esc(lab)}</span><b>${f?esc(f.value)+(f.unit?' '+esc(f.unit):unit?' '+unit:''):'<em>Not on file</em>'}</b></div>`}
function o2Sheet(o){if(o==='urine'||o==='bloodtour'){const S=O2STEPS[o];sheet(`<div id="o2step" class="o2step"><div class="o2n">STEP 1 OF ${S.length}</div><div class="o2t">${esc(S[0][1])}</div><div class="o2d">${S.map((_,j)=>`<i class="${j?'':'on'}"></i>`).join('')}</div>
  ${o==='bloodtour'?'<p class="o2s">The cell turns bright red when it picks up oxygen in the lungs and darker red after the body has used it. The heart and lungs are see-through so you can follow it.</p>':STATE.base==='female'?'<p class="o2s">Shown on a male body; in women the urethra is much shorter.</p>':''}</div>
  ${o==='urine'?`<div class="o2box"><div class="ove" style="color:#8E8E93">KIDNEY RESULTS</div>${o2Row('Kidney filtering (eGFR)',o2Find(/egfr/i))}${o2Row('Creatinine',o2Find(/^creat/i))}</div>`:''}`);$('#card').classList.add('og');return}
 if(o==='prostate'){const card=$('#card');if(card)card.insertAdjacentHTML('afterbegin','<div class="o2lock">Only you see this. Not shown to family.</div>')}
 if(o==='eye'){const a1=o2Find(/hba1c/i);if(a1&&parseFloat(a1.value)>=6.5){const card=$('#card');card.insertAdjacentHTML('beforeend',`<div class="o2box"><div class="ove" style="color:#9A5B00">DIABETIC EYE CHECK · YEARLY</div><p class="o2s" style="margin:4px 0 0">With HbA1c ${esc(a1.value)}%, a yearly retina check is advised. Eye tests from your doctor show here.</p></div>`)}}}

/* ---------- nervous system: on the body model (Z-Anatomy, CC BY-SA), not a separate file ---------- */
const O2NS={signal:{re:/^Right .*(median nerve|brachial plexus)|^Right (lateral|medial) cord|spinal cord/i,steps:[[/^Right .*digital nerve|^Right median nerve/i,'Fingertip','A fingertip touches something hot.'],[/^Right median nerve/i,'Median nerve','The message races up the arm nerve, up to 120 metres a second.'],[/brachial plexus|^Right (lateral|medial) cord/i,'Brachial plexus','Nerves from the arm join at the shoulder before they enter the spine.'],[/spinal cord/i,'Spinal cord','The spinal cord pulls the hand back first: a reflex, before you feel the heat.'],[/brain|cerebr/i,'Brain','Then the message reaches the brain and you feel it: hot!']]},
 feet:{re:/sciatic|tibial nerve|plantar|fibular nerve|peroneal|sural/i}};
function o2NervIdx(re){const m=LAY[5];if(!m||!m.userData.ranges)return[];const ia=[];for(const rg of m.userData.ranges){if(re.test(SET.names[rg[2]])){const s=m.geometry.index.array.subarray(rg[5],rg[5]+rg[6]);for(const v of s)ia.push(v)}}return ia}
function o2NervMesh(re){const m=LAY[5],ia=o2NervIdx(re);if(!ia.length)return null;const g=new THREE.BufferGeometry();g.setAttribute('position',m.geometry.attributes.position);if(m.geometry.attributes.normal)g.setAttribute('normal',m.geometry.attributes.normal);g.setIndex(new THREE.BufferAttribute(new Uint32Array(ia),1));
 const h=new THREE.Mesh(g,new THREE.MeshBasicMaterial({color:0xFF3B1F,toneMapped:false,depthTest:false,transparent:true}));h.renderOrder=20;h.frustumCulled=false;body.add(h);return h}
function o2NervPt(re){const m=LAY[5];if(!m)return null;const ia=o2NervIdx(re);if(!ia.length)return null;const a=m.geometry.attributes.position,b=new THREE.Box3(),p=new THREE.Vector3();
 for(let i=0;i<ia.length;i+=3){o2Denorm(a,ia[i],p);b.expandByPoint(p)}const c=b.getCenter(new THREE.Vector3());let best=null,bd=Infinity;for(let i=0;i<ia.length;i+=3){o2Denorm(a,ia[i],p);const d=p.distanceToSquared(c);if(d<bd){bd=d;best=p.clone()}}return best}
function o2Nerves(){shape();VIEW&&(VIEW.o='nerves');head(who()+' · NERVOUS SYSTEM','Brain, spinal cord and nerves','');document.body.classList.add('orgv','o2lab');orgBar('Nervous system','nerves');setLayer('nerves');
 O2.nmode=O2.nmode||'';o2NervMode(O2.nmode)}
function o2NervMode(k){O2.nmode=k;if(O2.nv){O2.nv.forEach(m=>body.remove(m));O2.nv=null}if(O2.ntm)clearInterval(O2.ntm);O2.ntm=0;let tg=$('#o2tags');if(tg)tg.innerHTML='';
 let b=$('#o2bar');if(!b){b=document.createElement('div');b.id='o2bar';document.body.appendChild(b)}b.hidden=false;b.innerHTML=o2Seg([['','Whole body'],['signal','Follow a signal'],['feet','Hands & feet']],k,'o2NervMode');
 rot.y=0;rot.x=0;goal.y=0;goal.x=0;body.position.x=0;
 if(!k){CAM(HOME0.z*1.25,HOME0.y+.2);o2NTags([[/^Spinal cord|spinal cord/i,'Spinal cord'],[/^Right sciatic nerve/i,'Sciatic nerve'],[/^Right median nerve/i,'Nerves to the arm'],[/cerebr|brain/i,'Brain']]);
  const n=(LAY[5]&&LAY[5].userData.ranges||[]).filter(rg=>/nerve|plexus|cord|ganglion/i.test(SET.names[rg[2]])).length;
  sheet(`<div class="o2stat"><div><b>${n||'–'}</b><small>named nerve parts</small></div><div><b>31</b><small>pairs leave the spine</small></div><div><b>120 m/s</b><small>fastest signals</small></div></div>
  <p class="cd" style="color:#1D1D1F">The brain and spinal cord send and receive messages through nerves to every part of the body. Tap a nerve to see what it does.</p><button class="btn pri" style="width:100%;margin-top:10px" onclick="o2NervMode('signal')">Follow a signal</button>`)}
 else if(k==='signal'){const h=o2NervMesh(O2NS.signal.re);O2.nv=h?[h]:[];const S=O2NS.signal.steps,pts=S.map(s=>o2NervPt(s[0]));let i=0;
  if(h)o2FrameMesh(h,1.15);
  const show=()=>{const st=S[i];o2NTags([[st[0],st[1]]],pts[i]);sheet(`<div class="o2step"><div class="o2n">STEP ${i+1} OF ${S.length}</div><div class="o2t">${esc(st[2])}</div><div class="o2d">${S.map((_,j)=>`<i class="${j<i?'d':j===i?'on':''}"></i>`).join('')}</div></div><div class="ova"><button class="btn pri" onclick="o2NervMode('signal')">Replay</button></div>`);
   };show();if(!U.still)O2.ntm=setInterval(()=>{if(i>=S.length-1){clearInterval(O2.ntm);O2.ntm=0;return}i++;show()},2600)}
 else{const h=o2NervMesh(O2NS.feet.re);O2.nv=h?[h]:[];if(h)o2FrameMesh(h,1.1);
  o2NTags([[/^Right sciatic nerve/i,'Sciatic nerve'],[/^Right .*plantar nerve|plantar/i,'Sole']]);const a1=o2Find(/hba1c/i),b12=o2Find(/b12|cobalamin/i);
  sheet(`<div class="o2box" style="margin-top:0"><div class="ove" style="color:#9A5B00">FOOT NERVE CHECK${a1&&parseFloat(a1.value)>=6.5?' · YEARLY':''}</div><p class="o2s" style="margin:4px 0 0">High sugar over years can dull the nerves in the feet, so people with diabetes have their feet checked once a year and look at them daily for cuts.</p></div>
   <div class="o2box">${o2Row('HbA1c',a1)}${o2Row('Vitamin B12',b12)}<p class="o2s">Low B12 can also cause tingling. Metformin can lower B12 over time.</p></div>`)}}
function o2FrameMesh(h,pad){const ix=h.geometry.index.array,pa=h.geometry.attributes.position,b=new THREE.Box3(),q=new THREE.Vector3();for(let i=0;i<ix.length;i+=3){o2Denorm(pa,ix[i],q);b.expandByPoint(q)}body.updateMatrixWorld(true);b.applyMatrix4(body.matrixWorld);const c=b.getCenter(new THREE.Vector3()),sz=b.getSize(new THREE.Vector3()).multiplyScalar(pad);body.position.x-=c.x;c.x=0;o2Frame(c,sz)}
function o2NTags(list,pt){let el=$('#o2tags');if(!el){el=document.createElement('div');el.id='o2tags';document.body.appendChild(el)}
 O2.ntags=list.map(([re,lab],i)=>({lab,p:i===0&&pt?pt:o2NervPt(re)})).filter(t=>t.p);el.innerHTML=O2.ntags.map((t,i)=>`<span class="h3t o2nt" data-i="${i}"><i></i>${esc(t.lab)}</span>`).join('');o2NPlace()}
function o2NPlace(){const el=$('#o2tags');if(!el||!O2.ntags)return;const r=$('#gl').getBoundingClientRect(),ct=$('#card').classList.contains('on')?$('#card').getBoundingClientRect().top:innerHeight;
 el.querySelectorAll('.o2nt').forEach(b=>{const t=O2.ntags[+b.dataset.i];O2Q.copy(t.p);body.localToWorld(O2Q);O2Q.project(cam);const x=r.left+(O2Q.x+1)/2*r.width,y=r.top+(1-O2Q.y)/2*r.height;b.style.transform=`translate(${Math.round(Math.min(x-7,innerWidth-(b.offsetWidth||90)-8))}px,${Math.round(y-12)}px)`;b.style.opacity=O2Q.z<1&&y<ct-16?1:0})}
(function o2Loop(){if(O2.ntags&&$('#o2tags'))o2NPlace();requestAnimationFrame(o2Loop)})();

/* the heart: natural look and a third view, follow a red cell */
const _h3Show=h3Show;h3Show=async function(kind){await _h3Show(kind);if(H3&&H3.root)o2Nat(H3.root,'heart').catch(()=>{})};
const _h3Sub=h3Sub;h3Sub=function(){_h3Sub();const s=$('#sub .h3seg');if(s&&!s.querySelector('.o2cell'))s.insertAdjacentHTML('beforeend',`<button class="o2cell" onclick="vgo({k:'organ',o:'bloodtour'},'Heart')">Follow a cell</button>`)};

/* explore everything from the body view */
const O2EX=[['heart','Heart'],['lung','Lungs'],['kidney','Kidneys'],['liver','Liver'],['brain','Brain'],['stomach','Stomach'],['gut','Intestines'],['pancreas','Pancreas'],['spleen','Spleen'],['bladder','Bladder'],['eye','Eyes'],['teeth','Teeth and mouth'],['bones','Bones and joints'],['nerves','Nervous system']];
function o2Explore(){const P=DATA.person||{},list=O2EX.slice();if(P.priv&&STATE.base!=='female')list.push(['prostate','Prostate']);if(P.priv&&STATE.base==='female')list.push(['uterus','Uterus and ovaries']);
 sheet(`<div class="row" style="justify-content:space-between"><b style="font-size:20px">Explore your body</b><button class="x" onclick="vshow({k:'body'})" aria-label="Close">✕</button></div><div class="o2grid">${list.map(([o,t])=>`<button onclick="vgo({k:'${o==='heart'?'heart':'organ'}',o:'${o}'})">${esc(t)}</button>`).join('')}</div>`)}
const _vBody=vBody;vBody=function(){_vBody();if(KID)return;const c=$('#card');if(c&&c.classList.contains('on')&&!c.querySelector('.o2ex')){const a=c.querySelector('button.lk[onclick*="credits"]');const h=`<button class="btn sec o2ex" style="width:100%;margin-top:10px" onclick="o2Explore()">Explore organs and systems</button>`;a?a.insertAdjacentHTML('beforebegin',h):c.insertAdjacentHTML('beforeend',h)}};

(function(){const st=document.createElement('style');st.textContent=`
body.orgv.o2lab #h3tags{display:block}body.orgv.o2lab #ogpin{display:none!important}
#o2bar{position:fixed;z-index:9;left:14px;right:14px;top:calc(max(14px,env(safe-area-inset-top)) + 50px);display:flex;flex-wrap:wrap;gap:8px;justify-content:center;align-items:center;pointer-events:none}
#o2bar>*{pointer-events:auto}#o2bar .h3seg{background:rgba(255,255,255,.92);box-shadow:0 2px 10px rgba(0,0,0,.1);border:0;height:38px}
#o2bar .chip,.o2chips .chip{height:36px;border-radius:18px;border:0;background:rgba(255,255,255,.92);box-shadow:0 2px 10px rgba(0,0,0,.08);font:600 13.5px Geist,Inter,sans-serif;color:#1D1D1F;padding:0 14px}
#o2bar .chip.on,.o2chips .chip.on{background:#1D1D1F;color:#fff}
.o2chips{display:flex;gap:6px;overflow-x:auto;max-width:100%;scrollbar-width:none;padding:2px}.o2chips::-webkit-scrollbar{display:none}
.o2sl{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.92);border-radius:22px;padding:0 16px;height:44px;box-shadow:0 2px 10px rgba(0,0,0,.08);font:600 12.5px Geist,Inter,sans-serif;color:#6E6E73;width:min(360px,100%);box-sizing:border-box}
.o2sl input{flex:1;-webkit-appearance:none;appearance:none;height:4px;border-radius:2px;background:#E5E5EA;outline:none}
.o2sl input::-webkit-slider-thumb{-webkit-appearance:none;width:28px;height:28px;border-radius:14px;background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.3);border:0}
.o2sl input::-moz-range-thumb{width:28px;height:28px;border-radius:14px;background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.3);border:0}
#o2cap{position:fixed;z-index:7;left:50%;transform:translateX(-50%);text-align:center;pointer-events:none}#o2cap[hidden]{display:none}#o2cap:not([hidden]){display:block;width:max-content;max-width:calc(100vw - 48px);box-sizing:border-box;background:rgba(255,255,255,.92);border-radius:16px;padding:7px 14px;font:600 13px Geist,Inter,sans-serif;color:#1D1D1F;box-shadow:0 2px 10px rgba(0,0,0,.08)}
.o2seg button{white-space:nowrap}.o2cell{border:0;background:none;border-radius:15px;padding:0 14px;font:600 14px Geist,Inter,sans-serif;color:#3A3A3C;white-space:nowrap}
.o2step .o2n{font-size:12px;font-weight:700;letter-spacing:.06em;color:#0062C4}.o2step .o2t{font-size:19px;font-weight:700;letter-spacing:-.01em;margin-top:4px;line-height:1.3}
.o2d{display:flex;gap:5px;margin-top:12px}.o2d i{flex:1;height:4px;border-radius:2px;background:#E5E5EA}.o2d i.d{background:#7FB5F0}.o2d i.on{background:#0071E3}
.o2s{font-size:13.5px;color:#6E6E73;line-height:1.45;margin:10px 0 0}
.o2box{background:#F5F5F7;border-radius:18px;padding:12px 14px;margin-top:12px}.o2r{display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;font-size:15px}.o2r b{font-size:17px}.o2r em{font-style:normal;font-weight:500;font-size:13px;color:#8E8E93}
.o2lock{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:#1A7F37;background:#E8F8EE;border-radius:14px;padding:5px 11px;margin:4px 0 8px}
.o2stat{display:flex;gap:8px}.o2stat div{flex:1;background:#F5F5F7;border-radius:16px;padding:10px 12px}.o2stat b{display:block;font-size:19px;letter-spacing:-.02em;white-space:nowrap}.o2stat small{font-size:11.5px;color:#6E6E73}
.o2grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.o2grid button{border:0;background:#F5F5F7;border-radius:16px;min-height:52px;font:600 15px Geist,Inter,sans-serif;color:#1D1D1F;text-align:left;padding:0 14px}
#o2tags{position:fixed;inset:0;pointer-events:none;z-index:4}#o2tags .h3t{pointer-events:none}
body.dk #o2bar .h3seg,body.dk #o2bar .chip,body.dk .o2sl,body.dk #o2cap{background:rgba(44,44,46,.92);color:#fff}body.dk .o2box,body.dk .o2stat div,body.dk .o2grid button{background:#2C2C2E;color:#fff}
`;document.head.appendChild(st)})();
