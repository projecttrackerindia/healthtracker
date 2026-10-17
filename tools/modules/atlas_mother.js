// ---------- atlas heart inside the pregnant mother (HuBMAP female frame via the male→female warp) ----------
let MHU=null;
async function motherHeart(){try{MHU=MHU||ATLAS.uniforms();const D=await ATLAS.load(),W=makeFemWarp(JSON.parse($('#fwarp').textContent)),s=D.toBody.s,o=D.toBody.o;
 const xf=(x,y,z,t)=>W(x*s[0]+o[0],y*s[1]+o[1],z*s[2]+o[2],t,1);const grp=new THREE.Group();const cen=new V();let n=0;
 D.parts.forEach(p=>{if(p.k===10)return;const g=ATLAS.geo(p,xf);const m=new THREE.Mesh(g,ATLAS.mat(p.k,MHU));m.userData={atlas:p,info:[p.n,ATLAS.desc(p.n)]};grp.add(m);g.computeBoundingSphere();cen.add(g.boundingSphere.center);n++;clipped.push(m.material)});
 cen.multiplyScalar(1/n);grp.children.forEach(m=>m.geometry.translate(-cen.x,-cen.y,-cen.z));grp.position.copy(cen);grp.userData.base=cen.clone();M.heart=grp;M.g.add(grp)}catch(e){console.warn('mother heart',e)}}
function placeHeart(w){if(!M.heart)return;const k=ss(18,36,w);M.heart.position.copy(M.heart.userData.base).add(new V(.012*k,.05*k,.01*k));M.heart.rotation.set(0,0,.14*k);M.heart.scale.setScalar(1+.05*k)}
