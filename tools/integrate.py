import re,sys
s=open('orig2.html').read()  # orig.html + Demo-2 pregnancy module (see base2.py)
# 1. worker source already in orig2 (Demo 2 fxsrc)
b=s.index('</script>',s.index('<script id="fxsrc" type="text/plain">'))
# 2. main-thread copy -> evaluate the same source
i=s.index('// ===================== procedural embryo / fetus (SDF + surface nets) =====================\nconst FX=(()=>{',b)
j=s.index('return{build,lerpT,skin,model,bio}})();',i)+len('return{build,lerpT,skin,model,bio}})();')
s=s[:i]+"const FX=new Function(document.getElementById('fxsrc').textContent+';return FX')();"+s[j:]
# ---- anatomy v2: Z-Anatomy (CC BY-SA 4.0) replaces the decimated BodyParts3D sets ----
import re as _re
for sid in ['mdl','nm','mdlm','nmm']:
    s,n=_re.subn(r'<script id="%s" type="[^"]+">.*?</script>\n?'%sid,'',s,count=1,flags=_re.S); assert n==1,sid
mdz=open('/home/claude/build/mdz.b64').read(); nmz=open('/home/claude/build/nmz.json').read()
k=s.index('<script id="mdlf"')
s=s[:k]+'<script id="mdz" type="text/plain">'+mdz+'</script>\n<script id="nmz" type="application/json">'+nmz+'</script>\n'+s[k:]
old="const ids=s=='male'?[['#mdl','#nm'],['#mdlm','#nmm']]:[['#mdlf','#nmf',(p,n)=>(p.l??1)!==1&&((p.l??1)!==2||KEEPF.test(n))],['#mdl','#nm',null,1],['#mdlm','#nmm',p=>p.l===2,1]],o=[];"
assert old in s
s=s.replace(old,"const MALEONLY=/testi|penis|penile|prostat|scrot|epididym|seminal|ejaculat|ductus deferens|spermatic|cremaster|glans/i,ids=s=='male'?[['#mdz','#nmz']]:[['#mdlf','#nmf',p=>{const l=p.l??1;return l===0||l===3}],['#mdz','#nmz',(p,n)=>p.l!==0&&!MALEONLY.test(n)&&(p.l!==3||p.y==='lymph'||p.y==='sense'),1]],o=[];")
old="if(p.g)tcol.set(PAL[p.g]);else"
assert old in s
s=s.replace(old,"if(p.c!==undefined)tcol.setHex(p.c);else if(p.g)tcol.set(PAL[p.g]);else")
old="return function(x,y,z,o){const P=[x,y,z],Q=[x,y,z],W={};"
assert old in s
s=s.replace(old,"return function(x,y,z,o,na){const P=[x,y,z],Q=[x,y,z],W={};")
old="const w=ss(-.1,.16,t)*lim*hip*"
assert old in s
s=s.replace(old,"const w=na?0:ss(-.1,.16,t)*lim*hip*")
old="if(S.warp){const t=[0,0,0],wb=[1e9,1e9,1e9,-1e9,-1e9,-1e9];for(let j=0;j<p.v;j++){const o=(vo+j)*3;S.warp(pos[o],pos[o+1],pos[o+2],t);"
assert old in s
s=s.replace(old,"if(S.warp){const t=[0,0,0],wb=[1e9,1e9,1e9,-1e9,-1e9,-1e9],na=(b[1]+b[4])/2<.6&&Math.abs((b[0]+b[3])/2)<.58;for(let j=0;j<p.v;j++){const o=(vo+j)*3;S.warp(pos[o],pos[o+1],pos[o+2],t,na);")
# ---- female hands: rigid hand fitted to the skin hand (see fwarp_hand.js / fwarp_H.json) ----
import json as _j
_i=s.index('function makeFemWarp(J){'); _k=s.index("if(typeof module!=='undefined')",_i)
s=s[:_i]+open('/home/claude/work/fwarp_hand.js').read()+s[_k:]
_m=_re.search(r'(<script id="fwarp" type="application/json">)(.*?)(</script>)',s,_re.S)
_J=_j.loads(_m.group(2)); _J['H']=_j.load(open('/home/claude/work/fwarp_H.json'))
# arm cross-section centres: move only halfway to the skin's centreline, so muscles keep their natural shape (full shift smeared the forearm)
for _sd in ('1','-1'):
    _a=_J['ARM'][_sd]
    for _f,_mm in (('cuf','cum'),('cvf','cvm')):
        _a[_f]=[round(_a[_mm][i]+.5*(_a[_f][i]-_a[_mm][i]),5) for i in range(len(_a[_f]))]
s=s[:_m.start(2)]+_j.dumps(_J,separators=(',',':'))+s[_m.end(2):]
# ---- lab tools patches ----
for old,new in [
 ("<script>\nconst $=s=>document.querySelector(s)","<script>\nwindow.NXH=new Set();window.NXP=[];\nconst $=s=>document.querySelector(s)"),
 ("PT.forEach((p,i)=>{if(F){if(!F.ids.has(i))return}else if(!p.L.mesh.visible","PT.forEach((p,i)=>{if(NXH.has(i))return;if(F){if(!F.ids.has(i))return}else if(!p.L.mesh.visible"),
 ("if(A.quiz){if(i>=0)quizClick(i)}else choose(i,false)}});","if(A.quiz){if(i>=0)quizClick(i)}else if(i>=0&&(e.ctrlKey||e.metaKey))NX.hide(i);else if(i>=0&&e.shiftKey)NX.pin(i);else choose(i,false)}});"),
 ("if(A.pins)items=A.pins;else if(A.labelsOn)","if(A.pins)items=A.pins;else if(NXP.length)items=NXP.map(i=>({i,t:PT[i].name,c:'#3d5afe'}));else if(A.labelsOn)"),
 ("const layerBoxes=()=>","let layerBoxes=()=>"),
 # Heart Lab: left-hand labels start below the control rows and the phase panel instead of running under them
 ("function layoutLabels(w,h){if(!LB.length)return;const Ls=[],Rs=[];LB.forEach(o=>{const v=typeof o.p==='string'",
  "let _lby=110,_lbt=0;const LBY0=()=>{const n=performance.now();if(n-_lbt<400)return _lby;_lbt=n;const st=document.getElementById('hstage').getBoundingClientRect();let b=110;['hphase','hwinw'].forEach(id=>{const e=document.getElementById(id);if(e&&!e.hidden&&e.offsetParent!==null)b=Math.max(b,e.getBoundingClientRect().bottom-st.top+12)});const pv=document.querySelector('#hstage .pvtop');if(pv)b=Math.max(b,pv.getBoundingClientRect().bottom-st.top+12);return _lby=b};\nfunction layoutLabels(w,h){if(!LB.length)return;const Ls=[],Rs=[];LB.forEach(o=>{const v=typeof o.p==='string'"),
 ("const place=(arr,left)=>{arr.sort((a,b)=>a.py-b.py);let y=110;arr.forEach(o=>{o.ly=Math.max(o.py,y);y=o.ly+24});",
  "const place=(arr,left)=>{arr.sort((a,b)=>a.py-b.py);let y=left?LBY0():110;arr.forEach(o=>{o.ly=Math.max(o.py,y);y=o.ly+Math.max(24,o.e.offsetHeight+6)});"),
 # phones: at most 3 labels per side so they never pile onto each other or the heart
 ("while(Rs.length>Ls.length+1){Rs.sort((a,b)=>a.px-b.px);Ls.push(Rs.shift())}",
  "if(w<520)[Ls,Rs].forEach(a=>{a.sort((p,q)=>p.py-q.py);while(a.length>3){const o=a.splice(a.length>>1,1)[0];o.e.style.display=o.ln.style.display=o.dt.style.display='none'}});\nwhile(Rs.length>Ls.length+1){Rs.sort((a,b)=>a.px-b.px);Ls.push(Rs.shift())}"),
 # phones: keep the tour card above the bottom tab bar
 ("function placeTour(el){const p=$('#tpop'),r=$('#tring'),W=innerWidth,Hh=innerHeight,",
  "function placeTour(el){const p=$('#tpop'),r=$('#tring'),W=innerWidth,Hh=(()=>{const a=document.querySelector('aside.side');if(!a||getComputedStyle(a).position!=='fixed')return innerHeight;const t=a.getBoundingClientRect().top;return t>innerHeight*.5?t-6:innerHeight})(),"),
 ("3D anatomy: BodyParts3D © DBCLS (male) · HuBMAP Human Reference Atlas v1.5 (female) · CC BY 4.0","3D anatomy: Z-Anatomy CC BY-SA 4.0 (built on BodyParts3D © DBCLS) · HuBMAP Human Reference Atlas v1.5 female organs CC BY 4.0"),
 ("Switch between the BodyParts3D male and the HuBMAP female reference body.","Switch between the Z-Anatomy male and the HuBMAP female reference body."),
]:
    assert s.count(old)==1,(old[:60],s.count(old)); s=s.replace(old,new)
old="let init='male';try{if(localStorage.getItem('dk-sex')==='female')init='female'}catch(e){}"
assert s.count(old)==1
s=s.replace(old,open('tools.js').read()+'\n'+old)
for old,new in [('/left biceps femoris/','/left (long |short )?(head of )?biceps femoris/'),
 ('/anterior interventricular branch of left coronary|trunk of left coronary/','/anterior interventricular branch of left coronary|trunk of left coronary|^left coronary artery$/'),
 ('/^right (supraspinatus|infraspinatus)$/','/^right (supraspinatus|infraspinatus)( muscle)?$/'),
 ('/left biceps femoris|^left semitendinosus$/','/left (long |short )?(head of )?biceps femoris|^left semitendinosus( muscle)?$/'),
 ('/(fourth|fifth) lumbar vertebra|lumbar vertebra (4|5)/','/(fourth|fifth) lumbar vertebra|lumbar vertebra (4|5)|^vertebra l(4|5)$|disc l4-l5/')]:
    assert s.count(old)==1,old; s=s.replace(old,new)
# ---- NX surface shading + new per-vertex attributes ----
for old,new in [
 ("function setX(on)", open('/home/claude/work/nxshade.js').read()+"\nmat.clearcoat=.06;mat.roughness=.55;nxShade(mat);nxShade(matSkin);nxShade(matSkinHi);\nfunction setX(on)"),
 ("const pos=new Float32Array(nv*3),col=new Float32Array(nv*3),idx=new Uint32Array(ni);let vo=0,io=0;","const pos=new Float32Array(nv*3),col=new Float32Array(nv*3),idx=new Uint32Array(ni),aoA=new Uint8Array(nv).fill(255),kA=new Uint8Array(nv),fA=new Int8Array(nv*3);let vo=0,io=0;"),
 ("p.b=wb}\n   for(let j=0;j<p.i;j++)idx[io+j]=ix[j]+vo;vo+=p.v;io+=p.i});","p.b=wb}\n   if(p.a)aoA.set(new Uint8Array(S.buf,S.base+p.o+p.v*6+p.i*2,p.v),vo);if(p.k)kA.fill(p.k,vo,vo+p.v);if(p.d)for(let j=vo;j<vo+p.v;j++){fA[j*3]=p.d[0];fA[j*3+1]=p.d[1];fA[j*3+2]=p.d[2]}\n   for(let j=0;j<p.i;j++)idx[io+j]=ix[j]+vo;vo+=p.v;io+=p.i});"),
 ("g.setIndex(new THREE.BufferAttribute(idx,1));g.computeVertexNormals();\n  const mesh=new THREE.Mesh(g,matFor(l))","g.setIndex(new THREE.BufferAttribute(idx,1));g.computeVertexNormals();g.setAttribute('ao',new THREE.BufferAttribute(aoA,1,true));g.setAttribute('kind',new THREE.BufferAttribute(kA,1));g.setAttribute('fdir',new THREE.BufferAttribute(fA,3,true));\n  const mesh=new THREE.Mesh(g,matFor(l))"),
 ("['position','normal','color'].forEach(a=>hg.setAttribute(a,g.attributes[a]))","['position','normal','color','ao','kind','fdir'].forEach(a=>hg.setAttribute(a,g.attributes[a]))"),
]:
    assert s.count(old)==1,(old[:70],s.count(old)); s=s.replace(old,new)
for old,new in [("Sc.add(new THREE.HemisphereLight(0xffffff,0x8a6a60,.95));\nconst L=new THREE.DirectionalLight(0xfff1e4,.9);","Sc.add(new THREE.HemisphereLight(0xffffff,0x8a6a60,.62));\nconst L=new THREE.DirectionalLight(0xfff1e4,.88);"),
 ("const rim=new THREE.DirectionalLight(0xbcd2ff,.55);","const rim=new THREE.DirectionalLight(0xbcd2ff,.42);"),("const fill=new THREE.DirectionalLight(0xffe0d0,.35);","const fill=new THREE.DirectionalLight(0xffe0d0,.26);")]:
    assert s.count(old)==1,old[:50]; s=s.replace(old,new)
old="const HL={ok:true,UI,cam:k=>{"
assert s.count(old)==1
s=s.replace(old,"window.HLX={O:()=>O,cut:m=>setCut(m),UI,G,S,R,setPlay:v=>{}};const HL={ok:true,UI,cam:k=>{")
# ---- atlas heart ----
s=s.replace('<script id="heartm"','<script id="heartz" type="text/plain">'+open('/home/claude/build/heartz.b64').read()+'</script>\n<script id="heartm"',1)
for old,new in [
 ("const esc=s=>String(s).replace(", open('/home/claude/work/atlas_core.js').read()+"\nconst esc=s=>String(s).replace("),
 ("window.HLX={O:()=>O,", open('/home/claude/work/atlas_hl.js').read()+"\nwindow.HLX={AT,setWin,applyAtlas,focusPart,O:()=>O,"),
 ("const L=[heart,...Object.values(VAL).map(v=>v.m),...deco.children].filter(Boolean);\n for(const h of rc.intersectObjects(L,false)){if(UI.cut!=='off'&&cutPl.distanceToPoint(h.point)<0)continue;return h}return null}",
  "const L=AT.on&&AT.ready?AT.meshes.filter(m=>m.visible):[heart,...Object.values(VAL).map(v=>v.m),...deco.children].filter(Boolean);\n for(const h of rc.intersectObjects(L,false)){if(AT.on){const k=h.object.userData.atlas.k;if((k===1||k===8||k===9)&&inWinJS(G.worldToLocal(h.point.clone())))continue;return h}if(UI.cut!=='off'&&cutPl.distanceToPoint(h.point)<0)continue;return h}return null}"),
 ("function clickAt(x,y){const h=hit(x,y),t=$('#htip');if(!h){t.hidden=true;return}","function clickAt(x,y){const h=hit(x,y),t=$('#htip');if(!h){t.hidden=true;if(AT.sel){AT.sel=null;applyAtlas()}return}if(h.object.userData.atlas)return atlasClick(h,t);"),
 ("TF=makeTF(st);deformMesh();\n updValve('mitral',st.avL,D);updValve('tricuspid',st.avR,D);updValve('aortic',st.slL,D);updValve('pulmonary',st.slR,D);",
  "TF=makeTF(st);if(!AT.on){deformMesh();\n updValve('mitral',st.avL,D);updValve('tricuspid',st.avR,D);updValve('aortic',st.slL,D);updValve('pulmonary',st.slR,D);}else if(AT.ready)atlasTick(st);"),
 ("pts.visible=UI.flow;","pts.visible=UI.flow&&!AT.on;"),
 ("function buildLabels(){$('#hlabels').replaceChildren();$('#hlines').replaceChildren();LB=[];if(!UI.labels)return;LBL.forEach(","function buildLabels(){$('#hlabels').replaceChildren();$('#hlines').replaceChildren();LB=[];if(!UI.labels)return;(AT.on&&AT.ready?atlasLabels():LBL).forEach("),
 ("UI.ready=true;$('#hld').hidden=true;","buildAtlas();UI.ready=true;$('#hld').hidden=true;"),
]:
    assert s.count(old)==1,(old[:80],s.count(old)); s=s.replace(old,new)
for old,new in [
 ("setElec:on=>{UI.elec=on;elec.visible=on;myo.transparent=on;myo.opacity=on?.32:1;myo.depthWrite=!on;myo.needsUpdate=true;buildLabels()}","setElec:on=>{UI.elec=on;const t=on&&!AT.on;myo.transparent=t;myo.opacity=t?.32:1;myo.depthWrite=!t;myo.needsUpdate=true;applyAtlas();buildLabels()}"),
 ("setCor:on=>deco.visible=on};","setCor:on=>{UI.cor=on;applyAtlas()}};"),
 ("['cut','Cut-away: off / four-chamber / long-axis',I.cut,()=>{const m=","['cut','Cut-away (atlas: open windows · physiology: sections)',I.cut,()=>{if(HLX.AT.on){const o=['none','front','right','left','all'],k=o[(o.indexOf(HLX.AT.wk)+1)%o.length];HLX.setWin(k);toast({none:'Closed heart',front:'Front windows: both ventricles',right:'Right heart opened',left:'Left heart opened',all:'All four chambers opened'}[k]);return}const m="),
 ("const UI={cut:'4ch',flow:true,elec:false,","const UI={cut:'off',flow:true,elec:true,"),
 ("const EDV=af?108:ex?125:sc==='brady'?135:120,ESV=ex?38:sc==='as'?58:50,","const BF=CY.body==='preg'?1.14:CY.body==='female'?.88:1,EDV=(af?108:ex?125:sc==='brady'?135:120)*BF,ESV=(ex?38:sc==='as'?58:50)*(CY.body==='preg'?1.05:CY.body==='female'?.86:1),"),
 ("aoMax=sc==='as'?118:ex?140:120,aoMin=ex?78:80;","aoMax=(sc==='as'?118:ex?140:120)-(CY.body==='preg'?6:CY.body==='female'?4:0),aoMin=(ex?78:80)-(CY.body==='preg'?10:0);"),
 ("AFTER.heart=()=>{hbuild();syncHUI()};","AFTER.heart=()=>{hbuild();syncHUI()};\n"+open('/home/claude/work/atlas_ui.js').read()),
]:
    assert s.count(old)==1,(old[:80],s.count(old)); s=s.replace(old,new)
MH=r"/ventric|atri|valve|papillary|chorda|septum|coronary|cardiac|circumflex|marginal art|diagonal|interventricular|arch of aorta|ascending aorta|pulmonary trunk|brachiocephalic|heart/i"
for old,new in [
 ("else if(l===3&&!HIDE.test(p.n))sets.org.push(p)","else if(l===3&&!HIDE.test(p.n)&&!(p.g===4&&"+MH+".test(p.n)))sets.org.push(p)"),
 ("M.g.add(M.fh);\n M.ready=true}","M.g.add(M.fh);\n await motherHeart();M.ready=true}\n"+open('/home/claude/work/atlas_mother.js').read()),
 ("const sv=st.EDV-st.ESV,hr=","const sv=Math.round(st.EDV-st.ESV),hr="),
 ("PS.on=true;PS.week=32;PS.view='mother';PS.tab='week';PS.camK='belly';PS.cut=true;PS.labels=false;PS.layers={bone:false,org:false};PS.skin=1;PS.still=matchMedia('(prefers-reduced-motion: reduce)').matches;document.documentElement.dataset.mode='preg';go('preg');\n</script>","PS.still=matchMedia('(prefers-reduced-motion: reduce)').matches;go('dash');\n</script>"),
 ("function go(p,opt={}){page=p;{const pg=p==='preg',hl=p==='heart';$('#stage').hidden=pg||hl;","function go(p,opt={}){page=p;{const pg=p==='preg',hl=p==='heart',nb=!(pg||hl||p==='dash'||p==='lab');$('#stage').hidden=pg||hl||nb;document.querySelector('.grid').classList.toggle('nobody',nb);"),
 ('Procedural heart model · textbook cardiac-cycle physiology · illustrative, not a patient simulation','Atlas heart: Z-Anatomy (CC BY-SA 4.0, built on BodyParts3D © DBCLS) + generated valves &amp; conduction · textbook cardiac-cycle physiology · educational, not a patient simulation'),
 ("if(M.ready){M.bone.visible=PS.layers.bone;M.org.visible=PS.layers.org}","if(M.ready){M.bone.visible=PS.layers.bone;M.org.visible=PS.layers.org;if(M.heart)M.heart.visible=PS.layers.org}"),
 ("L.push(M.org,M.bone,M.cx)","L.push(M.org,M.bone,M.cx);if(M.heart&&M.heart.visible)L.push(...M.heart.children)"),
 ("if(PS.view==='mother'){if(wasW!==w||force){deform(w);placeMother(w);fundal(w)}}","if(PS.view==='mother'){if(wasW!==w||force){deform(w);placeMother(w);fundal(w);placeHeart(w)}}"),
 ("L.push(['Bladder'","if(M.heart&&M.heart.visible)L.push([w>=24?'Heart (lifted & rotated by the uterus)':'Heart',()=>M.heart.getWorldPosition(new V())]);L.push(['Bladder'"),
 ("if(!info)return;$('#ptn').textContent=info[0];$('#ptd').textContent=info[1];t.hidden=false}","if(!info)return;$('#ptn').textContent=info[0];$('#ptd').textContent=info[1];if(h.object.userData.atlas){$('#ptd').insertAdjacentHTML('beforeend','<br><br>In pregnancy her heart pumps 30–50% more blood, beats 10–20 bpm faster, and is pushed up and rotated left by the growing uterus. ');const b=document.createElement('button');b.className='btn p sm';b.style.marginTop='8px';b.textContent='Open in Heart Lab (pregnancy)';b.onclick=()=>{go('heart');const t0=Date.now();(function w(){if(window.HLX&&HLX.AT.ready){setBody('preg');HLX.focusPart(h.object.userData.atlas.n)}else if(Date.now()-t0<20000)setTimeout(w,200)})()};$('#ptd').append(b)}t.hidden=false}"),
]:
    assert s.count(old)==1,(old[:70],s.count(old)); s=s.replace(old,new)
s=s.replace('<script id="mdlf"','<script id="latz" type="application/json">'+open('/home/claude/build/latz.json').read()+'</script>\n<script id="mdlf"',1)
# UI layers
import os
if os.path.exists('ui.css'):
    s=s.replace('</style></head>','</style>\n<style id="nx-ui">'+open('ui.css').read()+'</style></head>',1)
if os.path.exists('ui.js'):
    k=s.rindex('</script></body>')
    s=s[:k]+'</script>\n<script id="nx-ui-js">'+open('ui.js').read()+'\n'+s[k:]
# six-sidebar product layer (family, records, medicines, care, safety, privacy)
SIX=['core','net','safety','family','records','meds','care']
if os.path.exists('six/six.css'):
    s=s.replace('</style></head>','</style>\n<style id="six-css">'+open('six/six.css').read()+'</style></head>',1)
if os.path.exists('six/core.js'):
    code='\n'.join(open('six/%s.js'%n).read() for n in SIX if os.path.exists('six/%s.js'%n))
    assert '</script' not in code
    k=s.rindex('</script></body>')
    s=s[:k]+'</script>\n<script id="six-js">'+code+'\n'+s[k:]
# ---- brand: TheHealthTracker (thehealthtracker.com). Keep the X-DoKKo-Key header and storage keys unchanged so installs keep their data.
s=s.replace('DoKKo Heart Institute','Apex Heart Institute').replace('DoKKo Digestive Clinic','Lotus Digestive Clinic')
s=s.replace('<title>DoKKo · Advanced Anatomy Lab</title>','<title>TheHealthTracker · Family health, in 3D</title>')
s=s.replace('class="logo"><i>+</i>DoKKo</div>','class="logo">'+open('/home/claude/work/brand/out/svg/user-logo.svg').read().replace('<svg ','<svg class="thl" role="img" aria-label="TheHealthTracker" ',1)+'</div>')
s=re.sub(r'DoKKo(?!-Key)','TheHealthTracker',s)
open('new.html','w').write(s)
print('ok',len(s))
