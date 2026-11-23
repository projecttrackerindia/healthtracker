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
const O2HD={"kidney":"/a/hd-kidneys.12183e3b.glb","liver":"/a/hd-liver.92d8c06d.glb","lung":"/a/hd-lungs.49c72407.glb","stomach":"/a/hd-stomach.b5f00da1.glb","gut":"/a/hd-intestines.5744978f.glb","pancreas":"/a/hd-pancreas.cd45ca4f.glb","spleen":"/a/hd-spleen.71b696f9.glb","bladder":"/a/hd-bladder.404971b8.glb","brain":"/a/hd-brain.d2c57a4b.glb","eye":"/a/hd-eye.098c9684.glb","knee":"/a/hd-knee.0ccbfec3.glb","spine":"/a/hd-spine.896a50ab.glb","hip":"/a/hd-hip.298a7e49.glb","shoulder":"/a/hd-shoulder.22cac574.glb","hand":"/a/hd-hand.15c716b8.glb","foot":"/a/hd-foot.b99795b7.glb","teeth":"/a/hd-teeth.439f3881.glb","prostate":"/a/hd-male_reproductive.ea6ad577.glb","footlod":"/a/organ-foot.10bb9c44.glb"};O2A.foot=O2HD.footlod;delete O2HD.footlod;
const O2NEW=new Set(['eye','teeth','prostate','bones','urine','bloodtour']);
const O2=window.O2={cs:(()=>{const m=location.search.match(/[?&]cs=(num|edge|tap|card)/);return m?m[1]:'num'})(),bone:'knee',mode:{},ao:null,env:null,muscles:false,hd:(()=>{try{const v=localStorage.getItem('uh-hd');if(v)return v==='1'}catch(_){}return null})()};
/* joints built from the HD body (Z-Anatomy, CC BY-SA 4.0) with every named ligament, cartilage, nerve and vessel: tools/make_joints.py */
const O2JOINT={"elbow":"/a/joint-elbow.a0fb828b.glb","wrist":"/a/joint-wrist.8cf318fc.glb","ankle":"/a/joint-ankle.b2f7a163.glb","neck":"/a/joint-neck.bf470dd0.glb","skull":"/a/joint-skull.f5ccf94d.glb"};Object.assign(O2A,O2JOINT);Object.assign(O2HD,O2JOINT);
const O2BONES=[['knee','Knee'],['spine','Spine'],['hip','Hip'],['shoulder','Shoulder'],['elbow','Elbow'],['wrist','Wrist'],['hand','Hand'],['ankle','Ankle'],['foot','Foot'],['neck','Neck'],['skull','Skull']];
const O2BEND={knee:'Bend the knee',hip:'Lift the leg',shoulder:'Raise the arm',hand:'Bend the wrist',foot:'Point the foot'};

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
 'Forehead bone':'The frontal bone forms the forehead and the roof of the eye sockets; the frontal sinus sits inside it.','Parietal bone':'Two parietal bones form the top and sides of the skull, joined at the sutures.','Lower jaw':'The mandible, the only skull bone that moves, for chewing and speaking.','Cheekbone':'The zygomatic bone shapes the cheek and the outer rim of the eye socket.','Temporal bone':'Holds the ear canal, the middle and inner ear, and the jaw joint.',
 'Neck (C1)':'The atlas, the top vertebra. It holds the skull and lets you nod.','Upper back':'Twelve thoracic vertebrae; each holds a pair of ribs.','Lower back':'Five lumbar vertebrae carry most of the body’s weight, so back pain often starts here.','Sacrum':'Five vertebrae joined into one bone that links the spine to the hips.','Disc':'A cushion between two vertebrae that absorbs shocks.',
 'Hip bone':'Forms the socket where the thigh bone turns.','Upper arm bone':'The humerus. Its round head turns in the shoulder socket.','Shoulder blade':'The scapula, a flat bone that holds the shoulder socket and anchors the shoulder muscles.','Collarbone':'The clavicle, a strut that holds the shoulder away from the chest.',
 'Thumb':'Two bones and a mobile base joint let the thumb touch each finger.',
 'Ulna':'The forearm bone on the little-finger side. Its hook at the back is the point of your elbow.','Radius':'The forearm bone on the thumb side. It turns around the ulna when you turn your palm up or down.',
 'Annular ligament':'A ring of ligament that holds the head of the radius against the ulna while it turns.','Inner elbow ligament':'The ulnar collateral ligament steadies the inner elbow; throwing sports can strain it.',
 'Ulnar nerve':'Runs behind the inner elbow, the "funny bone". It feels the little finger and moves the small hand muscles.',
 'Scaphoid':'The wrist bone most often broken in a fall on an outstretched hand.','Lunate':'A moon-shaped wrist bone in the middle of the first row.',
 'Cartilage cushion':'The triangular fibrocartilage cushions the little-finger side of the wrist.','Median nerve':'Passes through the carpal tunnel; pressure on it causes carpal tunnel syndrome.',
 'Achilles tendon':'The strongest tendon in the body, joining the calf muscles to the heel bone.',
 'Forehead bone':'The frontal bone forms the forehead and the roof of the eye sockets; the frontal sinus sits inside it.','Parietal bone':'Two parietal bones form the top and sides of the skull, joined at the sutures.','Lower jaw':'The mandible, the only skull bone that moves, for chewing and speaking.','Cheekbone':'The zygomatic bone shapes the cheek and the outer rim of the eye socket.','Temporal bone':'Holds the ear canal, the middle and inner ear, and the jaw joint.',
 'Neck (C1)':'The atlas, the ring-shaped top vertebra that holds the skull and lets you nod.','C2':'The axis; its peg lets the head turn side to side.',
 'Disc C5–C6':'The disc most often worn or bulging in the neck.','Vertebral artery':'Runs up through holes in the neck vertebrae to supply the back of the brain.',
 'Carotid artery':'The main artery to the head and brain; the pulse you feel at the side of the neck.','Palm bones':'Five metacarpals form the palm.','Wrist bones':'Eight small carpal bones in two rows make the wrist flexible.','Forearm bone':'The radius turns around the ulna when you turn your palm up or down.',
 'Ankle bone':'The talus carries the body’s weight from the shin bone to the foot.','Heel bone':'The calcaneus, the largest foot bone; the Achilles tendon attaches to it.','Big toe metatarsal':'The long bone behind the big toe; it takes much of the push when you walk.','Big toe':'Two bones; the big toe gives the final push of every step.',
 'Spinal cord':'Carries messages between the brain and the body; nerves leave it in 31 pairs.','Sciatic nerve':'The thickest nerve, from the lower back down the back of each leg.','Nerves to the arm':'Branches of the brachial plexus that move and feel the arm and hand.','Brain':'Receives every message from the body and decides what to do.','Median nerve':'Runs down the middle of the forearm to the thumb side of the hand.','Brachial plexus':'A web of nerves at the neck and shoulder that supplies the arm.','Fingertip':'Dense touch and temperature sensors; the signal starts here.','Tibial nerve':'Runs down the back of the leg to the sole of the foot.','Sole of the foot':'Plantar nerves give feeling to the sole; diabetes can dull them.',
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
 foot:[[/^Right talus$/,'Ankle bone'],[/^Right calcaneus$/,'Heel bone'],[/^Right metatarsal \(first\)$/,'Big toe metatarsal'],[/^Right phalanx \(proximal big toe\)$/,'Big toe']],
 hand:[[/^Right phalanx \(distal thumb\)$/,'Thumb'],[/^Right metacarpal \(third\)$/,'Palm bones'],[/^Right lunate$/,'Wrist bones'],[/^Right radius$/,'Forearm bone']],
 elbow:[[/^Right humerus$/,'Upper arm bone'],[/^Right ulna$/,'Ulna'],[/^Right radius$/,'Radius'],[/^Right annular ligament of radius$/,'Annular ligament'],[/^Right ulnar collateral ligament$/,'Inner elbow ligament'],[/^Right ulnar nerve$/,'Ulnar nerve']],
 wrist:[[/^Right scaphoid bone$/,'Scaphoid'],[/^Right lunate bone$/,'Lunate'],[/^Right articular disc of distal radio-ulnar joint$/,'Cartilage cushion'],[/^Right median nerve$/,'Median nerve'],[/^Right radius$/,'Radius']],
 ankle:[[/^Right talus$/,'Ankle bone'],[/^Right calcaneus$/,'Heel bone'],[/^Right tibia$/,'Shin bone'],[/^Right fibula$/,'Fibula'],[/^Right calcaneal tendon$/,'Achilles tendon']],
 skull:[[/^Frontal bone$/,'Forehead bone'],[/^Left parietal bone$/,'Parietal bone'],[/^Mandible$/,'Lower jaw'],[/^Right zygomatic bone$/,'Cheekbone'],[/^Left temporal bone$/,'Temporal bone']],
 neck:[[/^Atlas C1$/,'Neck (C1)'],[/^Axis C2$/,'C2'],[/^Intervertebral disc C5-C6$/,'Disc C5–C6'],[/^Right vertebral artery$/,'Vertebral artery'],[/^Right common carotid artery$/,'Carotid artery']]};
Object.assign(ORGI,{eye:ORGI.eye||['Eyes','Your eyes','Your eyes focus light onto the retina and send what you see to the brain.'],
 urine:['Kidneys','Follow a drop','How urine is made and leaves the body.'],bloodtour:['Heart','Follow a red cell','One trip round the body takes about a minute.'],
 nerves:['Nervous system','Brain, spinal cord and nerves','Your nerves carry messages between the brain and every part of the body.']});

/* which file an organ opens */
const _ogf=ogf;
function o2Hd(){return O2.hd===null?o2Strong():O2.hd}
ogf=function(o){if(o==='prostate'&&!(DATA&&DATA.person&&DATA.person.priv&&STATE.base!=='female'))return null;const k=o==='bones'?O2.bone:o;if(o2Hd()&&O2HD[k]&&(STATE.base!=='female'||!OGF_F[o]))return O2HD[k];if(o==='bones')return O2A[O2.bone]||O2A.knee;if(o==='prostate')return DATA&&DATA.person&&DATA.person.priv&&STATE.base!=='female'?O2A.prostate:null;if(O2A[o])return O2A[o];return _ogf(o)};

/* ---------- natural look ---------- */
function o2Env(){if(O2.env)return Promise.resolve(O2.env);if(O2.envP)return O2.envP;
 O2.envP=new Promise(res=>{const go=()=>new THREE.RGBELoader().setDataType(THREE.UnsignedByteType).load('/a/studio.166ca6b8.hdr',tx=>{try{const pm=new THREE.PMREMGenerator(R);O2.env=pm.fromEquirectangular(tx).texture;tx.dispose();pm.dispose()}catch(_){O2.env=null}res(O2.env)},undefined,()=>res(null));
  if(THREE.RGBELoader)return go();const s=document.createElement('script');s.src='/a/rgbe.268414b5.js';s.onload=go;s.onerror=()=>res(null);document.head.appendChild(s)});return O2.envP}
const O2TINT={lung:[.95,.72,.70],kidney:[.86,.6,.56],liver:[.78,.5,.46],heart:[.85,.62,.58],brain:[.9,.76,.74],stomach:[.9,.7,.66],gut:[.9,.7,.66],pancreas:[.92,.8,.7],spleen:[.8,.55,.55],bladder:[.9,.75,.68],uterus:[.9,.68,.66],eye:[1,.96,.95],bones:[.98,.93,.86],teeth:[1,.97,.94],prostate:[.9,.7,.66],urine:[.86,.6,.56],bloodtour:[.85,.62,.58]};
const O2DRY=new Set(['bones','teeth']);
function o2Name(n){let e=n;while(e){if(e.userData&&e.userData.display_name)return e.userData.display_name;e=e.parent}return''}
function o2Kind(n){let e=n,k='';while(e){if(e.userData&&e.userData.anatomy_kind){k=e.userData.anatomy_kind;break}e=e.parent}const nm=o2Name(n);
 if(k==='Bone'&&/fibularis|tibialis|flexor|extensor|abductor|adductor|lumbrical|interosseous muscle|opponens|gastrocnemius|soleus|popliteus|plantaris/i.test(nm))return'Muscle';
 if(k==='Bone'&&/iliotibial tract|interosseous membrane/i.test(nm))return'Connective tissue';return k}
/* soft shadow in creases, worked out once per model on the CPU (so phones without SSAO get it too):
   each vertex is darkened by how far it sits below the average of its neighbours */
function o2Cav(g){if(!g||g.attributes.o2cav)return;const P=g.attributes.position,n=P.count,cav=new Float32Array(n).fill(1),Na=g.attributes.normal;
 if(g.index&&Na&&n<400000){/* raw (possibly quantised) values are fine: the measure is relative to edge length */
  const p=new Float32Array(n*3),N=new Float32Array(n*3);for(let i=0;i<n;i++){p[i*3]=P.getX(i);p[i*3+1]=P.getY(i);p[i*3+2]=P.getZ(i);const x=Na.getX(i),y=Na.getY(i),z=Na.getZ(i),L=Math.hypot(x,y,z)||1;N[i*3]=x/L;N[i*3+1]=y/L;N[i*3+2]=z/L}
  const I=g.index.array,S=new Float32Array(n*3),K=new Uint16Array(n),E=new Float32Array(n);
  for(let i=0;i<I.length;i+=3)for(let e=0;e<3;e++){const a=I[i+e],b=I[i+(e+1)%3],l=Math.hypot(p[a*3]-p[b*3],p[a*3+1]-p[b*3+1],p[a*3+2]-p[b*3+2]);S[a*3]+=p[b*3];S[a*3+1]+=p[b*3+1];S[a*3+2]+=p[b*3+2];K[a]++;E[a]+=l;S[b*3]+=p[a*3];S[b*3+1]+=p[a*3+1];S[b*3+2]+=p[a*3+2];K[b]++;E[b]+=l}
  for(let i=0;i<n;i++){if(!K[i])continue;const d=((S[i*3]/K[i]-p[i*3])*N[i*3]+(S[i*3+1]/K[i]-p[i*3+1])*N[i*3+1]+(S[i*3+2]/K[i]-p[i*3+2])*N[i*3+2])/((E[i]/K[i])||1);cav[i]=1-.5*Math.min(1,Math.max(0,d*2.4))}}
 g.setAttribute('o2cav',new THREE.BufferAttribute(cav,1))}
async function o2Nat(root,key){const env=await o2Env();const tint=new THREE.Color(...(O2TINT[key]||[.9,.72,.68])),dry=O2DRY.has(key);
 root.traverse(n=>{if(!n.isMesh||n.userData.o2nat)return;const m0=n.material,nm=o2Name(n);if(!m0||!m0.color)return;
  const m=new THREE.MeshPhysicalMaterial({map:m0.map||null,normalMap:m0.normalMap||null,roughnessMap:m0.roughnessMap||null,color:m0.color.clone().multiply(/blood cell|urine drop/i.test(nm)?new THREE.Color(1,1,1):tint),vertexColors:m0.vertexColors,
   roughness:Math.min(1,(m0.roughness??.6)*(dry?1:.8)),metalness:0,clearcoat:dry?.2:.38,clearcoatRoughness:dry?.5:.32,sheen:new THREE.Color(dry?0x30281c:0x5a1c14),
   envMap:env,envMapIntensity:env?.55:0,transparent:m0.transparent,opacity:m0.opacity,side:m0.side,depthWrite:m0.depthWrite,morphTargets:m0.morphTargets,morphNormals:m0.morphNormals,skinning:m0.skinning});
  if(m0.normalScale&&m.normalMap)m.normalScale.copy(m0.normalScale).multiplyScalar(1.4);
  /* reflections kept low so form reads from the key light, as in an atlas photograph */
  m.envMapIntensity=env?(dry?.16:.3):0;if(dry)m.color.multiplyScalar(.9);o2Cav(n.geometry);
  const sss=dry?.15:.35;m.onBeforeCompile=sh=>{sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute float o2cav;varying float vCav;').replace('#include <begin_vertex>','#include <begin_vertex>\nvCav=o2cav;');
   sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying float vCav;').replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.rgb*=vCav;').replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\nfloat o2fr=pow(1.0-abs(dot(normalize(vViewPosition),normal)),2.0);totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.0,0.55,0.45)*o2fr*'+sss.toFixed(2)+';')};
  m.customProgramCacheKey=()=>'o2nat-cav-'+sss;
  if(key==='eye'){if(/iris/i.test(nm)){m.color.setRGB(.2,.1,.035);m.vertexColors=false;m.map=null}if(/vitreous|retina|choroid/i.test(nm)){m.color.setRGB(.05,.02,.02);m.vertexColors=false;m.map=null}if(/^Right lens/i.test(nm)){m.color.setRGB(.06,.05,.04);m.vertexColors=false;m.map=null}
   if(/cornea|chamber/i.test(nm)){m.transparent=true;m.opacity=.1;m.depthWrite=false;m.clearcoat=.6;m.clearcoatRoughness=.05}}
  if(m0.userData&&m0.userData.o2glass){m.transparent=true;m.opacity=.18;m.depthWrite=false}
  n.material=m;n.userData.o2nat=1;
  /* a bone cut where the close-up ends shows a solid cut face (the inside drawn flat, the colour of cut bone) */
  let q=n,cut=false;while(q){if(q.userData&&q.userData.cut){cut=true;break}q=q.parent}
  if(cut&&!n.userData.o2cap){m.side=THREE.FrontSide;const cm=new THREE.MeshBasicMaterial({color:new THREE.Color(0xC9A98A).convertSRGBToLinear(),side:THREE.BackSide});const cap=new THREE.Mesh(n.geometry,cm);cap.raycast=()=>{};cap.userData.o2cap=1;cap.userData.o2nat=1;n.add(cap);n.userData.o2cap=1}});o2AoWanted(true)}

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
  if(o==='bones')hide=O2JOINT[O2.bone]?(k==='Muscle'&&!O2.muscles):!(k==='Bone'||(O2.muscles&&k==='Muscle'));
  if(o==='prostate')hide=/penis|glans|testis|epididymis|corpus|deferens/i.test(nm);
  if(o==='urine'&&STATE.base==='female')hide=/deferens|seminal|prostate/i.test(nm);
  if(o==='bloodtour'&&/lobe|atrium|ventricle|auricle/i.test(nm)){n.material.userData.o2glass=1;n.material.transparent=true;n.material.opacity=.18;n.material.depthWrite=false}
  n.visible=!hide});
 if(o==='urine'||o==='bloodtour'||o==='eye'||o==='bones'){const act=OG.mix.existingAction(OG.g.animations.find(a=>a.name!=='Explode'));if(act){act.stop();OG.mix.uncacheAction(act._clip)}}
 const front={eye:/^Right cornea$/,teeth:/upper central secondary incisor/,prostate:/^Prostate gland$/}[o];if(front)o2Face(front);
 o2Bar(o);o2Sheet(o);if(O2NEW.has(o)){o2Fit(o);if(innerWidth>=900)o2WideShift()}else{if(LAY[0]){const m=LAY[0].material;m.transparent=true;m.opacity=.06;m.depthWrite=false}if(innerWidth>=900)o2WideFit()}
 o2Nat(OG.root,o).catch(()=>{});
 if(o==='lung')o2Breath(false);if(o==='urine'||o==='bloodtour')o2Tour(o);if(o==='bones')o2Bend(0)}
/* size and centre a standalone model by its visible parts; the camera keeps it above the sheet */
function o2Fit(o){const root=OG.root,piv=OG.piv;piv.updateMatrixWorld(true);const inv=new THREE.Matrix4().copy(piv.matrixWorld).invert(),b=new THREE.Box3();
 root.traverse(n=>{if(n.isMesh&&n.visible){let v=true,e=n;while(e){if(e.visible===false){v=false;break}e=e.parent}if(v)b.expandByObject(n)}});if(b.isEmpty())return;b.applyMatrix4(inv);
 const s=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3()),T=.4,k=T/Math.max(s.x,s.y,s.z*.7);let holder=root.parent;if(holder===piv){holder=new THREE.Group();piv.remove(root);holder.add(root);piv.add(holder)}const p0=holder.position.clone();holder.scale.multiplyScalar(k);holder.position.copy(c.sub(p0).multiplyScalar(-k));
 piv.updateMatrixWorld(true);const w=new THREE.Vector3();piv.getWorldPosition(w);const ws=s.clone().multiplyScalar(k*body.scale.y);o2Frame(w,ws);OG.labels.forEach(l=>l.av=undefined)}
/* frame a box: its height fills about 40% of the screen (the part above the sheet), its width at most 78%, centred about a third down */
function o2Frame(c,sz){const H=innerHeight,cd=$('#card'),bar=$('#o2bar')&&!$('#o2bar').hidden?$('#o2bar'):$('#orgbar');
 const top=bar?bar.getBoundingClientRect().bottom+12:90,bot=o2Side()?H-24:cd&&cd.classList.contains('on')?H-8-cd.offsetHeight-12:H-24,bot2=O2.cs==='num'?bot-52:bot,fill=Math.max(.2,(bot2-top)/H*.82),ndc=1-(top+bot2)/H,wf=O2.cs==='edge'?Math.max(.4,(innerWidth-2*112)/innerWidth):.8;
 const t=Math.tan(THREE.MathUtils.degToRad(cam.fov/2)),d=Math.max(sz.y/2/(t*fill),sz.x/2/(t*cam.aspect*wf))+sz.z/2;
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
  ${o==='urine'?`<div class="o2box"><div class="ove" style="color:var(--ink3)">KIDNEY RESULTS</div>${o2Row('Kidney filtering (eGFR)',o2Find(/egfr/i))}${o2Row('Creatinine',o2Find(/^creat/i))}</div>`:''}`);$('#card').classList.add('og');return}
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
 else{const h=o2NervMesh(O2NS.feet.re);O2.nv=h?[h]:[];
  o2NTags([[/^Right tibial nerve/i,'Tibial nerve'],[/^Right (medial|lateral) plantar nerve/i,'Sole of the foot']]);const a1=o2Find(/hba1c/i),b12=o2Find(/b12|cobalamin/i);
  sheet(`<div class="o2box" style="margin-top:0"><div class="ove" style="color:#9A5B00">FOOT NERVE CHECK${a1&&parseFloat(a1.value)>=6.5?' · YEARLY':''}</div><p class="o2s" style="margin:4px 0 0">High sugar over years can dull the nerves in the feet, so people with diabetes have their feet checked once a year and look at them daily for cuts.</p></div>
   <div class="o2box">${o2Row('HbA1c',a1)}${o2Row('Vitamin B12',b12)}<p class="o2s">Low B12 can also cause tingling. Metformin can lower B12 over time.</p></div>`);o2FrameRe(/tibial nerve|plantar|fibular nerve|peroneal|sural/i,1.15)}}
/* frame the body on the nerves matching a name (after the sheet is in, so the space above it is known) */
function o2FrameRe(re,pad){const m=LAY[5];if(!m)return;const ix=o2NervIdx(re),pa=m.geometry.attributes.position,b=new THREE.Box3(),q=new THREE.Vector3();for(let i=0;i<ix.length;i+=3){o2Denorm(pa,ix[i],q);b.expandByPoint(q)}if(b.isEmpty())return;
 body.updateMatrixWorld(true);b.applyMatrix4(body.matrixWorld);const c=b.getCenter(new THREE.Vector3()),sz=b.getSize(new THREE.Vector3()).multiplyScalar(pad);body.position.x-=c.x;c.x=0;o2Frame(c,sz)}
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
 sheet(`<div class="row" style="justify-content:space-between"><b style="font-size:20px">Explore your body</b><button class="x" onclick="vshow({k:'body'})" aria-label="Close">✕</button></div><div class="o2grid">${list.map(([o,t])=>`<button onclick="${o==='ar'?'arStart()':o==='cut'||o==='measure'?`vgo({k:'${o}'})`:`vgo({k:'${o==='heart'?'heart':'organ'}',o:'${o}'})`}">${esc(t)}</button>`).join('')}</div>`)}
const _vBody=vBody;vBody=function(){_vBody();if(KID)return;const c=$('#card');if(c&&c.classList.contains('on')&&!c.querySelector('.o2ex')){const a=c.querySelector('button.lk[onclick*="credits"]');const h=`<button class="btn sec o2ex" style="width:100%;margin-top:10px" onclick="vgo({k:'explore'},'Body')">Explore your body</button>`;a?a.insertAdjacentHTML('beforebegin',h):c.insertAdjacentHTML('beforeend',h)}};

(function(){const st=document.createElement('style');st.textContent=`
body.orgv.o2lab #h3tags{display:block}body.orgv.o2lab #ogpin{display:none!important}
#o2bar{position:fixed;z-index:9;left:14px;right:14px;top:calc(max(14px,env(safe-area-inset-top)) + 50px);display:flex;flex-wrap:wrap;gap:8px;justify-content:center;align-items:center;pointer-events:none}
#o2bar>*{pointer-events:auto}#o2bar .h3seg{background:rgba(255,255,255,.92);box-shadow:0 2px 10px rgba(0,0,0,.1);border:0;height:38px}
#o2bar .chip,.o2chips .chip{height:36px;border-radius:18px;border:0;background:rgba(255,255,255,.92);box-shadow:0 2px 10px rgba(0,0,0,.08);font:600 13.5px Geist,Inter,sans-serif;color:#1D1D1F;padding:0 14px}
#o2bar .chip.on,.o2chips .chip.on{background:#1D1D1F;color:#fff}
.o2chips{display:flex;gap:6px;overflow-x:auto;max-width:100%;scrollbar-width:none;padding:2px}.o2chips::-webkit-scrollbar{display:none}
.o2sl{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.92);border-radius:22px;padding:0 16px;height:44px;box-shadow:0 2px 10px rgba(0,0,0,.08);font:600 12.5px Geist,Inter,sans-serif;color:var(--ink2);width:min(360px,100%);box-sizing:border-box}
.o2sl input{flex:1;-webkit-appearance:none;appearance:none;height:4px;border-radius:2px;background:#E5E5EA;outline:none}
.o2sl input::-webkit-slider-thumb{-webkit-appearance:none;width:28px;height:28px;border-radius:14px;background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.3);border:0}
.o2sl input::-moz-range-thumb{width:28px;height:28px;border-radius:14px;background:#fff;box-shadow:0 1px 5px rgba(0,0,0,.3);border:0}
#o2cap{position:fixed;z-index:7;left:50%;transform:translateX(-50%);text-align:center;pointer-events:none}#o2cap[hidden]{display:none}#o2cap:not([hidden]){display:block;width:max-content;max-width:calc(100vw - 48px);box-sizing:border-box;background:rgba(255,255,255,.92);border-radius:16px;padding:7px 14px;font:600 13px Geist,Inter,sans-serif;color:#1D1D1F;box-shadow:0 2px 10px rgba(0,0,0,.08)}
.o2seg button{white-space:nowrap}.o2cell{border:0;background:none;border-radius:15px;padding:0 14px;font:600 14px Geist,Inter,sans-serif;color:#3A3A3C;white-space:nowrap}
.o2step .o2n{font-size:12px;font-weight:700;letter-spacing:.06em;color:#0062C4}.o2step .o2t{font-size:19px;font-weight:700;letter-spacing:-.01em;margin-top:4px;line-height:1.3}
.o2d{display:flex;gap:5px;margin-top:12px}.o2d i{flex:1;height:4px;border-radius:2px;background:#E5E5EA}.o2d i.d{background:#7FB5F0}.o2d i.on{background:#2F5BFF}
.o2s{font-size:13.5px;color:var(--ink2);line-height:1.45;margin:10px 0 0}
.o2box{background:#F2F2EF;border-radius:18px;padding:12px 14px;margin-top:12px}.o2r{display:flex;justify-content:space-between;align-items:baseline;padding:6px 0;font-size:15px}.o2r b{font-size:17px}.o2r em{font-style:normal;font-weight:500;font-size:13px;color:var(--ink3)}
.o2lock{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:#1A7F37;background:#E8F8EE;border-radius:14px;padding:5px 11px;margin:4px 0 8px}
.o2stat{display:flex;gap:8px}.o2stat div{flex:1;background:#F2F2EF;border-radius:16px;padding:10px 12px}.o2stat b{display:block;font-size:19px;letter-spacing:-.02em;white-space:nowrap}.o2stat small{font-size:11.5px;color:var(--ink2)}
.o2grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.o2grid button{border:0;background:#F2F2EF;border-radius:16px;min-height:52px;font:600 15px Geist,Inter,sans-serif;color:#1D1D1F;text-align:left;padding:0 14px}
#o2tags{position:fixed;inset:0;pointer-events:none;z-index:4}#o2tags .h3t{pointer-events:none}
body.dk #o2bar .h3seg,body.dk #o2bar .chip,body.dk .o2sl,body.dk #o2cap{background:rgba(44,44,46,.92);color:#fff}body.dk .o2box,body.dk .o2stat div,body.dk .o2grid button{background:#2C2C2E;color:#fff}
`;document.head.appendChild(st)})();

/* ===================== Callouts (19 Nov): a dot on the part, a thin line, the name and what it does at the side ===================== */
/* wide screens put the sheet in a side panel on the right: the free space is then everything to its left */
function o2Side(){const cd=$('#card');if(!cd||!cd.classList.contains('on'))return null;const r=cd.getBoundingClientRect();return r.left>innerWidth*.4&&(r.height>innerHeight*.45||innerWidth>=980)?r:null}
function o2Band(){const H=innerHeight,cd=$('#card'),sd=o2Side();let top=70;for(const id of ['o2bar','orgbar','sub']){const e=$('#'+id);if(e&&!e.hidden&&e.getClientRects().length&&getComputedStyle(e).display!=='none'){const b=e.getBoundingClientRect().bottom;if(b>top&&b<H*.5)top=b}}
 return{top:top+8,bot:sd?H-16:cd&&cd.classList.contains('on')?cd.getBoundingClientRect().top-8:H-16,right:sd?sd.left-12:innerWidth}}
function o2Short(t){t=String(t||'').replace(/^[^:]{0,60}:\s*/,'');const m=t.match(/^.{20,}?[.;](\s|$)/);return(m?m[0]:t).trim().replace(/[;]$/,'.').replace(/^./,c=>c.toUpperCase())}
function o2Call(items){let el=$('#o2call');if(!items||!items.length){if(el)el.hidden=true;return}
 if(!el){el=document.createElement('div');el.id='o2call';el.innerHTML='<svg aria-hidden="true"></svg><div></div>';document.body.appendChild(el)}el.hidden=false;
 const sv=el.firstChild,box=el.lastChild,sig=items.map(i=>i.k+'|'+i.name+'|'+(i.sel?1:0)).join(';');
 if(el.dataset.sig!==sig){el.dataset.sig=sig;box.innerHTML=items.map((i,j)=>`<button class="o2lab2${i.sel?' sel':''}" data-j="${j}"><b>${esc(i.name)}</b>${i.def?`<small>${esc(i.def)}</small>`:''}</button>`).join('');
  box.querySelectorAll('button').forEach(b=>b.onclick=()=>{const it=O2.calls&&O2.calls[+b.dataset.j];it&&it.on&&it.on()})}
 O2.calls=items;const W=innerWidth,LW=O2.cs==='edge'?96:Math.min(164,W*.4),P=O2.cs==='edge'?12:10,{top,bot}=o2Band(),btn=box.children;
 const vis=items.map((i,j)=>Object.assign(i,{j,h:btn[j]?btn[j].offsetHeight||34:34})).filter(i=>i.ok&&i.y>top&&i.y<bot&&i.x>0&&i.x<W);
 const cx=vis.length?vis.reduce((a,i)=>a+i.x,0)/vis.length:W/2;let L=vis.filter(i=>i.x<cx),R=vis.filter(i=>i.x>=cx);
 while(L.length-R.length>1){L.sort((a,b)=>b.x-a.x);R.push(L.shift())}while(R.length-L.length>1){R.sort((a,b)=>a.x-b.x);L.push(R.shift())}
 const lay=g=>{g.sort((a,b)=>a.y-b.y);let y=top;g.forEach(i=>{i.ly=Math.max(i.y-i.h/2,y);y=i.ly+i.h+6});const over=y-6-bot;if(over>0){let lim=bot;for(let k=g.length-1;k>=0;k--){g[k].ly=Math.min(g[k].ly,lim-g[k].h);lim=g[k].ly-6}}g.forEach(i=>i.ly=Math.max(top,i.ly))};lay(L);lay(R);
 let path='';const show=new Set();
 const put=(i,left)=>{const b=btn[i.j];if(!b)return;show.add(i.j);const x=left?P:W-P-LW;b.style.width=LW+'px';b.style.textAlign=left?'right':'left';b.style.transform=`translate(${x}px,${Math.round(i.ly)}px)`;
  const ey=i.ly+Math.min(i.h/2,16),ex=left?P+LW:W-P-LW,kx=left?ex+10:ex-10;path+=`<path d="M${i.x.toFixed(1)} ${i.y.toFixed(1)}L${kx} ${ey.toFixed(1)}L${ex} ${ey.toFixed(1)}" class="${i.sel?'s':''}"/><circle cx="${i.x.toFixed(1)}" cy="${i.y.toFixed(1)}" r="4" class="${i.sel?'s':''}"/>`};
 L.forEach(i=>put(i,true));R.forEach(i=>put(i,false));sv.setAttribute('viewBox',`0 0 ${W} ${innerHeight}`);sv.innerHTML=path;
 [...btn].forEach((b,j)=>{const on=show.has(j);b.style.opacity=on?1:0;b.style.pointerEvents=on?'auto':'none'})}
/* label styles under test (?cs=num|edge|tap): keep the model readable */
const _o2Call=o2Call;o2Call=function(items){if(O2.cs==='card')return _o2Call(items);let el=$('#o2call');
 if(!items||!items.length){if(el)el.hidden=true;const lg=$('#o2leg');if(lg)lg.hidden=true;return}
 const sel=items.find(i=>i.sel);
 if(O2.cs==='tap'){const one=sel?[Object.assign({},sel)]:[];if(el)el.classList.add('tap');_o2Call(one.length?one:null);const h=$('#o2hint');const show=!sel;let hh=h;if(!hh){hh=document.createElement('div');hh.id='o2hint';hh.textContent='Tap any part to name it';document.body.appendChild(hh)}hh.hidden=!show;const {bot}=o2Band();hh.style.top=(bot-40)+'px';return}
 if(O2.cs==='edge'){items=items.map(i=>Object.assign(i,{def:i.sel?i.def:''}));if(el)el.classList.add('edge');const r=_o2Call(items);el=$('#o2call');el.classList.add('edge');return r}
 /* num: numbered dots on the parts, names in a strip above the sheet */
 if(!el){el=document.createElement('div');el.id='o2call';el.innerHTML='<svg aria-hidden="true"></svg><div></div>';document.body.appendChild(el)}el.hidden=false;el.classList.add('num');el.firstChild.innerHTML='';
 const {top,bot:bot0,right:RX}=o2Band(),W=RX||innerWidth,box=el.lastChild;let bot=bot0;{const cp=$('#o2cap');if(cp&&!cp.hidden&&cp.getClientRects().length&&getComputedStyle(cp).display!=='none'){const r=cp.getBoundingClientRect();if(r.height&&r.top<bot-4)bot=Math.min(bot,r.top+8)}}
 const ks=items.map(i=>i.k+':'+i.name).join('|');if(!O2.numOrder||O2.numSig!==ks){O2.numSig=ks;O2.numOrder=items.map((i,j)=>j).sort((a,b)=>items[a].y-items[b].y||items[a].x-items[b].x)}
 const no={};O2.numOrder.forEach((j,n)=>no[j]=n+1);
 const sig='n'+items.map(i=>i.k+':'+i.name+(i.sel?'*':'')).join('|');if(box.dataset.sig!==sig){box.dataset.sig=sig;box.innerHTML=items.map((i,j)=>`<button class="o2num${i.sel?' sel':''}" data-j="${j}" aria-label="${esc(i.name)}">${no[j]}</button>`).join('');box.querySelectorAll('button').forEach(b=>b.onclick=()=>{const it=items[+b.dataset.j];it&&it.on&&it.on()})}
 /* keep dots apart: a dot that would sit on another moves clear, with a hairline back to its exact spot */
 const placed=[];let lines='';O2.numOrder.forEach(j=>{const i=items[j],bt=box.children[j];if(!bt)return;const on=i&&i.ok&&i.y>top&&i.y<bot-52&&i.x>0&&i.x<W;bt.style.opacity=on?1:0;bt.style.pointerEvents=on?'auto':'none';if(!on)return;
  let x=i.x,y=i.y;for(let it=0;it<8;it++){let hit=null;for(const q of placed){const dx=x-q.x,dy=y-q.y;if(dx*dx+dy*dy<24*24){hit=q;break}}if(!hit)break;let dx=x-hit.x,dy=y-hit.y,l=Math.hypot(dx,dy);if(l<.5){dx=i.x<W/2?-1:1;dy=0;l=1}x=hit.x+dx/l*25;y=hit.y+dy/l*25}
  x=Math.max(14,Math.min(W-14,x));placed.push({x,y});bt.style.transform=`translate(${Math.round(x-11)}px,${Math.round(y-11)}px)`;
  if(Math.hypot(x-i.x,y-i.y)>4)lines+=`<path d="M${i.x.toFixed(1)} ${i.y.toFixed(1)}L${x.toFixed(1)} ${y.toFixed(1)}" class="${i.sel?'s':''}"/><circle cx="${i.x.toFixed(1)}" cy="${i.y.toFixed(1)}" r="2.5" class="nd${i.sel?' s':''}"/>`});
 el.firstChild.setAttribute('viewBox',`0 0 ${innerWidth} ${innerHeight}`);el.firstChild.innerHTML=lines;
 let lg=$('#o2leg');if(!lg){lg=document.createElement('div');lg.id='o2leg';document.body.appendChild(lg)}lg.hidden=false;let lt=bot-44;{const cp=$('#o2cap');if(cp&&!cp.hidden&&cp.getClientRects().length&&getComputedStyle(cp).display!=='none'){const r=cp.getBoundingClientRect();if(r.height&&r.top<lt+40)lt=r.top-44}}lg.style.top=lt+'px';lg.style.right=(innerWidth-W)+'px';
 const ls='l'+sig;if(lg.dataset.sig!==ls){lg.dataset.sig=ls;lg.innerHTML=O2.numOrder.map(j=>{const i=items[j];return`<button class="${i.sel?'sel':''}" data-j="${j}"><i>${no[j]}</i>${esc(i.name)}</button>`}).join('');lg.querySelectorAll('button').forEach(b=>b.onclick=()=>{const it=items[+b.dataset.j];it&&it.on&&it.on()});const s=lg.querySelector('.sel');if(s)s.scrollIntoView({inline:'center',block:'nearest'});else if(lg.dataset.org!==ks){lg.scrollLeft=0}lg.dataset.org=ks}};
(()=>{const st=document.createElement('style');st.textContent=`
#o2call.num circle.nd{fill:#1D1D1F;stroke:none}#o2call.num circle.nd.s{fill:#2F5BFF}
.o2num{position:absolute;left:0;top:0;width:22px;height:22px;border-radius:11px;border:0;padding:0;background:rgba(255,255,255,.94);color:#1D1D1F;font:700 11.5px/22px Geist,Inter,sans-serif;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.22),0 0 0 1px rgba(0,0,0,.06);transition:opacity .2s}
.o2num::before{content:'';position:absolute;inset:-11px}
.o2num.sel{background:#2F5BFF;color:#fff;transform-origin:center;box-shadow:0 0 0 4px rgba(47,91,255,.22)}
#o2leg{position:fixed;left:0;right:0;z-index:5;display:flex;gap:8px;overflow-x:auto;padding:0 16px;scrollbar-width:none;-webkit-overflow-scrolling:touch;scroll-snap-type:x proximity}
#o2leg[hidden]{display:none}#o2leg::-webkit-scrollbar{display:none}
#o2leg button{flex:none;scroll-snap-align:start;display:flex;align-items:center;gap:7px;height:36px;padding:0 13px 0 6px;border:0;border-radius:18px;background:rgba(255,255,255,.9);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);box-shadow:0 1px 4px rgba(0,0,0,.08);font:600 13px Geist,Inter,sans-serif;color:#1D1D1F;white-space:nowrap}
#o2leg i{font-style:normal;width:24px;height:24px;border-radius:12px;background:#F2F2EF;font:700 11.5px/24px Geist,Inter,sans-serif;text-align:center}
#o2leg button.sel{background:#2F5BFF;color:#fff}#o2leg button.sel i{background:rgba(255,255,255,.25);color:#fff}
#o2call.edge .o2lab2{background:none;box-shadow:none;-webkit-backdrop-filter:none;backdrop-filter:none;padding:2px 0}
#o2call.edge .o2lab2 b{font-size:12px;font-weight:600;line-height:1.25;text-shadow:0 0 3px #F2F2EF,0 0 6px #F2F2EF}
#o2call.edge .o2lab2.sel{background:none;color:#2F5BFF}#o2call.edge .o2lab2.sel small{display:none}
body.dk .o2num{background:rgba(44,44,46,.94);color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.12)}body.dk #o2leg button{background:rgba(44,44,46,.9);color:#fff}body.dk #o2leg i{background:#3A3A3C;color:#fff}body.dk #o2leg button.sel,body.dk .o2num.sel{background:#2F5BFF;color:#fff}
body.dk #orgbar span,body.dk #orgbar button{background:rgba(44,44,46,.92);color:#fff;box-shadow:0 2px 10px rgba(0,0,0,.4)}body.dk #orgbar svg[stroke]{stroke:#fff}body.dk #orgbar svg[fill='#1D1D1F']{fill:#fff}body.dk .h3seg{background:rgba(44,44,46,.92);border-color:transparent}body.dk .h3seg button{color:#EBEBF5}body.dk .h3seg .on{background:#F2F2EF;color:#1D1D1F}body.dk .fx[style*='EEF0FF']{background:#2A2A3C!important;color:#F2F2EF}
@media (min-width:900px){#o2bar{right:calc(min(420px,38vw) + 32px)}}
@media (max-height:740px){#card.og,body.h3 #card,body.ov #card{max-height:38vh!important}}
#o2hint{position:fixed;left:50%;transform:translateX(-50%);z-index:5;background:rgba(255,255,255,.9);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-radius:16px;padding:8px 14px;font:600 13px Geist,Inter,sans-serif;color:#3A3A3C;box-shadow:0 1px 4px rgba(0,0,0,.08);pointer-events:none}#o2hint[hidden]{display:none}
`;document.head.appendChild(st)})();
const O2P=new THREE.Vector3();
function o2Scr(v){const r=$('#gl').getBoundingClientRect();O2P.copy(v).project(cam);return{x:r.left+(O2P.x+1)/2*r.width,y:r.top+(1-O2P.y)/2*r.height,ok:O2P.z<1}}
/* organ views */
ogPlace=function(){if(!OG){o2Call(null);return}const items=OG.labels.map((l,i)=>{const ok=o2Anch(l,O2Q),p=o2Scr(O2Q);return{k:'l'+i,x:p.x,y:p.y,ok:ok&&p.ok,name:l.lab,def:O2D[l.lab]||o2Short(l.n.userData.description),sel:OG.sel===l.n,on:()=>ogPick(l.n)}});
 if(OG.sel&&!OG.labels.some(l=>l.n===OG.sel)){const l={n:OG.sel};if(!OG.selL||OG.selL.n!==OG.sel)OG.selL=l;const ok=o2Anch(OG.selL,O2Q),p=o2Scr(O2Q),t=o2Text(OG.sel.userData);items.push({k:'sel',x:p.x,y:p.y,ok:ok&&p.ok,name:t.n,def:o2Short(t.d),sel:true,on:()=>{}})}
 o2Call(items)};
/* the heart: same callouts */
h3Place=function(){const el=$('#h3tags');if(el)el.style.display='none';if(!H3||!H3.root){o2Call(null);return}const items=[];
 h3L().forEach(([code,name])=>{const o=H3.nodes[name];if(!o)return;const info=H3P.find(p=>p[3]===code);if(!o.userData.o2l)o.userData.o2l={n:o};const l=o.userData.o2l;if(l.av===undefined)l.av=o2Spot(o,H3.piv||H3.root);if(!l.av)return;o2Pos(l.av.m,l.av.i,O2Q);l.av.m.localToWorld(O2Q);const p=o2Scr(O2Q);
  items.push({k:code,x:p.x,y:p.y,ok:p.ok,name:info[1].replace('Coronary arteries','Coronary artery'),def:o2Short(info[2]),sel:!!(H3.sel&&h3Info(H3.sel.name)===info),on:()=>h3Go(code)})});o2Call(items)};
/* wide screens: the side panel takes the right; frame the organ in the space to its left, centred there, big enough to read */
function o2Free(){const W=innerWidth;return innerWidth>=900?W-(Math.min(420,W*.38)+32):W}
function o2WideFit(){if(!OG||!OG.root)return;body.updateMatrixWorld(true);const b=new THREE.Box3();OG.root.traverse(n=>{if(n.isMesh&&n.visible)b.expandByObject(n)});if(b.isEmpty())return;
 const W=innerWidth,F=o2Free(),c=b.getCenter(new THREE.Vector3()),sz=b.getSize(new THREE.Vector3());o2FrameBand(c,sz,F/W*.86);
 const t=Math.tan(THREE.MathUtils.degToRad(cam.fov/2)),d=goalZ-c.z;body.position.x+=-c.x-((W-F)/2/W)*2*d*t*cam.aspect;OG.labels&&OG.labels.forEach(l=>l.av=undefined)}
function o2WideShift(){if(!OG||!OG.root)return;body.updateMatrixWorld(true);const b=new THREE.Box3();OG.root.traverse(n=>{if(n.isMesh&&n.visible)b.expandByObject(n)});if(b.isEmpty())return;
 const W=innerWidth,F=o2Free(),c=b.getCenter(new THREE.Vector3()),t=Math.tan(THREE.MathUtils.degToRad(cam.fov/2)),d=goalZ-c.z;body.position.x+=-c.x-((W-F)/2/W)*2*d*t*cam.aspect;OG.labels&&OG.labels.forEach(l=>l.av=undefined)}
/* frame the heart in the space left between the controls and the sheet, so short screens never put it under the buttons */
function o2FrameBand(c,sz,wf){wf=wf||.8;const H=innerHeight,{top,bot}=o2Band(),b2=O2.cs==='num'?bot-52:bot,fill=Math.max(.18,(b2-top)/H*.86),ndc=1-(top+b2)/H;
 const t=Math.tan(THREE.MathUtils.degToRad(cam.fov/2)),d=Math.max(sz.y/2/(t*fill),sz.x/2/(t*cam.aspect*wf))+sz.z/2;CAM(d,c.y-ndc*d*t,0);camZ=goalZ;camY=goalY}
function o2HeartFit(){if(!H3||!H3.root||MODE!=='heartv'||innerHeight>=740||innerWidth>=700)return;body.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(H3.root);if(b.isEmpty())return;o2FrameBand(b.getCenter(new THREE.Vector3()),b.getSize(new THREE.Vector3()))}
const _h3Show2=h3Show;h3Show=async function(k){await _h3Show2(k);requestAnimationFrame(()=>requestAnimationFrame(o2HeartFit));if(H3&&H3.root)H3.root.traverse(o=>{if(o.userData&&o.userData.o2l)o.userData.o2l.av=undefined})};
/* nervous system */
o2NPlace=function(){if(!O2.ntags||!$('#o2tags')){return}const t=$('#o2tags');t.innerHTML='';o2Call(O2.ntags.map((g,i)=>{O2Q.copy(typeof g.p==='function'?g.p():g.p);body.localToWorld(O2Q);const p=o2Scr(O2Q);return{k:'n'+i,x:p.x,y:p.y,ok:p.ok,name:g.lab,def:O2D[g.lab]||'',sel:false,on:()=>{}}}))};
const _o2Clean=o2Clean;o2Clean=function(){_o2Clean();o2Call(null);O2.ntags=null};
const _h3Off2=h3Off;h3Off=function(){_h3Off2();o2Call(null)};

/* ===================== Selecting a part: everything else fades, nothing is painted ===================== */
function o2Ghost(root,keep){root.traverse(m=>{if(!m.isMesh||!m.material)return;let on=!keep,q=m;while(q&&!on){if(q===keep)on=true;q=q.parent}const mt=m.material;
 if(!m.userData.o2m)m.userData.o2m={t:mt.transparent,o:mt.opacity,d:mt.depthWrite};const o=m.userData.o2m;if(mt.emissive){mt.emissive.set(0);mt.emissiveIntensity=0}
 if(on){mt.transparent=o.t;mt.opacity=o.o;mt.depthWrite=o.d}else{mt.transparent=true;mt.opacity=Math.min(o.o,.12);mt.depthWrite=false}mt.needsUpdate=true})}
function o2Facts(u,n){const k=o2Kind(n)||u.anatomy_kind||'',f=String(u.fma_ids||'').split(/[,; ]+/).filter(Boolean).map(x=>x.replace(/^FMA:?/i,'FMA '));return[k,u.system&&u.system!=='organ'&&u.system.toLowerCase()!==k.toLowerCase()?u.system:'',...f].filter(Boolean)}
ogPick=function(n){if(!OG||!n)return;OG.sel=n;o2Ghost(OG.root,n);const u=n.userData||{},t=o2Text(u),fx=o2Facts(u,n),lab=(OG.labels.find(l=>l.n===n)||{}).lab;
 sheet(`<div class="row" style="justify-content:space-between"><button class="lk" onclick="ogClear()">‹ ${esc((ORGI[OG.o]||[OG.o,OG.o])[1])}</button><button class="x" onclick="ogClear()" aria-label="Close">✕</button></div>
 <div class="cn" style="font-size:22px;margin-top:4px">${esc(lab||t.n.replace(/\s*\((reconstructed surface|parenchyma)\)/i,''))}</div>${lab&&lab!==t.n?`<div class="o2tn">${esc(u.display_name||'')}</div>`:''}
 ${fx.length?`<div class="o2fx">${fx.map(x=>`<span>${esc(x)}</span>`).join('')}</div>`:''}
 <p class="cd" style="color:#1D1D1F">${esc(String(lab&&O2D[lab]?O2D[lab]:t.d).replace(/^[^:]{0,60}:\s*/,'').replace(/^./,c=>c.toUpperCase()))}</p>
 <div class="ova"><button class="btn sec" onclick="o2Atlas()">All parts</button><button class="btn pri" onclick="send('ask',{q:'Explain the ${esc((lab||t.n).toLowerCase().replace(/'/g,''))}: what it does and what can go wrong'})">${T('ask')}</button></div>`)};
ogClear=function(){if(!OG)return;OG.sel=null;o2Ghost(OG.root,null);vshow(VIEW,true)};
/* every part of the model, grouped and searchable */
const O2KO=['Organ','Bone','Cartilage','Muscle','Connective tissue','Artery','Vein','Nerve','Gland','Duct'];
function o2Atlas(q){if(!OG)return;const seen=new Map();OG.root.traverse(n=>{const u=n.userData;if(u&&u.display_name&&!seen.has(u.display_name)){let vis=false;n.traverse(m=>{if(m.isMesh&&m.visible)vis=true});if(vis)seen.set(u.display_name,n)}});
 const all=[...seen.entries()],by={};all.forEach(([nm,n])=>{const k=o2Kind(n)||'Other';(by[k]=by[k]||[]).push([nm,n])});OG.atlas=all.map(x=>x[1]);
 const ks=Object.keys(by).sort((a,b)=>(O2KO.indexOf(a)+99)%99-(O2KO.indexOf(b)+99)%99||a.localeCompare(b)),hdOn=o2Hd(),hasHd=!!O2HD[OG.o==='bones'?O2.bone:OG.o];
 sheet(`<div class="row" style="justify-content:space-between"><b style="font-size:20px">All parts · ${all.length}</b><button class="x" onclick="ogClear()" aria-label="Close">✕</button></div>
 <input class="o2q" type="search" placeholder="Search ${all.length} parts" aria-label="Search parts" oninput="o2AtlasF(this.value)" value="${esc(q||'')}">
 ${hasHd?`<div class="o2hd"><span>Detail</span><div class="h3seg"><button class="${hdOn?'':'on'}" onclick="o2SetHd(false)">Standard</button><button class="${hdOn?'on':''}" onclick="o2SetHd(true)">Full</button></div></div>`:''}
 <div id="o2al">${ks.map(k=>`<div class="o2ak" data-k="${esc(k)}">${esc(k==='Organ'?'Organs and parts':k+(by[k].length>1&&!/s$/.test(k)?'s':''))} · ${by[k].length}</div>${by[k].sort((a,b)=>a[0].localeCompare(b[0])).map(([nm,n])=>`<button class="o2ar" data-i="${OG.atlas.indexOf(n)}" onclick="ogPick(OG.atlas[${OG.atlas.indexOf(n)}])"><span>${esc(nm)}</span><small>${esc((String(n.userData.fma_ids||'').split(/[,; ]+/)[0]||'').replace(/^FMA:?/i,'FMA '))}</small></button>`).join('')}`).join('')}</div>
 <p class="o2s">Names and FMA identifiers from the Foundational Model of Anatomy; shapes from BodyParts3D (CC BY 4.0).</p>`);if(q)o2AtlasF(q)}
function o2AtlasF(q){q=String(q||'').toLowerCase().trim();const l=$('#o2al');if(!l)return;l.querySelectorAll('.o2ar').forEach(b=>{b.hidden=!!q&&!b.textContent.toLowerCase().includes(q)});l.querySelectorAll('.o2ak').forEach(h=>{let n=h.nextElementSibling,any=false;while(n&&n.classList.contains('o2ar')){if(!n.hidden)any=true;n=n.nextElementSibling}h.hidden=!any})}
function o2SetHd(on){O2.hd=on;try{localStorage.setItem('uh-hd',on?'1':'0')}catch(_){}vshow(VIEW,true).then(()=>setTimeout(o2Atlas,400))}
const _o2Bar=o2Bar;o2Bar=function(o){_o2Bar(o);const b=$('#o2bar');if(!b||!OG)return;b.insertAdjacentHTML('beforeend',`<button class="chip o2c" onclick="o2Atlas()">All parts</button>`);b.hidden=false};

/* the heart: a picked part stays, the rest fades (no paint on the part) */
function o2GhostP(root,on){root.traverse(m=>{if(!m.isMesh||!m.material)return;const mt=m.material;if(!m.userData.o2m)m.userData.o2m={t:mt.transparent,o:mt.opacity,d:mt.depthWrite};const o=m.userData.o2m;if(mt.emissive){mt.emissive.set(0);mt.emissiveIntensity=0}
 if(on(m)){mt.transparent=o.t;mt.opacity=o.o;mt.depthWrite=o.d}else{mt.transparent=true;mt.opacity=Math.min(o.o,.14);mt.depthWrite=false}mt.needsUpdate=true})}
const _h3Pick=h3Pick;h3Pick=function(o,keep){_h3Pick(o,keep);if(!H3||!H3.root)return;const info=h3Info(o.name);o2GhostP(H3.root,m=>{const n=h3Name(m);return !!(n&&h3Info(n.name)===info)})};
const _h3Back=h3Back;h3Back=function(){if(H3&&H3.root)o2GhostP(H3.root,()=>true);_h3Back()};
/* ===================== Reports, medicines and specialists open on the right part ===================== */
function o2BonePick(){const t=latest().filter(f=>f.org==='bones').map(f=>(f.raw||'')+' '+f.test+' '+(f.rep||'')).join(' ');
 return /\b(dexa|dxa|bmd|bone (mineral )?density|t.?score|lumbar|spine|vertebr|cervical|thoracic)/i.test(t)?'spine':/\bhip\b|femoral neck|pelvi/i.test(t)?'hip':/knee|patell/i.test(t)?'knee':/shoulder|humer|clavic/i.test(t)?'shoulder':/wrist|hand|finger|carpal/i.test(t)?'hand':/ankle|foot|heel|toe|calcan/i.test(t)?'foot':null}
const _vOrgan2=vOrgan;vOrgan=async function(o){if(o==='bones'&&!O2.boneUser){const b=O2.boneStart||o2BonePick();if(b)O2.bone=b}return _vOrgan2(o)};
const _o2Bone=o2Bone;o2Bone=function(k){O2.boneUser=true;_o2Bone(k)};
/* the nervous system shows any nerve tests on file */
const _o2NervMode=o2NervMode;o2NervMode=function(k){_o2NervMode(k);if(k)return;const fs=latest().filter(f=>f.org==='nerves');if(!fs.length)return;const c=$('#card');if(!c)return;
 c.insertAdjacentHTML('beforeend',`<div class="o2box"><div class="ove" style="color:var(--ink3)">YOUR NERVE TESTS</div>${fs.map(f=>`<div class="o2r"><span>${esc(f.test.replace(/\s*\(.*\)/,''))}</span><b style="color:${FCOL(f)}">${esc(f.value)}${f.unit?' '+esc(f.unit):''}</b></div>`).join('')}</div>`)};
/* a specialist's consult opens on the part they look after (the uterus and prostate never open here) */
function o2Spec(d){const s=String(d.specialty||'').toLowerCase(),F=d.findings||[],v=c=>{const f=F.find(x=>String(x.code||'').toLowerCase()===c);return f?parseFloat(f.value):NaN};
 if(/ophthal|eye|retina|optom|cornea|glaucoma/.test(s))return'organ:eye';if(/dent|orthodont|oral|maxillo|periodont|endodont/.test(s))return'organ:teeth';
 if(/neuro/.test(s))return'organ:nerves';if(/ortho|bone|joint|spine|rheumat|sports med/.test(s)){O2.boneStart=null;O2.boneUser=false;return'organ:bones'}
 if(/cardio|heart/.test(s))return'heartv';if(/pulmo|chest|respir|lung|tb\b/.test(s))return'organ:lung';if(/nephro|kidney|urolog|androl/.test(s))return'organ:kidney';
 if(/endocrin|diabet|thyroid/.test(s)){const t=v('tsh');return t>4.5||t<.4?'organ:thyroid':'organ:pancreas'}if(/hepat|liver/.test(s))return'organ:liver';if(/gastro|digest/.test(s))return'organ:stomach';return''}
const _boot=boot;boot=async function(d){if(d&&d.specialty&&!d.start){const st=o2Spec(d);if(st)d.start=st}return _boot(d)};
/* medicines: where they work (prostate only for the man himself) */
(function(){const P=(re,o)=>DRUGS.unshift([re,o]);
 const cal=DRUGS.find(x=>x[0].test('calcium'));if(cal){cal[1].works=[['bones','Keeps bones strong (absorbed in the gut)']];cal[1].watch=[['bones','Vitamin D and calcium levels yearly']]}
 const met=DRUGS.find(x=>x[0].test('metformin'));if(met){met[1].watch=(met[1].watch||[]).concat([['nerves','Check vitamin B12 once a year; low B12 can cause tingling']])}
 P(/alendron|risedron|ibandron|zoledron|denosumab/i,{works:[['bones','Slows bone loss so bones stay stronger']],side:[['stomach','Heartburn; take with a full glass of water and stay upright 30 minutes']],watch:[['bones','Bone density (DEXA) every 2 years']],avoid:'Lying down right after the tablet.'});
 P(/timolol|latanoprost|bimatoprost|travoprost|brimonidine|dorzolamide|brinzolamide/i,{works:[['eye','Lowers the pressure inside the eye to protect the optic nerve']],side:[['eye','Mild stinging or redness.']],watch:[['eye','Eye pressure check as advised']],avoid:'Stopping the drops without the eye doctor.'});
 P(/pregabalin|gabapentin|lyrica|duloxetine|amitriptyline/i,{works:[['nerves','Calms nerve pain and tingling']],side:[['brain','Drowsiness or dizziness.']],watch:[['nerves','Tell the doctor how the pain changes']],avoid:'Alcohol. Driving if drowsy.'});
 P(/methylcobalamin|mecobalamin|cyanocobalamin|vitamin b ?12|neurobion/i,{works:[['nerves','Helps nerves repair and work properly']],side:[],watch:[['nerves','B12 level after 3 months']],avoid:''});
 P(/tamsulosin|silodosin|alfuzosin|finasteride|dutasteride|urimax/i,{works:[['prostate','Relaxes the prostate so urine flows more easily']],side:[['heart','Dizziness on standing up.']],watch:[['prostate','PSA and urine flow as advised']],avoid:'Standing up quickly after the first dose.'})})();
const _vMed=vMed;vMed=function(name){const d=(DRUGS.find(x=>x[0].test(name))||[])[1];let keep=null;if(d&&!(DATA.person&&DATA.person.priv)){keep=d.works;d.works=d.works.filter(w=>!/prostate|uterus/.test(w[0]))}try{return _vMed(name)}finally{if(keep)d.works=keep}};

(function(){const st=document.createElement('style');st.textContent=`
#h3tags{display:none!important}
#o2call{position:fixed;inset:0;pointer-events:none;z-index:5}#o2call[hidden]{display:none}#o2call svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
#o2call path{fill:none;stroke:rgba(29,29,31,.55);stroke-width:1}#o2call path.s{stroke:#2F5BFF;stroke-width:1.5}
#o2call circle{fill:#fff;stroke:#1D1D1F;stroke-width:1.5}#o2call circle.s{fill:#2F5BFF;stroke:#fff;stroke-width:2}
.o2lab2{position:absolute;left:0;top:0;border:0;background:rgba(255,255,255,.86);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border-radius:12px;padding:5px 9px 6px;font-family:Manrope,Geist,Inter,sans-serif;color:#1D1D1F;box-shadow:0 1px 6px rgba(0,0,0,.08);transition:opacity .2s;box-sizing:border-box;min-height:32px}
.o2lab2 b{display:block;font-size:12.5px;font-weight:700;line-height:1.25}.o2lab2 small{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:11px;line-height:1.3;color:#5A5A5F;margin-top:1px}
.o2lab2.sel{background:#2F5BFF;color:#fff}.o2lab2.sel small{color:rgba(255,255,255,.88)}
body.dk .o2lab2{background:rgba(44,44,46,.88);color:#fff}body.dk .o2lab2 small{color:#C7C7CC}body.dk #o2call path{stroke:rgba(255,255,255,.55)}body.dk #o2call circle{fill:#1C1C1E;stroke:#fff}
.o2tn{font-size:13px;color:var(--ink2);margin-top:2px}.o2fx{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.o2fx span{background:#F2F2EF;border-radius:10px;padding:3px 9px;font-size:12px;font-weight:600;color:#3A3A3C}
.o2q{width:100%;box-sizing:border-box;height:44px;border-radius:22px;border:0;background:#F2F2EF;padding:0 16px;font:500 15px Geist,Inter,sans-serif;margin-top:10px;outline:none}
.o2hd{display:flex;align-items:center;justify-content:space-between;margin-top:10px;font-size:14px;font-weight:600;color:#3A3A3C}.o2hd .h3seg{background:#F2F2EF;border:0}
.o2ak{font-size:12px;font-weight:700;letter-spacing:.05em;color:var(--ink3);text-transform:uppercase;margin:16px 2px 6px}
.o2ar{display:flex;width:100%;justify-content:space-between;align-items:center;gap:10px;border:0;background:none;border-bottom:1px solid #F2F2EF;min-height:44px;padding:0 2px;font:500 15px Geist,Inter,sans-serif;color:#1D1D1F;text-align:left}.o2ar small{color:var(--ink3);font-size:12px;flex:none}
body.dk .o2fx span,body.dk .o2q,body.dk .o2hd .h3seg{background:#2C2C2E;color:#fff}body.dk .o2ar{color:#fff;border-color:#2C2C2E}
`;document.head.appendChild(st)})();

/* ===================== Body close-ups (thyroid, ears, skin…): callouts on a point of the part itself ===================== */
Object.assign(O2D,{'Isthmus':'The thin bridge of thyroid tissue that joins the two lobes across the front of the windpipe.','Windpipe':'The trachea carries air from the voice box down to the lungs.','Red cells':'Carry oxygen on haemoglobin. Haemoglobin and RBC count measure them.','White cells':'Fight infection. Your WBC count measures them.','Platelets':'Tiny cell pieces that plug cuts and start clotting. Your platelet count measures them.','Right breast':'Milk-making glands and fat, held to the chest wall by fine ligaments. Check monthly for lumps or changes.','Left breast':'Milk-making glands and fat, held to the chest wall by fine ligaments. Check monthly for lumps or changes.','Bladder':'A muscular bag that stores urine until you pass it.','Womb':'The uterus, where a baby grows; it sits just behind the bladder.'});
Object.assign(O2D,{'Thyroid gland':'Two lobes around the windpipe below the voice box. It makes the hormones that set how fast the body uses energy.','Voice box':'The larynx, with the vocal cords inside; the thyroid cartilage is its front (the Adam’s apple).','Right ear':'The outer ear collects sound; the middle and inner ear turn it into nerve signals.','Left ear':'The outer ear collects sound; the middle and inner ear turn it into nerve signals.','Inner ear':'The cochlea turns sound into nerve signals; the canals beside it sense balance.','Molars':'Back teeth with broad tops that grind food.','Front teeth':'Incisors cut food.','Lower jaw':'The mandible holds the lower teeth.','Spine':'Thirty-three vertebrae protect the spinal cord and carry the body’s weight.','Hip':'The hip bone forms the socket where the thigh bone turns.','Right eye':'Focuses light onto the retina and sends what you see to the brain.','Left eye':'Focuses light onto the retina and sends what you see to the brain.'});
/* parts partly covered from the front (the voice box sits behind the thyroid's upper lobes): aim higher on the part */
const O2BIAS={'Voice box':.32};
function o2BodyPt(re,bias=0){let best=null,bz=-Infinity,near=null,nd=Infinity;const p=new THREE.Vector3(),b=new THREE.Box3(),hits=[];
 for(const l of [0,1,2,3,4,5]){const m=LAY[l];if(!m||!m.userData.ranges)continue;const ix=m.geometry.index.array,pa=m.geometry.attributes.position;for(const rg of m.userData.ranges){if(!re.test(SET.names[rg[2]]))continue;const s=ix.subarray(rg[5],rg[5]+rg[6]);hits.push([pa,s]);for(let i=0;i<s.length;i+=3){o2Denorm(pa,s[i],p);b.expandByPoint(p)}}}
 if(b.isEmpty())return null;const c=b.getCenter(new THREE.Vector3()),sz=b.getSize(new THREE.Vector3()),r=Math.max(1e-5,Math.min(sz.x,sz.y)*.3);c.y+=sz.y*bias;
 for(const [pa,s] of hits)for(let i=0;i<s.length;i++){o2Denorm(pa,s[i],p);const dx=p.x-c.x,dy=p.y-c.y,d2=dx*dx+dy*dy;if(d2<r*r&&p.z>bz){bz=p.z;best=p.clone()}const d3=d2+(p.z-c.z)**2;if(d3<nd){nd=d3;near=p.clone()}}return best||near}
const _partView=partView;partView=function(o){const r=_partView(o);if(r){tags([]);const L=PVL||(PARTS[o]&&PARTS[o].labels||[]).map(([n,re])=>({lab:n,re}));PVL=null;O2.pv=L.map(x=>x.p?{lab:x.lab,p:x.p}:{lab:x.lab,p:o2BodyPt(x.re,O2BIAS[x.lab]||0)}).filter(x=>x.p)}return r};
const _partOff=partOff;partOff=function(){_partOff();if(O2.pv){O2.pv=null;o2Call(null)}};
(function o2PvLoop(){if(O2.pv&&!OG&&!H3)o2Call(O2.pv.map((g,i)=>{O2Q.copy(typeof g.p==='function'?g.p():g.p);body.localToWorld(O2Q);const p=o2Scr(O2Q);return{k:'p'+i,x:p.x,y:p.y,ok:p.ok,name:g.lab,def:O2D[g.lab]||'',sel:false,on:()=>{}}}));requestAnimationFrame(o2PvLoop)})();

/* ===================== Lymphatic system (19 Nov): nodes, spleen, thymus and tonsils on the body (Z-Anatomy, CC BY-SA 4.0);
   inside a lymph node (HuBMAP CCF reference organ, NIH, CC BY 4.0) ===================== */
O2A.lnode='/a/lymph-node.c4c3ad6c.glb';O2NEW.add('lnode');
Object.assign(ORGI,{lymph:['Lymphatic system','Lymph nodes, spleen, thymus and tonsils','Lymph nodes filter the fluid that drains from the tissues and are where immune cells meet germs.'],lnode:['Lymph node','Inside a lymph node','A bean-shaped filter: lymph flows in, past immune cells, and out again.']});
OGL.lnode=[[/capsule/i,'Capsule'],[/follicle/i,'Follicles'],[/paracortex/i,'Paracortex'],[/medulla/i,'Medulla'],[/afferent/i,'Lymph in'],[/efferent/i,'Lymph out'],[/blood_vasc/i,'Blood vessels']];
Object.assign(O2D,{'Capsule':'A tough outer coat of connective tissue.','Follicles':'Clusters of B cells in the outer cortex; they swell when fighting an infection.','Paracortex':'The T-cell zone, between the follicles and the medulla.','Medulla':'The inner part, with cords of plasma cells and channels that collect lymph.','Lymph in':'Afferent lymphatic vessels bring lymph from the tissues.','Lymph out':'The efferent vessel carries filtered lymph on toward the blood.','Blood vessels':'Arteries and veins enter at the hilum to feed the node.',
 'Neck nodes':'Cervical nodes drain the head and neck; often swollen with a sore throat.','Armpit nodes':'Axillary nodes drain the arm and breast.','Groin nodes':'Inguinal nodes drain the leg and lower belly wall.','Gut nodes':'Mesenteric nodes drain the intestines.','Thymus':'Where T cells mature; large in children, it shrinks after puberty.','Spleen':'Filters old red blood cells and helps fight infection.','Tonsils':'Lymphoid tissue at the back of the throat that meets germs first.'});
const O2LC={lnode:{capsule:[.93,.88,.82,.18],follicle:[.78,.62,.66],paracortex:[.88,.78,.70],medulla:[.84,.56,.52],afferent:[.96,.92,.74,.55],efferent:[.96,.92,.74,.55],blood:[.75,.12,.14]}};
const _o2Nat=o2Nat;o2Nat=async function(root,key){await _o2Nat(root,key);const C=O2LC[key];if(!C)return;root.traverse(n=>{if(!n.isMesh)return;const nm=(o2Name(n)||n.name||'').toLowerCase();const k=Object.keys(C).find(k=>nm.includes(k));if(!k)return;const c=C[k],m=n.material;m.vertexColors=false;m.map=null;m.color.setRGB(c[0],c[1],c[2]);if(c[3]!=null){m.transparent=true;m.opacity=c[3];m.depthWrite=false}m.needsUpdate=true})};
const O2LY=[[/\bnodes?\b/i,0xC9A27E],[/^spleen\b/i,0x7A2A3A],[/thymus|palatine tonsil/i,0xD9B49A]];
function o2LayMesh(l,re,col){const m=LAY[l];if(!m||!m.userData.ranges)return null;const ia=[];for(const rg of m.userData.ranges){const nm=SET.names[rg[2]];if(re.test(nm)&&!/cerebell/i.test(nm)){const s=m.geometry.index.array.subarray(rg[5],rg[5]+rg[6]);for(const v of s)ia.push(v)}}if(!ia.length)return null;
 const g=new THREE.BufferGeometry();g.setAttribute('position',m.geometry.attributes.position);if(m.geometry.attributes.normal)g.setAttribute('normal',m.geometry.attributes.normal);g.setIndex(new THREE.BufferAttribute(new Uint32Array(ia),1));
 const h=new THREE.Mesh(g,new THREE.MeshPhysicalMaterial({color:col,roughness:.45,clearcoat:.35,clearcoatRoughness:.3,sheen:new THREE.Color(0x5a1c14)}));h.renderOrder=8;h.frustumCulled=false;body.add(h);if(O2.env){h.material.envMap=O2.env;h.material.envMapIntensity=.5}return h}
function o2Lymph(){shape();if(VIEW)VIEW.o='lymph';head(who()+' · LYMPHATIC SYSTEM','Lymph nodes, spleen, thymus and tonsils','');document.body.classList.add('orgv','o2lab');orgBar('Lymphatic system','lymph');setLayer('organs');o2Env();
 for(const l in LAY){const m=LAY[l];if(+l===0){m.visible=true;m.material.opacity=.1}else if(+l===3||+l===2){m.visible=true;m.material.transparent=true;m.material.opacity=+l===3?.07:.08;m.material.depthWrite=false}else m.visible=false}
 O2.nv=O2LY.map(([re,c])=>o2LayMesh(3,re,c)).filter(Boolean);rot.y=0;rot.x=0;goal.y=0;goal.x=0;body.position.x=0;CAM(HOME0.z*1.2,HOME0.y+.25);
 let b=$('#o2bar');if(!b){b=document.createElement('div');b.id='o2bar';document.body.appendChild(b)}b.hidden=false;b.innerHTML=o2Seg([['','Whole body'],['in','Inside a node']],'','o2LymphMode');
 const nn=(LAY[3]&&LAY[3].userData.ranges||[]).filter(rg=>/\bnodes?\b/i.test(SET.names[rg[2]])).length,wbc=o2Find(/^wbc|white (blood )?cell|total leu/i),ly=o2Find(/lymphocyte/i),crp=o2Find(/^crp|c.?reactive/i);
 sheet(`<div class="o2stat"><div><b>~600</b><small>lymph nodes in the body</small></div><div><b>${nn||'–'}</b><small>node groups shown</small></div><div><b>1 in 4</b><small>white cells are lymphocytes</small></div></div>
  <p class="cd" style="color:#1D1D1F">Lymph drains from the tissues through the nodes, where immune cells check it for germs, and returns to the blood near the heart. Swollen nodes usually mean the body is fighting an infection nearby.</p>
  <div class="o2box">${o2Row('White blood cells',wbc)}${o2Row('Lymphocytes',ly)}${o2Row('CRP (inflammation)',crp)}</div>
  <button class="btn pri" style="width:100%;margin-top:12px" onclick="o2LymphMode('in')">Inside a lymph node</button>`);
 let el=$('#o2tags');if(!el){el=document.createElement('div');el.id='o2tags';document.body.appendChild(el)}
 O2.ntags=[[/cervical nodes|jugulodigastric/i,'Neck nodes'],[/axillary nodes/i,'Armpit nodes'],[/inguinal nodes/i,'Groin nodes'],[/mesenteric nodes/i,'Gut nodes'],[/thymus/i,'Thymus'],[/^spleen$/i,'Spleen'],[/palatine tonsil/i,'Tonsils']].map(([re,lab])=>({lab,p:o2BodyPt(re)})).filter(t=>t.p)}
function o2LymphMode(k){if(k==='in')return vgo({k:'organ',o:'lnode'},'Lymphatic system')}
const _vOrgan3=vOrgan;vOrgan=async function(o){if(o==='lymph'){o2Clean();return o2Lymph()}return _vOrgan3(o)};
O2EX.splice(O2EX.findIndex(x=>x[0]==='nerves')+1,0,['lymph','Lymphatic system']);
const _o2Spec=o2Spec;o2Spec=function(d){const s=String(d.specialty||'').toLowerCase();if(/haemat|hemat|oncol|immunol/.test(s))return'organ:lymph';return _o2Spec(d)};
/* files without part names in their metadata (HuBMAP): name the parts from their node names */
const _ogGet=ogGet;ogGet=async function(o){const g=await _ogGet(o);if(g&&!g.userData.o2named){g.userData.o2named=1;g.scene.traverse(n=>{if(n.name&&!(n.userData&&n.userData.display_name)&&n.children.some(c=>c.isMesh)){
 const nm=n.name.replace(/^(Yao|VH|NIH|SBU|Allen)_([MF]_)?/i,'').replace(/_/g,' ').replace(/\s+/g,' ').trim();n.userData.display_name=nm.charAt(0).toUpperCase()+nm.slice(1);
 n.userData.anatomy_kind=/vessel|vascul|efferent|afferent/i.test(nm)?'Vessel':'Organ'}})}return g};
/* the whole lymphatic system fills the screen above the sheet */
const _o2Lymph=o2Lymph;o2Lymph=function(){_o2Lymph();const h=O2.nv&&O2.nv[0];if(h)setTimeout(()=>{if(O2.nv&&O2.nv[0]===h)o2FrameMesh(h,1.04)},60)};

/* ===================== Atlas upgrade, stage 2 (23 Nov 2026): ear, nose and throat; the linings of brain and lungs;
   the skin block; and "go deeper" to air sacs and the kidney filter. Real atlas data where it exists (Z-Anatomy, CC BY-SA 4.0;
   HuBMAP Human Reference Atlas incl. Allen brain regions, CC BY 4.0); the rest built to published measurements, for
   research-team review. Models: tools/scene_to_glb.py. ===================== */
const O2XF={"alveoli":"/a/x-alveoli.a8f39e1b.glb","ear":"/a/x-ear.a8a04bdd.glb","nephron":"/a/x-nephron.8f73f2fa.glb","throat":"/a/x-throat.cac5c5f4.glb","skin":"/a/x-skin.3fa98763.glb","pleura":"/a/x-pleura.4a66f020.glb","meninges":"/a/x-meninges.e527c766.glb","nose":"/a/x-nose.08369933.glb"};
const O2SET={ent:[['ear','Ear'],['nose','Nose & sinuses'],['throat','Throat']],lining:[['meninges','Brain'],['pleura','Lungs']],skinl:[['skin','Skin layers']],deeper:[['alveoli','Air sacs'],['nephron','Kidney filter']]};
O2.sub=O2.sub||{};for(const o in O2SET){O2NEW.add(o);O2TINT[o]=[1,1,1]}
const o2SubOf=o=>O2.sub[o]||O2SET[o][0][0];
Object.assign(ORGI,{ent:['Ear, nose and throat','Ear, nose and throat','The parts a mirror cannot show: hearing and balance, the sinuses, and the voice box.'],
 lining:['Linings','Linings','Thin layers that wrap the brain and the lungs. Many conditions are named by the layer they affect.'],
 skinl:['Skin','Skin layers','A block of skin 4 mm wide, with its layers at true thickness.'],
 deeper:['Go deeper','Go deeper','Down to the units that do the work: air sacs in the lungs, filters in the kidneys.']});
const O2XL={ear:[[/^Ear canal$/,'Ear canal'],[/^Eardrum$/,'Eardrum'],[/^Hammer/,'Ossicles'],[/^Cochlea$/,'Cochlea'],[/^Semicircular canals$/,'Balance canals'],[/^Hearing and balance nerve$/,'Hearing nerve'],[/^Eustachian tube$/,'Eustachian tube']],
 nose:[[/^Frontal sinus$/,'Frontal sinus'],[/^Ethmoid sinus$/,'Ethmoid sinus'],[/^Sphenoid sinus$/,'Sphenoid sinus'],[/^Maxillary sinus$/,'Maxillary sinus'],[/^Turbinates$/,'Turbinates'],[/^Nasal septum/,'Septum']],
 throat:[[/^Vocal cords$/,'Vocal cords'],[/^False vocal cords$/,'False vocal cords'],[/^Epiglottis$/,'Epiglottis'],[/^Below the vocal cords$/,'Windpipe']],
 meninges:[[/^Dura mater$/,'Dura mater'],[/^Arachnoid mater$/,'Arachnoid'],[/^Brain surface/,'Pia mater'],[/^Cortical veins$/,'Cortical veins'],[/^Middle meningeal artery$/,'Meningeal artery']],
 pleura:[[/^Pleura$/,'Pleura'],[/^Right lung, upper lobe$/,'Upper lobe'],[/^Right lung, middle lobe$/,'Middle lobe'],[/^Left lung, lower lobe$/,'Lower lobe'],[/^Windpipe$/,'Windpipe']],
 skin:[[/^Epidermis$/,'Epidermis'],[/^Dermis$/,'Dermis'],[/^Fat layer$/,'Fat layer'],[/^Hair follicle$/,'Hair follicle'],[/^Oil gland$/,'Oil gland'],[/^Sweat gland$/,'Sweat gland'],[/^Pressure sensor$/,'Pressure sensor'],[/^Touch sensor$/,'Touch sensor']],
 alveoli:[[/^Respiratory bronchiole$/,'Smallest airway'],[/^Alveolar duct$/,'Alveolar duct'],[/^Air sacs$/,'Air sacs'],[/^Inside an air sac$/,'Capillaries'],[/^Pulmonary arteriole$/,'Arteriole'],[/^Pulmonary venule$/,'Venule']],
 nephron:[[/^Glomerulus$/,'Glomerulus'],[/^Bowman capsule$/,'Bowman capsule'],[/^Proximal tubule$/,'Proximal tubule'],[/^Loop of Henle$/,'Loop of Henle'],[/^Thick ascending limb$/,'Ascending limb'],[/^Distal tubule$/,'Distal tubule'],[/^Collecting duct$/,'Collecting duct']]};
Object.assign(O2D,{
 'Ear canal':'Meatus acusticus externus. About 25 mm long and S-shaped; wax glands line its outer part.','Eardrum':'Membrana tympanica. About 9 mm across; sound makes it vibrate.',
 'Ossicles':'Malleus, incus and stapes: the three smallest bones in the body carry the eardrum\'s vibration to the inner ear. The stirrup is about 3 mm long.',
 'Cochlea':'Cochlea. A snail-shaped tube of 2¾ turns where sound becomes nerve signals; high notes are sensed at the base, low notes at the tip.',
 'Balance canals':'Canales semicirculares. Three fluid-filled rings at right angles sense turning, nodding and tilting.','Hearing nerve':'N. vestibulocochlearis (VIII). Carries hearing and balance to the brainstem.',
 'Eustachian tube':'Tuba auditiva. Links the middle ear to the back of the nose and evens out pressure, which is why ears "pop".',
 'Frontal sinus':'Sinus frontalis. An air space in the forehead bone behind the eyebrows.','Ethmoid sinus':'Cellulae ethmoidales. A honeycomb of small air cells between the eyes.',
 'Sphenoid sinus':'Sinus sphenoidalis. Deep in the skull, behind the nose, just under the pituitary gland.','Maxillary sinus':'Sinus maxillaris. The largest sinus, in each cheekbone; it drains high up, so it clears slowly.',
 'Turbinates':'Conchae nasales. Curled shelves that warm, wet and filter the air you breathe.','Septum':'Septum nasi. The wall of cartilage and bone that divides the nose; a bent septum can block one side.',
 'Vocal cords':'Plicae vocales. Two folds that part to breathe and close and vibrate to make your voice.','False vocal cords':'Plicae vestibulares. Folds above the vocal cords that protect the airway when you swallow.',
 'Epiglottis':'Epiglottis. A leaf of cartilage that folds back over the voice box when you swallow.',
 'Dura mater':'Dura mater. The tough outer layer, fixed to the inside of the skull. A bleed under it is a subdural haematoma.',
 'Arachnoid':'Arachnoid mater. A thin, web-like layer. Below it, brain fluid cushions the brain; a bleed there is a subarachnoid haemorrhage.',
 'Pia mater':'Pia mater. A delicate layer that follows every fold of the brain and carries its surface vessels.',
 'Cortical veins':'Veins on the brain surface drain blood into the large sinuses in the dura.','Meningeal artery':'A. meningea media. Runs on the dura under the temple; a blow there can tear it.',
 'Pleura':'Pleura. Two thin layers with a film of fluid between them let the lungs glide as you breathe. Fluid there is a pleural effusion; air there is a collapsed lung.',
 'Upper lobe':'The right lung has three lobes and the left has two; each lobe divides into segments with their own airway.','Middle lobe':'Only the right lung has a middle lobe.','Lower lobe':'The largest lobe, resting on the diaphragm.',
 'Epidermis':'Epidermis. About 0.1 mm thick; new cells form at its base and take about a month to reach the surface.','Dermis':'Dermis. Collagen and elastic fibres give skin its strength and stretch; it carries the vessels, nerves and glands.',
 'Fat layer':'Tela subcutanea. Fat lobules that insulate, cushion and store energy.','Hair follicle':'Folliculus pili. Grows a hair from the bulb at its base.',
 'Oil gland':'Glandula sebacea. Keeps hair and skin supple; when it blocks, a spot forms.','Sweat gland':'Glandula sudorifera eccrina. A coiled gland deep in the dermis; its duct spirals up to a pore.',
 'Pressure sensor':'Corpusculum lamellosum (Pacinian). Onion-like layers sense pressure and vibration.','Touch sensor':'Corpusculum tactus (Meissner). Sits in the ridges just under the epidermis and senses light touch.',
 'Smallest airway':'Bronchiolus respiratorius. The last airway, already with a few air sacs on its wall.','Alveolar duct':'Ductus alveolaris. Leads air into clusters of air sacs.',
 'Air sacs':'Alveoli. About 480 million, each about 0.2 mm across. Oxygen crosses a wall under 1 micrometre thick into the blood.',
 'Capillaries':'A mesh of capillaries wraps every air sac; red cells pass through in under a second.','Arteriole':'Arteriola pulmonalis. Brings oxygen-poor blood to the air sacs.','Venule':'Venula pulmonalis. Carries oxygen-rich blood back toward the heart.',
 'Glomerulus':'Glomerulus. A knot of capillaries that filters about 180 litres of fluid a day from the blood.','Bowman capsule':'Capsula glomeruli. The cup that catches the filtered fluid.',
 'Proximal tubule':'Tubulus contortus proximalis. Takes back most of the water, salt, sugar and protein building blocks.','Loop of Henle':'Ansa nephroni. Dips into the medulla and lets the kidney make concentrated urine.',
 'Ascending limb':'The thick ascending limb pumps out salt; many water tablets act here.','Distal tubule':'Tubulus contortus distalis. Fine-tunes salt and acid balance.','Collecting duct':'Tubulus renalis colligens. Hormones set how much water it keeps.'});
const _ogfX=ogf;ogf=function(o){if(O2SET[o])return O2XF[o2SubOf(o)];return _ogfX(o)};
const _vOrganX=vOrgan;vOrgan=async function(o){if(O2SET[o])OGL[o]=O2XL[o2SubOf(o)];return _vOrganX(o)};
/* these close-ups have no test results of their own: the sheet names the part shown and says how big it really is */
const O2SUBT={alveoli:['Air sacs','About 480 million air sacs pass oxygen into the blood across a wall thinner than 1 micrometre. One cluster is shown, many hundred times larger than life.'],
 nephron:['Kidney filter (nephron)','Each kidney has about a million of these filters. One is shown, much larger than life: the filter knot, then the tubes that turn the filtered fluid into urine.'],
 ear:['Ear','Outer, middle and inner ear. Sound moves the eardrum and three tiny bones, and the cochlea turns it into nerve signals.'],
 nose:['Nose and sinuses','The nasal cavity and the four pairs of sinuses, the air spaces in the bones of the face.'],
 throat:['Throat','The voice box from inside: the vocal cords, the epiglottis and the start of the windpipe.'],
 meninges:['Linings of the brain','Three layers wrap the brain: the tough dura, the web-like arachnoid and the thin pia that follows every fold.'],
 pleura:['Linings of the lungs','Two thin layers wrap each lung and line the chest wall, with a film of fluid between them so the lungs can glide.'],
 skin:['Skin layers','A block of skin 4 mm wide, with its layers at true thickness.']};
function o2NoLab(o){return O2SET[o]?O2SUBT[o2SubOf(o)]||null:null}
function o2Sub(k){const o=OG&&OG.o;if(!o||!O2SET[o])return;O2.sub[o]=k;vshow(VIEW,true)}
const _o2BarX=o2Bar;o2Bar=function(o){if(!O2SET[o]||O2SET[o].length<2)return _o2BarX(o);let b=$('#o2bar');if(!b){b=document.createElement('div');b.id='o2bar';document.body.appendChild(b)}b.innerHTML=o2Seg(O2SET[o],o2SubOf(o),'o2Sub');b.hidden=false};
O2EX.splice(O2EX.findIndex(x=>x[0]==='bones')+1,0,['ent','Ear, nose and throat'],['skinl','Skin layers'],['lining','Linings']);O2EX.push(['deeper','Go deeper'],['cut','Cross-section'],['measure','Measure']);
/* life size in the room, only where the browser supports AR (arStart in body.html) */
if(typeof xrOk==='function')xrOk().then(ok=>{if(ok&&!O2EX.some(x=>x[0]==='ar'))O2EX.push(['ar','See it life size'])});

/* ===================== Science panel (23 Nov 2026): cells and markers from the HuBMAP Human Reference Atlas ASCT+B tables
   (v2.0, CC BY 4.0), with authors, version and DOI; per structure on tap. tools/make_asctb.py ===================== */
let O2CT=null;const o2Cells=()=>O2CT||(O2CT=fetch('/a/asctb.f43c2901.json').then(r=>r.json()).catch(()=>null));
const O2CTK={kidney:'kidney',liver:'liver',lung:'lung',pancreas:'pancreas',brain:'brain',lnode:'lnode',prostate:'prostate',skinl:'skinl'};
function o2CtKey(o){if(o==='deeper')return o2SubOf('deeper')==='nephron'?'kidney':'lung';if(o==='lining')return o2SubOf('lining')==='pleura'?'lung':'brain';if(o==='bones')return O2.bone==='knee'?'knee':null;return O2CTK[o]||null}
const o2W=s=>String(s||'').toLowerCase().replace(/\(.*?\)/g,' ').replace(/\b(left|right|the|of|and|reconstructed|surface)\b/g,' ').replace(/[^a-z ]/g,' ').split(/\s+/).filter(w=>w.length>2);
function o2Match(T,name){const w=o2W(name);if(!w.length)return null;let best=null,bs=0;for(const s of T.structures){const a=o2W(s.as);const hit=w.filter(x=>a.some(y=>y.startsWith(x.slice(0,5))||x.startsWith(y.slice(0,5)))).length/w.length;if(hit>bs){bs=hit;best=s}}return bs>=.67?best:null}
function o2CellList(cells,n=6){return`<ul class="o2cl">${cells.slice(0,n).map(c=>`<li><b>${esc(c.ct.replace(/^./,x=>x.toUpperCase()))}</b><span class="o2id">${esc(c.id||'')}</span>${c.mk.length?`<span class="o2mk">${c.mk.map(m=>`<i>${esc(m)}</i>`).join('')}</span>`:''}</li>`).join('')}</ul>`}
function o2Cite(T){return`<p class="o2src">${esc(T.title||'HuBMAP ASCT+B table')}${T.version?' · '+esc(T.version):''}${T.date?' · '+esc(T.date):''}. ${esc((T.authors||'').split(';').slice(0,3).join(',')+((T.authors||'').split(';').length>3?' et al.':''))}${T.doi?` · <a href="${esc(T.doi)}" target="_blank" rel="noopener">${esc(T.doi.replace(/^https?:\/\//,''))}</a>`:''}. HuBMAP Human Reference Atlas, CC BY 4.0.</p>`}
async function o2CellsPanel(o){const k=o2CtKey(o),D=await o2Cells();if(!D||!k||!D.organs[k])return;const T=D.organs[k];document.body.classList.add('o2cellson');
 sheet(`<div class="row" style="justify-content:space-between"><button class="lk" onclick="vshow(VIEW,true)">‹ ${esc((ORGI[o]||[o,o])[1])}</button><button class="x" onclick="vshow(VIEW,true)" aria-label="Close">✕</button></div>
 <div class="cn" style="font-size:22px;margin-top:4px">Cells and markers</div><p class="cd">${T.structures.length} structures and the cell types found in each, with the genes or proteins that identify them.</p>
 <div class="o2cs">${T.structures.map(s=>`<details><summary><b>${esc(s.as.replace(/^./,x=>x.toUpperCase()))}</b><span>${s.cells.length} cell type${s.cells.length>1?'s':''} · ${esc(s.id)}</span></summary>${o2CellList(s.cells,40)}</details>`).join('')}</div>${o2Cite(T)}`)}
const _o2SheetC=o2Sheet;o2Sheet=function(o){_o2SheetC(o);const k=o2CtKey(o);if(!k)return;o2Cells().then(D=>{if(!D||!D.organs[k]||!OG||OG.o!==o)return;const card=$('#card');if(!card||card.querySelector('.o2cbtn'))return;const T=D.organs[k],n=T.structures.reduce((a,s)=>a+s.cells.length,0);
 card.insertAdjacentHTML('beforeend',`<button class="btn sec o2cbtn" style="width:100%;margin-top:10px" onclick="o2CellsPanel('${o}')">Cells and markers · ${n} entries</button>`)})};
const _ogPickC=ogPick;ogPick=function(n){_ogPickC(n);if(!OG||!n)return;const k=o2CtKey(OG.o);if(!k)return;o2Cells().then(D=>{if(!D||!D.organs[k]||!OG||OG.sel!==n)return;const u=n.userData||{},lab=(OG.labels.find(l=>l.n===n)||{}).lab;const s=o2Match(D.organs[k],lab||u.display_name)||o2Match(D.organs[k],u.display_name);if(!s)return;
 const card=$('#card');if(!card||card.querySelector('.o2cbox'))return;card.insertAdjacentHTML('beforeend',`<div class="o2box o2cbox"><div class="ove" style="color:var(--ink3)">CELLS HERE · ${esc(s.as.toUpperCase())}</div>${o2CellList(s.cells,5)}${o2Cite(D.organs[k])}</div>`)})};
(()=>{const st=document.createElement('style');st.textContent=`.o2cl{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-direction:column;gap:8px}.o2cl li{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline}.o2cl b{font-size:14px;font-weight:600}.o2id{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink3)}.o2mk{display:flex;flex-wrap:wrap;gap:4px;width:100%}.o2mk i{font:500 12px ui-monospace,SFMono-Regular,Menlo,monospace;font-style:normal;padding:2px 8px;border-radius:10px;background:rgba(94,92,230,.14);color:#BFBDFF}.o2src{font-size:12px;line-height:16px;color:var(--ink3);margin:10px 0 0}.o2src a{color:#64D2FF}.o2cs{display:flex;flex-direction:column;gap:6px;margin-top:8px;max-height:52vh;overflow-y:auto}.o2cs details{border-radius:14px;background:rgba(255,255,255,.06);padding:10px 12px}.o2cs summary{display:flex;flex-direction:column;gap:2px;cursor:pointer;list-style:none}.o2cs summary span{font-size:12px;color:var(--ink3)}`;document.head.appendChild(st)})();

/* ===================== Research-team review (23 Nov 2026): close-ups with parts we built ourselves say whether the
   research team has checked them (Admin → Library → Anatomy review, api/anatomy_review.py). The line is placed at
   once and only its words change when the answer arrives, so the sheet never jumps. ===================== */
let O2RV=null;const o2Rev=()=>O2RV||(O2RV=fetch('/api/v1/anatomy/review').then(r=>r.ok?r.json():null).catch(()=>null));
function o2RvId(o){if(O2SET[o])return'x-'+o2SubOf(o);if(o==='bones'&&O2JOINT[O2.bone])return'joints';return null}
const _o2SheetR=o2Sheet;o2Sheet=function(o){_o2SheetR(o);const id=o2RvId(o),card=$('#card');if(!id||!card)return;
 card.insertAdjacentHTML('beforeend','<p class="o2rv"><i></i><span>Being checked by our research team</span></p>');const p=card.lastElementChild;
 o2Rev().then(D=>{const s=D&&D.items&&D.items[id];if(!p.isConnected||!s||s.state!=='approved')return;p.classList.add('ok');
  p.lastElementChild.textContent='Checked by our research team'+(s.at?' · '+new Date(s.at*1000).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}):'')})};
(()=>{const st=document.createElement('style');st.textContent=`.o2rv{display:flex;align-items:center;gap:7px;font-size:12px;line-height:16px;color:var(--ink3);margin:10px 0 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.o2rv i{flex:none;width:7px;height:7px;border-radius:50%;background:#FF9F0A}.o2rv.ok i{background:#30D158}.o2rv span{overflow:hidden;text-overflow:ellipsis}`;document.head.appendChild(st)})();
/* while the cells panel is open, the numbered labels step aside so nothing sits over the model; any move away brings them back */
const _vshowC=vshow;vshow=function(...a){document.body.classList.remove('o2cellson');return _vshowC.apply(this,a)};
(()=>{const st=document.createElement('style');st.textContent='body.o2cellson #h3tags,body.o2cellson #ogpin,body.o2cellson #o2leg{display:none!important}';document.head.appendChild(st)})();
