// ===================== Anatomy Lab tools: layer opacity, hide/unhide, pins, structure tree =====================
(()=>{
const LCOL=['#e8c9b4','#c8553f','#e6dac0','#d9a08a','#c0392b','#e2bf55'];
A.op=A.op||{};const OM={};
function opMat(l){const base=l===0?matSkin:mat;let m=OM[l];if(!m){m=base.clone();nxShade(m);OM[l]=m}m.transparent=true;m.opacity=A.op[l];m.depthWrite=A.op[l]>.9;m.clippingPlanes=base.clippingPlanes;m.needsUpdate=true;return m}
function applyOp(){if(A.focus||A.holo)return;LAYS.forEach(L=>{const o=A.op[L.l];if(o!==undefined&&o<.995&&L.mesh.visible){L.mesh.material=opMat(L.l);L.mesh.renderOrder=L.l===0?5:2+L.l}})}
const _av=A.applyVis;A.applyVis=function(){_av.apply(this,arguments);applyOp()};
// ---- hide / unhide individual structures ----
function reindex(L){let n=0;const keep=[];PT.forEach((p,i)=>{if(p.L===L&&!NXH.has(i)){keep.push(p);n+=p.i}});if(n===L.idx.length&&!NXH.size){L.mesh.geometry.setIndex(new THREE.BufferAttribute(L.idx,1));return}const a=new Uint32Array(n);let o=0;keep.sort((x,y)=>x.io-y.io).forEach(p=>{a.set(L.idx.subarray(p.io,p.io+p.i),o);o+=p.i});L.mesh.geometry.setIndex(new THREE.BufferAttribute(a,1))}
const HIS=[],RED=[];const rec=a=>{HIS.push(a);RED.length=0;syncHist()};
const NX=window.NX={hide(i,nohist){if(i<0)return;if(!nohist)rec({t:'hide',ids:[i]});NXH.add(i);if(sel===i)choose(-1);reindex(PT[i].L);toast('Hidden: '+PT[i].name+' · Ctrl/⌘-click hides, “Unhide all” restores');sync()},
 show(i,nohist){if(!nohist)rec({t:'show',ids:[i]});NXH.delete(i);reindex(PT[i].L);sync()},
 unhideAll(nohist){if(!NXH.size)return;if(!nohist)rec({t:'show',ids:[...NXH]});const Ls=new Set([...NXH].map(i=>PT[i].L));NXH.clear();Ls.forEach(reindex);sync()},
 undo(){const a=HIS.pop();if(!a){toast('Nothing to undo');return}RED.push(a);apply(a,true);syncHist()},redo(){const a=RED.pop();if(!a)return;HIS.push(a);apply(a,false);syncHist()},
 pin(i){if(i<0)return;const k=NXP.indexOf(i);if(k>=0)NXP.splice(k,1);else NXP.push(i);computeLabels();sync()},
 clearPins(){NXP.length=0;computeLabels();sync()},find:q=>PT.findIndex(p=>p.s.includes(q)),cam:()=>[tx,ty,zoom,C.position.z,A.auto],view:(x,y,z,ry,rx)=>{A.auto=false;tx=x;ty=y;zoom=z;goalRY=null;goalRX=rx||0;body.rotation.set(rx||0,ry,0);C.position.set(x,y+.2,z);A.showDots=false},count:re=>PT.filter(p=>re.test(p.s)).length,sc:()=>Sc,ren:()=>R,dbg:()=>{const L=LAYS.find(x=>x.l===2);const g=L.mesh.geometry;let s=0;const a=g.attributes.ao.array;for(let i=0;i<a.length;i+=97)s+=a[i];return [L.mesh.material===mat,!!g.attributes.ao,s/(a.length/97),g.attributes.kind.array[5],R.info.programs.map(p=>p.name+':'+(p.cacheKey||'').slice(0,0)).join(','),R.getContext().getProgramInfoLog?1:0]}};
function apply(a,inv){const hide=(a.t==='hide')!==inv,Ls=new Set();a.ids.forEach(i=>{hide?NXH.add(i):NXH.delete(i);Ls.add(PT[i].L)});if(hide&&a.ids.includes(sel))choose(-1);Ls.forEach(reindex);sync()}
function syncHist(){const u=$('#nxUndo'),r=$('#nxRedo');if(u)u.disabled=!HIS.length;if(r)r.disabled=!RED.length}
function sync(){const h=$('#nxHid');if(h)h.textContent=NXH.size;const p=$('#nxPin');if(p)p.textContent=NXP.length;$$('[data-nxhide]').forEach(b=>{const i=+b.dataset.nxhide;b.classList.toggle('off',NXH.has(i))});const ip=$('#ipin');if(ip&&infoSel>=0)ip.textContent=NXP.includes(infoSel)?'Unpin':'Pin label'}
// info card: Pin + Hide buttons
const ib=$('#info .ib');if(ib){ib.insertAdjacentHTML('beforeend','<button id="ipin">Pin label</button><button id="ihide">Hide</button>');$('#ipin').onclick=()=>{NX.pin(infoSel)};$('#ihide').onclick=()=>{const i=infoSel;NX.hide(i)}}
new MutationObserver(sync).observe($('#info'),{attributes:true,attributeFilter:['hidden']});
// reset when the body is rebuilt (sex switch)
const _cb=clearBody;clearBody=function(){NXH.clear();NXP.length=0;HIS.length=RED.length=0;setTimeout(()=>{syncHist();if(A.boneCol)boneColors(true)},0);return _cb.apply(this,arguments)};
// ---- layer panel with opacity sliders ----
layerBoxes=()=>`<div class="nxl">${LN.map((n,l)=>{const has=A.has(l),cnt=has?PT.filter(p=>p.l===l).length:0,op=Math.round((A.op[l]??1)*100);return `<div class="nxr ${has?'':'na'}"><label><input type="checkbox" data-layer="${l}" ${A.vis[l]?'checked':''} ${has&&!A.focus?'':'disabled'}><i style="background:${LCOL[l]}"></i><b>${n}</b><small>${has?cnt.toLocaleString()+' parts':'n/a'}</small></label><input type="range" min="5" max="100" value="${op}" data-lop="${l}" aria-label="${n} opacity" ${has&&!A.focus?'':'disabled'}><em>${op}%</em></div>`}).join('')}</div>
<div class="nxbar"><button class="btn s sm" data-nx="unhide">Unhide all (<span id="nxHid">${NXH.size}</span>)</button><button class="btn s sm" data-nx="unpin">Clear pins (<span id="nxPin">${NXP.length}</span>)</button><small class="mute">Ctrl/⌘-click hides a structure · Shift-click pins its label</small></div>`;
document.addEventListener('input',e=>{const r=e.target.closest('[data-lop]');if(!r)return;const l=+r.dataset.lop;A.op[l]=r.value/100;r.nextElementSibling.textContent=r.value+'%';if(!A.vis[l]&&A.has(l)){A.vis[l]=true;const cb=$(`[data-layer="${l}"]`);if(cb)cb.checked=true}A.applyVis()});
document.addEventListener('click',e=>{const b=e.target.closest('[data-nx]');if(b){const k=b.dataset.nx;if(k==='unhide')NX.unhideAll();if(k==='unpin')NX.clearPins();if(k==='all'){LN.forEach((n,l)=>{if(A.has(l))A.vis[l]=true});A.applyVis();render()}if(k==='none'){LN.forEach((n,l)=>A.vis[l]=l===2);A.applyVis();render()}return}
 const h=e.target.closest('[data-nxhide]');if(h){e.stopPropagation();const i=+h.dataset.nxhide;NXH.has(i)?NX.show(i):NX.hide(i);return}
 const s=e.target.closest('[data-nxsel]');if(s){const i=+s.dataset.nxsel,p=PT[i];if(NXH.has(i))NX.show(i);if(A.focus)setFocus(null);if(!A.vis[p.l]){A.vis[p.l]=true;A.applyVis()}choose(i,true);focusBox(p.box,false);zoom=Math.max(zoom,4.5);return}});
// ---- structure tree (system → region → structure) ----
function tree(){if(!A.ready||!PT.length)return'';const by={};PT.forEach((p,i)=>{(by[p.l]??={});(by[p.l][p.region||'Other']??=[]).push(i)});
 return `<div class="card nxtree"><div class="hd"><h3>Structures</h3><span class="demo">${PT.length.toLocaleString()} parts</span></div><input type="search" id="nxq" placeholder="Filter structures…" autocomplete="off"><div id="nxt">${LN.map((n,l)=>by[l]?`<details data-l="${l}"><summary><i style="background:${LCOL[l]}"></i>${n}<small>${Object.values(by[l]).reduce((a,b)=>a+b.length,0)}</small></summary>${Object.keys(by[l]).sort().map(r=>`<details data-r="${esc(r)}" data-l="${l}"><summary>${esc(r)}<small>${by[l][r].length}</small></summary><div class="nxlist"></div></details>`).join('')}</details>`:'').join('')}</div></div>`}
function item(i){const p=PT[i];return `<div class="nxit"><button data-nxsel="${i}">${esc(p.name)}</button><button class="eye ${NXH.has(i)?'off':''}" data-nxhide="${i}" title="Hide / show" aria-label="Hide or show ${esc(p.name)}">◉</button></div>`}
document.addEventListener('toggle',e=>{const d=e.target;if(!d.matches||!d.matches('.nxtree details[data-r]')||!d.open)return;const box=d.querySelector('.nxlist');if(box.childElementCount)return;const l=+d.dataset.l,r=d.dataset.r;box.innerHTML=PT.map((p,i)=>[p,i]).filter(([p])=>p.l===l&&(p.region||'Other')===r).sort((a,b)=>a[0].name.localeCompare(b[0].name)).map(([p,i])=>item(i)).join('')},true);
document.addEventListener('input',e=>{if(e.target.id!=='nxq')return;const q=e.target.value.trim().toLowerCase(),t=$('#nxt');if(q.length<2){t.innerHTML=tree().match(/<div id="nxt">([\s\S]*)<\/div><\/div>$/)[1];return}
 const hits=PT.map((p,i)=>[p,i]).filter(([p])=>p.s.includes(q)).slice(0,80);t.innerHTML=hits.length?`<div class="nxlist">${hits.map(([p,i])=>item(i)).join('')}</div>`:'<p class="mute sm">No match.</p>'});
// ---- stage controls: undo / redo peeling, colour-coded bones, studio background ----
const SV={undo:'<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',redo:'<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>',bones:'<circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="12" cy="17" r="3"/>',studio:'<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 14l5-4 4 3 4-5 5 6"/>'};
const rail=$('#tools');if(rail){rail.insertAdjacentHTML('beforeend',`<button id="nxUndo" title="Undo (Ctrl+Z)" aria-label="Undo"><svg viewBox="0 0 24 24">${SV.undo}</svg></button><button id="nxRedo" title="Redo (Ctrl+Shift+Z)" aria-label="Redo"><svg viewBox="0 0 24 24">${SV.redo}</svg></button><button id="nxBone" title="Colour-code each bone" aria-label="Colour-code bones"><svg viewBox="0 0 24 24">${SV.bones}</svg></button><button id="nxStudio" title="Dark studio background" aria-label="Dark studio background"><svg viewBox="0 0 24 24">${SV.studio}</svg></button>`);
 $('#nxUndo').onclick=e=>{e.stopPropagation();NX.undo()};$('#nxRedo').onclick=e=>{e.stopPropagation();NX.redo()};
 $('#nxBone').onclick=e=>{e.stopPropagation();A.boneCol=!A.boneCol;if(A.boneCol&&!A.vis[2]){A.vis[2]=true;A.applyVis();if(page==='lab')render()}boneColors(A.boneCol);toast(A.boneCol?'Bones colour-coded: each bone has its own colour':'Natural bone colour')};
 $('#nxStudio').onclick=e=>{e.stopPropagation();A.studio=!A.studio;stage.classList.toggle('studio',A.studio);try{localStorage.setItem('dk-studio',A.studio?'1':'')}catch(_){};syncTools()};syncHist()}
function syncTools(){const b=$('#nxBone'),s=$('#nxStudio');if(b)b.classList.toggle('on',!!A.boneCol);if(s)s.classList.toggle('on',!!A.studio)}
try{if(localStorage.getItem('dk-studio')){A.studio=true;stage.classList.add('studio')}}catch(_){}
addEventListener('keydown',e=>{if(page!=='lab'&&page!=='dash'&&page!=='patients')return;if(e.target.closest&&e.target.closest('input,textarea,select'))return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?NX.redo():NX.undo()}});
// atlas colour scheme per bone (our own palette)
const BC=[[/frontal bone/,0x9fa3c7],[/parietal/,0x86bd62],[/temporal bone/,0xc0773e],[/occipital/,0x9b5fa0],[/sphenoid/,0xc6c64a],[/ethmoid/,0xe39a3d],[/zygomatic/,0xe58b55],[/maxilla/,0xd9b27a],[/mandible/,0xd8c08e],[/nasal bone|nasal concha/,0x48b5a6],[/lacrimal/,0x6dd0c1],[/palatine/,0xd36f8a],[/vomer/,0xe06a6a],[/hyoid/,0xa0c4e8],
 [/vertebra c|atlas|axis/,0x79acdc],[/vertebra t/,0xe0b06d],[/vertebra l/,0x9ccb72],[/sacrum/,0xd88fb4],[/coccyx|coccygeal/,0xb58fd8],[/manubrium|body of sternum|xiphoid/,0xc79fdb],[/rib/,0xe6c49a],
 [/clavicle/,0xef9c5a],[/scapula/,0x67bcc6],[/humerus/,0xdecb64],[/radius/,0xef8686],[/ulna/,0x86aaee],[/scaphoid|lunate|triquetr|pisiform|trapezi|capitate|hamate/,0xb6d36a],[/metacarpal/,0xe7a4cf],[/phalanx.*(finger|hand)|phalanx of (thumb|index|middle|ring|little)/,0x9fd6d0],
 [/hip bone|ilium|ischium|pubis/,0xb39ce0],[/femur/,0xecbc59],[/patella/,0x5fbf9f],[/tibia/,0xdf8c6c],[/fibula/,0x8dbde0],[/talus|calcaneus|navicular|cuboid|cuneiform/,0xc4d46e],[/metatarsal/,0xe2a2c6],[/phalanx/,0x9fd6d0]];
const ORIG=new Map();
function boneColors(on){const tc=new THREE.Color();PT.forEach((p,i)=>{if(p.l!==2||p.k!==1)return;const L=p.L;if(!ORIG.has(i))ORIG.set(i,L.base.slice(p.vo*3,(p.vo+p.v)*3));let hex=null;if(on)for(const[re,c]of BC)if(re.test(p.s)){hex=c;break}
 if(hex===null){L.base.set(ORIG.get(i),p.vo*3)}else{tc.setHex(hex);for(let j=p.vo;j<p.vo+p.v;j++){L.base[j*3]=tc.r;L.base[j*3+1]=tc.g;L.base[j*3+2]=tc.b}}paint(i)});if(!on)ORIG.clear();syncTools()}
const _lab=PAGES.lab;PAGES.lab=()=>_lab()+tree();
const _set=PAGES.set;PAGES.set=()=>_set().replace('Male reference: BodyParts3D adult male with full muscle, skeleton, organ, vessel and nerve layers.','Male reference: Z-Anatomy atlas (built on BodyParts3D) with every muscle, bone, ligament, the heart and its valves, arteries, veins, brain, spinal cord and peripheral nerves.').replace('The full muscle layer and skeleton are the BodyParts3D male reference','Muscles, skeleton, vessels and nerves are the Z-Anatomy reference').replace('3D anatomy from BodyParts3D © DBCLS and the HuBMAP Human Reference Atlas v1.5, both CC BY 4.0','3D anatomy from Z-Anatomy (CC BY-SA 4.0, built on BodyParts3D © DBCLS) and the HuBMAP Human Reference Atlas v1.5 (CC BY 4.0)');
const st=document.createElement('style');st.textContent=`
.nxl{display:grid;gap:6px}.nxr{display:grid;grid-template-columns:minmax(0,1fr) 110px 38px;gap:10px;align-items:center;background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:8px 10px}.nxr.na{opacity:.45}
.nxr label{display:flex;gap:8px;align-items:center;min-width:0}.nxr input[type=checkbox]{width:auto}.nxr i,.nxtree summary i{width:10px;height:10px;border-radius:3px;flex:none}.nxr b{font-size:13px}.nxr small{color:var(--mute);font:500 10.5px var(--mono);margin-left:auto}
.nxr input[type=range]{padding:0;border:0;background:none}.nxr em{font:500 11px var(--mono);font-style:normal;color:var(--mute);text-align:right}
.nxbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}.nxbar small{font-size:11.5px}
.nxtree input[type=search]{margin-bottom:10px}.nxtree details{border-radius:10px}.nxtree>#nxt>details{background:var(--soft);border:1px solid var(--line);margin-bottom:6px;padding:4px 8px}
.nxtree summary{display:flex;gap:8px;align-items:center;cursor:pointer;padding:6px 2px;font-weight:600;font-size:13px;list-style:none}.nxtree summary::-webkit-details-marker{display:none}.nxtree summary small{margin-left:auto;color:var(--mute);font:500 10.5px var(--mono)}
.nxtree details details{margin-left:14px}.nxtree details details summary{font-weight:500;color:var(--mute)}
.nxlist{display:grid;gap:2px;max-height:300px;overflow:auto;padding:2px 0 6px}.nxit{display:flex;align-items:center;gap:4px}.nxit button:first-child{flex:1;text-align:left;font-size:12.5px;padding:5px 8px;border-radius:8px}.nxit button:first-child:hover{background:var(--acc-soft);color:var(--blue)}
#tools button:disabled{opacity:.35}
.stage.studio{background:radial-gradient(120% 90% at 50% 30%,#4b5059 0%,#2a2e35 55%,#16181d 100%)!important}.stage.studio .cr{color:#9aa1ad}.stage.studio .mhint{background:rgba(0,0,0,.35);color:#c9ced8}
.nxit .eye{width:26px;height:26px;border-radius:8px;color:var(--blue);font-size:12px}.nxit .eye.off{color:var(--mute);opacity:.5;text-decoration:line-through}
@media(max-width:650px){.nxr{grid-template-columns:1fr 80px 34px}}`;document.head.append(st);
})();
// ---- Latin names + "open in Heart Lab" on the info card ----
(()=>{let LAT={};try{LAT=JSON.parse($('#latz').textContent)}catch(e){}
 const HEARTRE=/ventricle|atrium|atrial|valve|leaflet|papillary|chorda|coronar|cardiac|aort|pulmonary trunk|vena cava|interventricular|circumflex|septomarginal|conduction|heart|myocard|pericard/i,NOTHEART=/lateral ventricle|third ventricle|fourth ventricle|of brain|cerebr|ventricle of larynx|laryngeal ventricle/i;
 const _si=showInfo;showInfo=function(tag,name,desc,specs){_si.apply(this,arguments);const la=LAT[name]||LAT[name.replace(/^(Left|Right) /,'')];if(la)$('#inm').insertAdjacentHTML('beforeend',`<small class="lat">${esc(la)}</small>`);
  if(HEARTRE.test(name)&&!NOTHEART.test(name))$('#ispec').insertAdjacentHTML('beforeend',`<button class="chip" data-nxheart="${esc(name)}">🫀 Open in Heart Lab</button>`)};
 document.addEventListener('click',e=>{const b=e.target.closest('[data-nxheart]');if(!b)return;const n=b.dataset.nxheart,sex=A.sex;go('heart');const t0=Date.now();(function w(){if(window.HLX&&HLX.AT.ready){if(typeof setBody==='function')setBody(sex==='female'?'female':'male');HLX.focusPart(n)}else if(Date.now()-t0<20000)setTimeout(w,200)})()});
})();
