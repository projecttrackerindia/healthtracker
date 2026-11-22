import * as THREE from "three";
try{
const ITEMS=window.ITEMS;
const V3=THREE.Vector3;
/* ---------- textures & materials ---------- */
function ctex(w,h,draw,rep){const c=document.createElement("canvas");c.width=w;c.height=h;draw(c.getContext("2d"),w,h);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8;if(rep){t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(rep,rep)}return t}
function star(g,x,y,r){g.beginPath();for(let i=0;i<10;i++){const a=i*Math.PI/5-Math.PI/2,rr=i%2?r*.45:r;g.lineTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr)}g.closePath();g.fill()}
function weave(g,w,h,base,pattern){g.fillStyle=base;g.fillRect(0,0,w,h);
  for(let i=0;i<h;i+=2){g.fillStyle="rgba(0,0,0,.03)";g.fillRect(0,i,w,1)}
  for(let i=0;i<w;i+=2){g.fillStyle="rgba(255,255,255,.035)";g.fillRect(i,0,1,h)}
  for(let i=0;i<2600;i++){g.fillStyle=Math.random()<.5?"rgba(255,255,255,.07)":"rgba(0,0,0,.035)";g.fillRect(Math.random()*w,Math.random()*h,1.3,1.3)}
  if(pattern==="stars"){g.fillStyle="rgba(255,255,255,.8)";for(let y=14;y<h;y+=36)for(let x=((y/36|0)%2)*18+10;x<w;x+=36)star(g,x,y,4.5)}
  if(pattern==="leaves"){g.fillStyle="rgba(255,255,255,.7)";for(let y=14;y<h;y+=36)for(let x=((y/36|0)%2)*18+10;x<w;x+=36){g.beginPath();g.ellipse(x,y,6,2.6,.6,0,7);g.fill()}}
  if(pattern==="terry"){for(let i=0;i<6000;i++){g.fillStyle=Math.random()<.5?"rgba(255,255,255,.09)":"rgba(0,0,0,.05)";g.beginPath();g.arc(Math.random()*w,Math.random()*h,1.1,0,7);g.fill()}}
  if(pattern==="rib"){for(let x=0;x<w;x+=5){g.fillStyle="rgba(0,0,0,.05)";g.fillRect(x,0,2,h)}}}
const MC={};
function fab(hex,pattern="plain",rep=1.5,rough=.92){const k=hex+pattern+rep;if(!MC[k])MC[k]=new THREE.MeshStandardMaterial({map:ctex(256,256,(g,w,h)=>weave(g,w,h,hex,pattern),rep),roughness:rough});return MC[k]}
function plain(hex,rough=.6,metal=0){const k="p"+hex+rough+metal;if(!MC[k])MC[k]=new THREE.MeshStandardMaterial({color:hex,roughness:rough,metalness:metal});return MC[k]}
function gloss(hex){const k="g"+hex;if(!MC[k])MC[k]=new THREE.MeshPhysicalMaterial({color:hex,roughness:.22,clearcoat:.8,clearcoatRoughness:.15});return MC[k]}
function labelTex(text,sub,bg="#FFFFFF",fg="#1D1D1F"){return ctex(512,320,(g,w,h)=>{g.fillStyle=bg;g.beginPath();g.roundRect(0,0,w,h,44);g.fill();
  g.fillStyle="#C8385F";g.beginPath();g.arc(66,70,16,0,7);g.fill();
  g.fillStyle=fg;g.font="600 52px -apple-system,Inter,sans-serif";g.textBaseline="middle";
  const words=text.split(" · ");g.fillText(words[0],44,150);if(words[1]){g.font="500 40px -apple-system,Inter,sans-serif";g.fillStyle="rgba(0,0,0,.5)";g.fillText(words[1],44,212)}
  g.fillStyle="rgba(0,0,0,.12)";g.fillRect(44,260,200,8)})}
/* the Urban Health logo, drawn from the header's own SVG so it is always the real one */
function logoTex(){return ctex(1024,256,(g,w,h)=>{const svg=document.querySelector(".gnav .logo svg.lgl")||document.querySelector(".gnav .logo svg");if(!svg)return;
  const vb=(svg.getAttribute("viewBox")||"0 0 333.6 64").trim().split(/[\s,]+/).map(Number),s=Math.min((w-40)/vb[2],(h-40)/vb[3]);
  g.save();g.translate((w-vb[2]*s)/2-vb[0]*s,(h-vb[3]*s)/2-vb[1]*s);g.scale(s,s);
  for(const el of svg.querySelectorAll("rect,path,circle")){g.save();const tr=(el.getAttribute("transform")||"").match(/translate\(\s*([-\d.]+)[\s,]+([-\d.]+)\s*\)/);if(tr)g.translate(+tr[1],+tr[2]);
    const A=k=>el.getAttribute(k),p=new Path2D();
    if(el.tagName==="rect"){const x=+A("x")||0,y=+A("y")||0,ww=+A("width"),hh=+A("height"),r=Math.min(+A("rx")||0,ww/2,hh/2);p.moveTo(x+r,y);p.arcTo(x+ww,y,x+ww,y+hh,r);p.arcTo(x+ww,y+hh,x,y+hh,r);p.arcTo(x,y+hh,x,y,r);p.arcTo(x,y,x+ww,y,r);p.closePath()}
    else if(el.tagName==="circle")p.arc(+A("cx"),+A("cy"),+A("r"),0,Math.PI*2);
    else p.addPath(new Path2D(A("d")));
    if(A("fill")&&A("fill")!=="none"){g.fillStyle=A("fill");g.fill(p)}
    if(A("stroke")&&A("stroke")!=="none"){g.strokeStyle=A("stroke");g.lineWidth=+A("stroke-width")||1;g.lineCap=A("stroke-linecap")||"butt";g.lineJoin=A("stroke-linejoin")||"miter";g.stroke(p)}
    g.restore()}
  g.restore()})}
/* ---------- geometry helpers ---------- */
function rrShape(w,d,r){const s=new THREE.Shape(),x=-w/2,y=-d/2;r=Math.min(r,w/2-.001,d/2-.001);s.moveTo(x+r,y);s.lineTo(x+w-r,y);s.quadraticCurveTo(x+w,y,x+w,y+r);s.lineTo(x+w,y+d-r);s.quadraticCurveTo(x+w,y+d,x+w-r,y+d);s.lineTo(x+r,y+d);s.quadraticCurveTo(x,y+d,x,y+d-r);s.lineTo(x,y+r);s.quadraticCurveTo(x,y,x+r,y);return s}
function rbox(w,h,d,r,mat){const bv=Math.min(r,h/2.2);const g=new THREE.ExtrudeGeometry(rrShape(Math.max(.02,w-2*bv),Math.max(.02,d-2*bv),Math.max(.005,r-bv*.5)),{depth:Math.max(.001,h-2*bv),bevelEnabled:true,bevelThickness:bv,bevelSize:bv,bevelSegments:5,curveSegments:10}).rotateX(-Math.PI/2);g.center();
  const uv=g.attributes.uv;for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)*1.2,uv.getY(i)*1.2);return new THREE.Mesh(g,mat)}
const cyl=(rt,rb,h,mat,seg=40)=>new THREE.Mesh(new THREE.CylinderGeometry(rt,rb,h,seg),mat);
const tor=(r,t,mat,arc=Math.PI*2)=>new THREE.Mesh(new THREE.TorusGeometry(r,t,16,64,arc),mat);
const plane=(w,h,mat)=>new THREE.Mesh(new THREE.PlaneGeometry(w,h),mat);
/* ---------- product models ---------- */
const OPT_PAT={swad:["stars","leaves","plain"]};
const B={
 garment(it,g){const m=fab(it.col,"plain",1.6);const n=it.id==="nighty"?2:1;
  for(let k=0;k<n;k++){const y=k*.15;const body=rbox(.86,.15,.64,.12,m);body.position.set(k*.03,y,k*.02);g.add(body);
   [-1,1].forEach(s=>{const sl=rbox(.24,.04,.56,.05,m);sl.position.set(k*.03+s*.27,y+.085,k*.02+.02);sl.rotation.y=s*.12;g.add(sl)})}
  const top=(n-1)*.15+.09;
  const col=tor(.13,.03,m,Math.PI);col.position.set((n-1)*.03,top,(n-1)*.02-.22);col.rotation.x=-.5;g.add(col);
  const pl=rbox(.07,.012,.46,.01,fab(it.col,"rib",1));pl.position.set((n-1)*.03,top+.004,(n-1)*.02+.05);g.add(pl);
  for(let i=0;i<3;i++){const bt=cyl(.022,.022,.014,plain("#FBF8F4",.35));bt.position.set((n-1)*.03,top+.014,(n-1)*.02-.08+i*.13);g.add(bt)}
  return g},
 jhabla(it,g){const m=fab(it.col,"rib",2);for(let k=0;k<2;k++){const b=rbox(.72,.09,.56,.08,m);b.position.set(k*.03,k*.095,k*-.02);g.add(b)}
  [-.12,.12].forEach(x=>{const tie=rbox(.03,.012,.22,.006,plain("#FFFFFF",.8));tie.position.set(x,.15,.12);tie.rotation.y=x*2;g.add(tie)});return g},
 bra(it,g){const m=fab(it.col);const b=rbox(.8,.08,.5,.08,m);g.add(b);
  [-.18,.18].forEach(x=>{const c=new THREE.Mesh(new THREE.SphereGeometry(.17,40,20,0,Math.PI*2,0,Math.PI/2),m);c.scale.set(1,.45,1);c.position.set(x,.04,0);g.add(c)});
  const strap=tor(.36,.014,m,Math.PI);strap.rotation.x=-Math.PI/2;strap.position.set(0,.05,-.05);g.add(strap);return g},
 outfit(it,g){const m=fab(it.col,"rib",2);const b=rbox(.72,.1,.56,.08,m);g.add(b);
  [-.14,.14].forEach(x=>{const bt=new THREE.Mesh(new THREE.CapsuleGeometry(.07,.12,8,16),fab("#F3EEE6"));bt.rotation.x=Math.PI/2;bt.scale.y=.8;bt.position.set(x,.1,.08);g.add(bt)});return g},
 fold(it,g){const pats=["stars","leaves","plain"];const pat=pats[(window.__optIdx?.(it))||0]||"plain";const cols=[it.col,"#F1F4F8",it.col];
  for(let k=0;k<3;k++){const b=rbox(.82,.1,.58,.07,fab(cols[k],k===1?"plain":pat,1.6));b.position.set((k-1)*.02,k*.1,(k%2)*.015);g.add(b)}return g},
 towel(it,g){const m=fab(it.col,"terry",1.4);for(let k=0;k<2;k++){const b=rbox(.84,.15,.6,.1,m);b.position.set(k*.025,k*.15,0);g.add(b)}
  const band=rbox(.845,.06,.1,.02,fab("#FFFFFF","terry"));band.position.set(.025,.2,.22);g.add(band);return g},
 pack(it,g){const S={"mm-diaper":[.74,.6,.4],"ps-undies":[.5,.56,.3],"mm-bpads":[.5,.5,.26],"ps-pads":[.62,.76,.36],"mm-wipes":[.72,.24,.46]},s=S[it.id]||[.6,.74,.36],flat=it.id==="mm-wipes";
  const b=rbox(s[0],s[1],s[2],flat?.09:.11,gloss(it.col));g.add(b);
  if(flat){const lid=rbox(s[0]*.5,.035,s[2]*.42,.03,plain("#FFFFFF",.35));lid.position.y=s[1]/2+.012;g.add(lid)}
  else{const seal=rbox(s[0]*.96,.05,s[2]*.7,.02,plain(it.col,.5));seal.position.y=s[1]/2;g.add(seal)}
  const lh=Math.min(s[0]*.45,s[1]*.8);const l=plane(lh*1.6,lh,new THREE.MeshStandardMaterial({map:labelTex(it.lab||"",""),transparent:true,roughness:.5}));l.position.set(0,flat?0:-.02,s[2]/2+.006);g.add(l);return g},
 box(it,g){const s=[.58,.36,.42];const b=rbox(s[0],s[1],s[2],.03,fab(it.col,"plain",1,.85));g.add(b);
  const lid=rbox(s[0]+.02,.08,s[2]+.02,.03,fab(it.col,"plain",1,.8));lid.position.y=s[1]/2-.02;g.add(lid);
  const l=plane(.4,.22,new THREE.MeshStandardMaterial({map:labelTex(it.lab||"SNACKS",""),transparent:true,roughness:.6}));l.position.set(0,-.03,s[2]/2+.006);g.add(l);return g},
 bottle(it,g){const b=cyl(.16,.16,.62,gloss(it.col),48);b.position.y=.31;g.add(b);
  const band=cyl(.162,.162,.12,plain("#FFFFFF",.4),48);band.position.y=.36;g.add(band);
  const cap=cyl(.13,.145,.16,plain("#2C2C2E",.35),40);cap.position.y=.7;g.add(cap);
  const st=cyl(.018,.018,.2,plain("#2C2C2E",.4),12);st.position.set(.05,.86,0);st.rotation.z=-.35;g.add(st);return g},
 wash(it,g){const b=cyl(.12,.13,.5,gloss(it.col),48);b.position.y=.25;g.add(b);
  const band=cyl(.132,.132,.16,plain("#FFFFFF",.4),48);band.position.y=.24;g.add(band);
  const cap=cyl(.085,.1,.12,plain("#FFFFFF",.3),40);cap.position.y=.56;g.add(cap);
  const flip=rbox(.1,.03,.07,.012,plain("#F2F2F4",.3));flip.position.set(0,.635,.01);g.add(flip);return g},
 backpack(it,g){const m=fab(it.col,"plain",1.3,.85),t=fab(it.col,"rib",1.2,.9);
  const body=rbox(.62,.82,.36,.16,m);body.position.y=.41;g.add(body);
  const pk=rbox(.48,.34,.1,.08,t);pk.position.set(0,.27,.2);g.add(pk);
  const z=rbox(.42,.02,.02,.008,plain("#3A3A3C",.4));z.position.set(0,.45,.25);g.add(z);
  const pull=rbox(.035,.06,.02,.008,plain("#C9C9CC",.25,.6));pull.position.set(.17,.42,.26);g.add(pull);
  const hd=tor(.1,.022,plain("#2B2B2D",.45),Math.PI);hd.position.set(0,.82,0);g.add(hd);
  [-.17,.17].forEach(x=>{const st=rbox(.07,.64,.03,.015,plain("#2B2B2D",.5));st.position.set(x,.42,-.195);g.add(st)});return g},
 jar(it,g){const b=cyl(.17,.17,.2,gloss("#FFFFFF"),48);b.position.y=.1;g.add(b);const l=cyl(.172,.172,.1,plain(it.col,.5),48);l.position.y=.1;g.add(l);
  const lid=cyl(.18,.18,.08,plain("#F2F2F2",.3),48);lid.position.y=.24;g.add(lid);return g},
 pouch(it,g){const b=rbox(.7,.32,.42,.15,fab(it.col,"plain",1.2));g.add(b);
  const z=rbox(.62,.03,.035,.012,plain("#3A3A3C",.4));z.position.y=.165;g.add(z);
  const pull=rbox(.05,.03,.11,.012,plain("#C9C9CC",.25,.6));pull.position.set(.27,.17,.06);g.add(pull);return g},
 slippers(it,g){const m=fab(it.col,"terry",1.2);[-.15,.15].forEach(x=>{const s=new THREE.Mesh(new THREE.CapsuleGeometry(.12,.42,10,24),m);s.rotation.x=Math.PI/2;s.scale.set(1,1,.38);s.position.set(x,.05,0);g.add(s);
   const strap=tor(.11,.035,m,Math.PI);strap.position.set(x,.07,-.12);g.add(strap)});return g},
 cable(it,g){const m=plain("#F2F2F4",.35);for(let k=0;k<3;k++){const t=tor(.2-k*.012,.022,m);t.rotation.x=-Math.PI/2;t.position.set(k*.012,.025+k*.03,k*.01);g.add(t)}
  const plug=rbox(.08,.06,.16,.02,m);plug.position.set(.26,.05,.08);g.add(plug);const tip=rbox(.05,.02,.05,.008,plain("#C9C9CC",.25,.7));tip.position.set(.26,.05,.18);g.add(tip);return g},
 ties(it,g){const cs=[it.col,"#2C2C2E","#C9B9A9"];cs.forEach((c,k)=>{const t=tor(.1,.026,plain(c,.7));t.rotation.x=-Math.PI/2+.15;t.position.set(-.18+k*.17,.03+k*.02,k%2*.06);g.add(t)});
  [0,1].forEach(k=>{const c=rbox(.22,.05,.07,.02,plain(k?"#2C2C2E":it.col,.5));c.position.set(.05,.03,.2+k*.1);g.add(c)});return g},
 belt(it,g){const m=fab(it.col,"rib",1.4);const r=cyl(.2,.2,.56,m,48);r.rotation.z=Math.PI/2;r.position.y=.2;g.add(r);
  const v=plane(.3,.16,plain("#BFB3A6",.95));v.position.set(0,.2,.201);g.add(v);return g},
 capset(it,g){const m=fab(it.col,"rib",2);const cap=new THREE.Mesh(new THREE.SphereGeometry(.2,40,20,0,Math.PI*2,0,Math.PI/2),m);cap.position.y=.0;g.add(cap);
  const rim=tor(.2,.03,m);rim.rotation.x=Math.PI/2;g.add(rim);
  [-.32,.32].forEach(x=>{const mt=new THREE.Mesh(new THREE.CapsuleGeometry(.08,.1,8,16),m);mt.rotation.x=Math.PI/2;mt.scale.y=.6;mt.position.set(x,.05,.04);g.add(mt)});return g},
 roll(it,g){const m=fab(it.col,"plain",1.4);const r=cyl(.22,.22,.86,m,48);r.rotation.z=Math.PI/2;r.position.y=.22;g.add(r);
  [-.22,.22].forEach(x=>{const b=tor(.226,.018,plain("#FFFFFF",.8));b.rotation.y=Math.PI/2;b.position.set(x,.22,0);g.add(b)});
  [-1,1].forEach(sg=>{const e=new THREE.Mesh(new THREE.CircleGeometry(.215,40),new THREE.MeshStandardMaterial({map:ctex(128,128,(c,w,h)=>{c.fillStyle=it.col;c.fillRect(0,0,w,h);c.strokeStyle="rgba(0,0,0,.12)";c.lineWidth=3;c.beginPath();for(let a=0;a<18;a+=.1){const rr=a*3.3;c.lineTo(64+Math.cos(a)*rr,64+Math.sin(a)*rr)}c.stroke()}),roughness:.95}));e.position.set(sg*.431,.22,0);e.rotation.y=sg*Math.PI/2;g.add(e)});return g},
 power(it,g){const b=rbox(.36,.13,.62,.05,plain("#3A3A3C",.45));g.add(b);
  for(let k=0;k<4;k++){const l=new THREE.Mesh(new THREE.SphereGeometry(.016,10,10),new THREE.MeshBasicMaterial({color:k<3?"#34C759":"#5A5A5E"}));l.position.set(-.06+k*.04,.067,.24);g.add(l)}
  const c=tor(.14,.016,plain("#F2F2F4",.35));c.rotation.x=-Math.PI/2;c.position.set(.36,0,-.1);g.add(c);return g},
 folder(it,g){const b=rbox(.82,.05,.6,.04,fab(it.col,"plain",1,.85));g.add(b);
  const paper=plane(.6,.5,plain("#FFFFFF",.9));paper.rotation.x=-Math.PI/2;paper.position.set(.04,.03,-.06);paper.rotation.z=.06;g.add(paper);
  const flap=rbox(.82,.02,.3,.03,fab(it.col,"plain",1,.8));flap.position.set(0,.045,.14);g.add(flap);
  const l=plane(.42,.26,new THREE.MeshStandardMaterial({map:labelTex(it.lab,""),transparent:true,roughness:.5}));l.rotation.x=-Math.PI/2;l.position.set(0,.057,.14);g.add(l);return g},
 book(it,g){const cover=rbox(.6,.09,.78,.02,fab(it.col,"plain",1,.8));g.add(cover);
  const pages=rbox(.56,.07,.74,.01,plain("#FAF8F4",.95));pages.position.set(.025,0,0);g.add(pages);
  const l=plane(.4,.25,new THREE.MeshStandardMaterial({map:labelTex(it.lab,""),transparent:true,roughness:.5}));l.rotation.x=-Math.PI/2;l.position.set(0,.047,-.05);g.add(l);
  const rib=plane(.03,.3,plain("#C8385F",.6));rib.rotation.x=-Math.PI/2;rib.position.set(.18,.047,.3);g.add(rib);return g},
 card(it,g){const b=rbox(.62,.03,.4,.04,plain("#2C2C2E",.3));g.add(b);
  const face=plane(.58,.36,new THREE.MeshStandardMaterial({map:ctex(512,320,(c,w,h)=>{c.fillStyle="#2C2C2E";c.fillRect(0,0,w,h);c.fillStyle="#fff";c.beginPath();c.roundRect(300,40,180,180,14);c.fill();c.fillStyle="#1D1D1F";for(let i=0;i<9;i++)for(let j=0;j<9;j++)if((i*7+j*3+i*j)%3)c.fillRect(316+i*17,56+j*17,14,14);c.fillStyle="#C8385F";c.beginPath();c.arc(56,64,16,0,7);c.fill();c.fillStyle="#fff";c.font="600 40px -apple-system,Inter,sans-serif";c.fillText("MEDICAL ID",36,150);c.font="400 26px -apple-system,Inter,sans-serif";c.fillStyle="rgba(255,255,255,.6)";c.fillText("Scan in an emergency",36,196)}),roughness:.3}));face.rotation.x=-Math.PI/2;face.position.y=.016;g.add(face);return g}
};
function build(it){const inner=new THREE.Group();(B[it.model]||B.pack)(it,inner);inner.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true}});
  const bb=new THREE.Box3().setFromObject(inner),c=bb.getCenter(new V3());inner.position.set(-c.x,-bb.min.y,-c.z);const g=new THREE.Group();g.add(inner);return g}
/* ---------- bag ---------- */
const W=2.5,D=1.35,H=1.45,BED=.6;   // BED: the padded base the things rest on, so a full bag shows them at the rim
function makeBag(){
  const G=new THREE.Group(),hidden=new THREE.MeshBasicMaterial({visible:false});
  const taper=geo=>{const p=geo.attributes.position;for(let i=0;i<p.count;i++){const k=.88+.12*(p.getY(i)/H);p.setX(i,p.getX(i)*k);p.setZ(i,p.getZ(i)*k)}geo.computeVertexNormals();return geo};
  const shell=taper(new THREE.ExtrudeGeometry(rrShape(W,D,.34),{depth:H,bevelEnabled:false,curveSegments:16}).rotateX(-Math.PI/2));
  const outer=new THREE.Mesh(shell,[hidden,fab("#F3EFE9","plain",2.2,.96)]);outer.castShadow=true;outer.receiveShadow=true;G.add(outer);
  const lin=shell.clone();lin.scale(.975,1,.955);G.add(new THREE.Mesh(lin,[hidden,new THREE.MeshStandardMaterial({map:fab("#E4DDD3","plain",2).map,roughness:1,side:THREE.BackSide})]));
  const bottom=new THREE.Mesh(new THREE.ShapeGeometry(rrShape(W*.87,D*.85,.28)).rotateX(-Math.PI/2),plain("#D8D0C5",1));bottom.position.y=BED-.012;bottom.scale.setScalar(.88+.12*BED/H);bottom.receiveShadow=true;G.add(bottom);
  const rimS=rrShape(W+.06,D+.06,.37);rimS.holes.push(rrShape(W-.05,D-.05,.31));
  const rim=new THREE.Mesh(new THREE.ExtrudeGeometry(rimS,{depth:.12,bevelEnabled:true,bevelThickness:.02,bevelSize:.02,bevelSegments:3,curveSegments:16}).rotateX(-Math.PI/2),fab("#ECE7E0","plain",3,.9));rim.position.y=H-.1;rim.castShadow=true;G.add(rim);
  const tag=plane(1.24,.31,new THREE.MeshStandardMaterial({map:logoTex(),transparent:true,roughness:.62,polygonOffset:true,polygonOffsetFactor:-2}));
  const ty=.64,tk=.88+.12*ty/H;tag.position.set(0,ty,D/2*tk+.008);tag.rotation.x=Math.atan(.12*D/2/H);G.add(tag);
  const hm=plain("#2B2B2D",.45);
  [1,-1].forEach(dir=>{const z0=dir*(D/2-.03),pts=[[-.6,H-.12],[-.58,H+.35],[-.38,H+.8],[0,H+.95],[.38,H+.8],[.58,H+.35],[.6,H-.12]].map(([x,y])=>new V3(x,y,z0+dir*Math.max(0,y-H)*.55));
    const m=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),64,.052,14),hm);m.castShadow=true;G.add(m);
    [-.6,.6].forEach(x=>{const t=rbox(.2,.26,.03,.01,hm);t.position.set(x,H-.2,z0+dir*.014);G.add(t)})});
  return G;
}
function studio(scene,soft=1){scene.add(new THREE.HemisphereLight(0xffffff,0xe6e1d9,1.15));
  const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(3.5,7,5);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-3,right:3,top:4,bottom:-2,near:1,far:20});key.shadow.bias=-.0006;key.shadow.radius=4;scene.add(key);
  const fill=new THREE.DirectionalLight(0xffffff,.55);fill.position.set(-4,2.5,3);scene.add(fill);
  const rim=new THREE.DirectionalLight(0xffffff,.8);rim.position.set(0,3,-6);scene.add(rim);
  const ground=new THREE.Mesh(new THREE.PlaneGeometry(14,14),new THREE.ShadowMaterial({opacity:.15*soft}));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);return key}
/* Lighter on slower phones. A phone with little memory, or anyone who asks for reduced motion, starts light: fewer
   pixels, a smaller shadow, no idle sway, and nothing drawn while nothing moves. A phone that turns out slow (frames
   longer than 40 ms) switches to the same settings by itself after a second or so. */
let LITE=(navigator.deviceMemory||8)<=3||(navigator.hardwareConcurrency||8)<=4||matchMedia("(prefers-reduced-motion: reduce)").matches;
const liteDpr=()=>Math.min(devicePixelRatio,1.25);
/* ---------- product thumbnails (rendered once) ---------- */
(function thumbs(){
  const R=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});R.setPixelRatio(1);R.setSize(LITE?320:480,LITE?320:480,false);R.outputColorSpace=THREE.SRGBColorSpace;R.toneMapping=THREE.ACESFilmicToneMapping;R.toneMappingExposure=1.05;R.shadowMap.enabled=true;R.shadowMap.type=THREE.PCFSoftShadowMap;
  const sc=new THREE.Scene(),key=studio(sc,1.4);if(LITE)key.shadow.mapSize.set(1024,1024);key.position.set(2.2,5,3.2);Object.assign(key.shadow.camera,{left:-1.2,right:1.2,top:1.2,bottom:-1.2});key.shadow.camera.updateProjectionMatrix();
  const cam=new THREE.PerspectiveCamera(24,1,.01,60),dir=new V3(.62,.72,1.15).normalize();
  const out={};
  ITEMS.forEach(it=>{const m=build(it);m.rotation.y=-.45;sc.add(m);m.updateMatrixWorld(true);
    const sp=new THREE.Box3().setFromObject(m).getBoundingSphere(new THREE.Sphere());
    const d=sp.radius/Math.sin(THREE.MathUtils.degToRad(12))*1.04;cam.position.copy(sp.center).addScaledVector(dir,d);cam.lookAt(sp.center);
    R.render(sc,cam);out[it.id]=R.domElement.toDataURL("image/png");sc.remove(m)});
  // bag snapshot for the story
  R.setSize(640,560,false);cam.aspect=640/560;cam.fov=27;cam.updateProjectionMatrix();key.position.set(3.5,7,5);Object.assign(key.shadow.camera,{left:-3,right:3,top:4,bottom:-2});key.shadow.camera.updateProjectionMatrix();
  const bag=makeBag();bag.rotation.y=-.35;sc.add(bag);cam.position.set(0,4.1,7.4);cam.lookAt(0,1.05,0);R.render(sc,cam);window.BAGIMG=R.domElement.toDataURL("image/png");
  R.dispose();R.forceContextLoss();
  Object.assign(window.THUMB,out);window.onThumbs&&window.onThumbs();
})();
/* ---------- live bag ---------- */
const R=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:"high-performance"});
R.setPixelRatio(LITE?liteDpr():Math.min(devicePixelRatio,2));R.outputColorSpace=THREE.SRGBColorSpace;R.toneMapping=THREE.ACESFilmicToneMapping;R.toneMappingExposure=1.05;R.shadowMap.enabled=true;R.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene(),KEY=studio(scene);if(LITE)KEY.shadow.mapSize.set(1024,1024);
let dirty=true,ft=[],lastF=0;   // dirty: something changed and needs drawing; ft: recent frame times, to notice a slow phone
function goLite(){if(LITE)return;LITE=true;R.setPixelRatio(liteDpr());KEY.shadow.mapSize.set(1024,1024);if(KEY.shadow.map){KEY.shadow.map.dispose();KEY.shadow.map=null}size();dirty=true}
const cs=ctex(128,128,(g)=>{const gr=g.createRadialGradient(64,64,4,64,64,64);gr.addColorStop(0,"rgba(0,0,0,.3)");gr.addColorStop(1,"rgba(0,0,0,0)");g.fillStyle=gr;g.fillRect(0,0,128,128)});
const blob=plane(3.8,2.1,new THREE.MeshBasicMaterial({map:cs,transparent:true,depthWrite:false}));blob.rotation.x=-Math.PI/2;blob.position.y=.004;scene.add(blob);
const G=makeBag();scene.add(G);
const cam=new THREE.PerspectiveCamera(27,1,.1,60);let dist=8.4;
let lookY=1.0;
function frame(){cam.position.set(0,dist*.52+lookY-1,dist);cam.lookAt(0,lookY,0)}
/* bag contents. Each item rests on whatever is under it: a fine height map of the basket floor, read under the item's
   own footprint (not whole coarse cells, which left items hovering over their neighbours). A new item goes to the lowest
   spot it fits, turned along or across the basket, so the bag fills from the floor up and nothing floats. */
const NX=36,NZ=18,X0=-1.04,X1=1.04,Z0=-.5,Z1=.5,FLOOR=BED,CW=(X1-X0)/NX,CD=(Z1-Z0)/NZ;let HM=new Array(NX*NZ).fill(FLOOR);
function cellsUnder(x,z,hx,hz,k){const i0=Math.max(0,Math.ceil((x-hx*k-X0)/CW-.5)),i1=Math.min(NX-1,Math.floor((x+hx*k-X0)/CW-.5)),
    j0=Math.max(0,Math.ceil((z-hz*k-Z0)/CD-.5)),j1=Math.min(NZ-1,Math.floor((z+hz*k-Z0)/CD-.5)),out=[];
  for(let j=j0;j<=j1;j++)for(let i=i0;i<=i1;i++)out.push(j*NX+i);
  if(!out.length)out.push(Math.max(0,Math.min(NZ-1,Math.floor((z-Z0)/CD)))*NX+Math.max(0,Math.min(NX-1,Math.floor((x-X0)/CW))));return out}
const live=new Map(),SC=.92;let bumpT=9;
function restAt(x,z,hx,hz){let top=FLOOR;for(const c of cellsUnder(x,z,hx,hz,.82))top=Math.max(top,HM[c]);return top}
function settle(o){const base=restAt(o.x,o.z,o.hx,o.hz);o.land=base-o.oy;const t=base+o.hy*2*.97;for(const c of cellsUnder(o.x,o.z,o.hx,o.hz,.92))HM[c]=Math.max(HM[c],t)}
function measure(m){const p=m.position.clone();m.position.set(0,0,0);m.updateMatrixWorld(true);const bb=new THREE.Box3().setFromObject(m);m.position.copy(p);m.updateMatrixWorld(true);
  // cx, cz: where the box's middle sits from the model's origin (a model laid on its side is no longer centred on it)
  return {hx:(bb.max.x-bb.min.x)/2,hz:(bb.max.z-bb.min.z)/2,hy:(bb.max.y-bb.min.y)/2,oy:bb.min.y,cx:(bb.min.x+bb.max.x)/2,cz:(bb.min.z+bb.max.z)/2}}
/* Where a new item goes: every spot on a fine grid, upright or laid on its side, along or across the basket. The one
   whose top ends lowest wins, so the bag fills in layers and nothing teeters on a tall neighbour. */
function bestSpot(o){let best=null;
  for(const lie of [0,1]){const d=lie?o.d1:o.d0;
    for(const turn of [0,1]){const hx=turn?d.hz:d.hx,hz=turn?d.hx:d.hz;if(2*hx>X1-X0+.08||2*hz>Z1-Z0+.08)continue;
      const sx=Math.max(0,X1-X0-2*hx),sz=Math.max(0,Z1-Z0-2*hz),nx=Math.max(1,Math.round(sx/.1)),nz=Math.max(1,Math.round(sz/.1));
      for(let a=0;a<=nx;a++)for(let b=0;b<=nz;b++){const x=X0+hx+sx*a/nx,z=Z0+hz+sz*b/nz,rest=restAt(x,z,hx,hz),sc=rest+2*d.hy+Math.random()*.03;
        if(!best||sc<best.sc)best={sc,x,z,turn,lie}}}}
  return best||{x:0,z:0,turn:0,lie:0}}
function prep(o){if(o.m0)return;const m=build(o.it);m.scale.setScalar(SC);m.rotation.set(0,0,0);o.m0=m;o.d0=measure(m);m.rotation.set(0,0,Math.PI/2);o.d1=measure(m);m.rotation.set(0,0,0)}
function dropInto(o){prep(o);const m=o.m0,sp=bestSpot(o),rz=sp.lie?Math.PI/2:0;
  m.rotation.set(0,(sp.turn?Math.PI/2:0)+(Math.random()<.5?0:Math.PI)+(Math.random()-.5)*.14,rz);
  const d=measure(m);Object.assign(o,{hx:d.hx,hz:d.hz,hy:d.hy,oy:d.oy,x:sp.x,z:sp.z,mx:sp.x-d.cx,mz:sp.z-d.cz});settle(o);
  o.m=m;o.vy=0;o.b=0;o.done=false;o.sq=0;o.tx=(Math.random()-.5)*.05;o.tz=rz+(Math.random()-.5)*.05;
  m.position.set(o.mx*.4,4.2,o.mz);m.rotation.x=(Math.random()-.5)*1.4;m.rotation.z=rz+(Math.random()-.5)*1.4;G.add(m)}
/* after something comes out, everything settles again from the bottom up */
function repack(){HM=new Array(NX*NZ).fill(FLOOR);const ls=[...live.values()].filter(o=>o.m).sort((a,b)=>(a.land+a.oy)-(b.land+b.oy));
  for(const o of ls){settle(o);if(o.m.position.y>o.land+.001){o.done=false;o.vy=0;o.b=2}}}
function shrink(m){const t0=performance.now();(function f(){const k=Math.min(1,(performance.now()-t0)/260);m.scale.setScalar(SC*(1-k));if(k<1)requestAnimationFrame(f);else G.remove(m)})()}
function sync(ids,fast){const want=new Set(ids);let removed=false;
  for(const [id,o] of [...live]){if(!want.has(id)){live.delete(id);if(o.m)shrink(o.m);removed=true}}
  if(removed)setTimeout(repack,280);
  const fresh=ids.filter(id=>!live.has(id)).map(id=>{const o={id,it:ITEMS.find(i=>i.id===id)};live.set(id,o);prep(o);return o});
  fresh.sort((a,b)=>b.d0.hx*b.d0.hz-a.d0.hx*a.d0.hz);   // the biggest footprints go in first, at the bottom
  fresh.forEach((o,k)=>setTimeout(()=>{if(live.get(o.id)===o)dropInto(o)},k*(fast?70:130)))}
/* drag to turn */
let yaw=-.35,tYaw=-.35,drag=null,lastDrag=-1e9;const el=R.domElement;
el.addEventListener("pointerdown",e=>{drag={x:e.clientX,y:tYaw};el.setPointerCapture(e.pointerId)});
el.addEventListener("pointermove",e=>{if(drag){tYaw=drag.y+(e.clientX-drag.x)*.012;lastDrag=performance.now()}});
el.addEventListener("pointerup",()=>{drag=null;lastDrag=performance.now()});el.addEventListener("pointercancel",()=>drag=null);
let host=null;const ro=new ResizeObserver(()=>size());
let baseDist=8.4;
function size(){dirty=true;if(!host)return;const w=host.clientWidth,h=host.clientHeight;if(w<4||h<4)return;R.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix();dist=baseDist*Math.max(1,1.3/cam.aspect);frame()}
function mount(h,d,ly){if(ly!=null)lookY=ly;if(d){baseDist=d;dist=d*Math.max(1,1.3/cam.aspect)}frame();if(host===h)return;if(host){ro.unobserve(host)}host=h;h.innerHTML="";h.appendChild(el);ro.observe(h);size();window.B3.host=h}
const clock=new THREE.Clock();
function tick(){requestAnimationFrame(tick);const dt=Math.min(.033,clock.getDelta()),t=clock.elapsedTime;if(!host||document.hidden)return;
  const r=host.getBoundingClientRect();if(r.bottom<0||r.top>innerHeight)return;
  if(!LITE&&!drag&&performance.now()-lastDrag>2500)tYaw+=((-.35+Math.sin(t*.4)*.3)-tYaw)*.02;
  let busy=dirty||drag||Math.abs(tYaw-yaw)>1e-4||Math.abs(shiftT-shiftX)>1e-3||Math.abs(liftT-lift)>.5||bumpT<1.5;
  yaw+=(tYaw-yaw)*.12;G.rotation.y=yaw;shiftX+=(shiftT-shiftX)*.06;G.position.x=shiftX;blob.position.x=shiftX;
  lift+=(liftT-lift)*.08;if(Math.abs(lift-liftOn)>.4){liftOn=lift;const w=host.clientWidth,h=host.clientHeight;if(Math.abs(lift)<.5){cam.clearViewOffset()}else{cam.setViewOffset(w,h,0,lift,w,h)}}
  bumpT+=dt;const bs=Math.exp(-7*bumpT)*Math.sin(bumpT*22)*.045;G.scale.set(1-bs*.6,1+bs,1-bs*.6);
  for(const o of live.values()){if(!o.m)continue;if(!o.done||o.sq>0)busy=true;if(o.done){if(o.sq>0){o.sq=Math.max(0,o.sq-dt*4);const s=Math.sin(o.sq*Math.PI)*.1;o.m.scale.set(SC*(1+s),SC*(1-s),SC*(1+s))}continue}
    o.vy-=15*dt;o.m.position.y+=o.vy*dt;o.m.position.x+=(o.mx-o.m.position.x)*Math.min(1,dt*6);o.m.position.z+=(o.mz-o.m.position.z)*Math.min(1,dt*6);
    o.m.rotation.x+=(o.tx-o.m.rotation.x)*Math.min(1,dt*5);o.m.rotation.z+=(o.tz-o.m.rotation.z)*Math.min(1,dt*5);
    if(o.m.position.y<=o.land){o.m.position.y=o.land;if(o.b<2&&o.vy<-1.2){o.vy=-o.vy*.25;o.b++;o.sq=1;if(o.b===1)bumpT=0}else{o.done=true;o.sq=1}}}
  if(!busy)return;   // nothing moved: keep the last frame and spare the battery
  dirty=false;const now=performance.now();if(lastF&&ft.length<90){ft.push(now-lastF);if(ft.length===90){const m=ft.slice().sort((a,b)=>a-b)[45];if(m>40)goLite()}}lastF=now;
  R.render(scene,cam);rendered++;if(window.onB3Frame)window.onB3Frame()}
let rendered=0;
let shiftX=0,shiftT=0,lift=0,liftT=0,liftOn=0;
function setLift(px){liftT=px;dirty=true}
function shift(x,instant){shiftT=x;if(instant){shiftX=x}dirty=true}
const _v=new V3(),_b=new THREE.Box3();
function toHost(v){v.project(cam);const w=host.clientWidth,h=host.clientHeight;return {x:(v.x*.5+.5)*w,y:(-v.y*.5+.5)*h}}
function screen(id){const o=live.get(id);if(!o||!o.m||!o.done||!host)return null;_b.setFromObject(o.m);if(_b.max.y<H-.12)return null;_v.set((_b.min.x+_b.max.x)/2,_b.max.y,(_b.min.z+_b.max.z)/2);return toHost(_v)}
const bagShell=G.children[0];
function bagBox(){if(!host)return null;_b.setFromObject(bagShell);let x0=1e9,x1=-1e9,y0=1e9,y1=-1e9;
  for(const x of [_b.min.x,_b.max.x])for(const y of [_b.min.y,_b.max.y+0.9])for(const z of [_b.min.z,_b.max.z]){const p=toHost(_v.set(x,y,z));x0=Math.min(x0,p.x);x1=Math.max(x1,p.x);y0=Math.min(y0,p.y);y1=Math.max(y1,p.y)}
  return {left:x0,right:x1,top:y0,bottom:y1}}
window.B3={ok:true,host:null,mount,sync,shift,lift:setLift,screen,bagBox,bump:()=>bumpT=0,perf:()=>({lite:LITE,rendered,dpr:R.getPixelRatio()}),
  /* for checks: where each item rests (bottom, top) against the rim */
  rest:()=>({rim:H,items:[...live.values()].filter(o=>o.m).map(o=>({id:o.id,bottom:+(o.land+o.oy).toFixed(3),top:+(o.land+o.oy+2*o.hy).toFixed(3),y:+(o.m.position.y-o.land).toFixed(4)}))})};
tick();
window.onB3Ready&&window.onB3Ready();
}catch(err){console.warn("3D unavailable — using illustrations",err)}
