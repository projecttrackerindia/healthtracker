// ===================== Atlas heart: data + material (Z-Anatomy CC BY-SA 4.0 + generated structures) =====================
const ATLAS={data:null,loading:null,
 load(){if(this.data)return Promise.resolve(this.data);if(this.loading)return this.loading;return this.loading=(async()=>{const raw=Uint8Array.from(atob($('#heartz').textContent),c=>c.charCodeAt(0));const buf=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const jl=new DataView(buf).getUint32(0,true),meta=JSON.parse(new TextDecoder().decode(new Uint8Array(buf,4,jl))),base=4+jl;
  meta.parts.forEach(p=>{const o=base+p.o,v=p.v,q=new Uint16Array(buf,o,v*3),b=p.b,pos=new Float32Array(v*3);for(let j=0;j<v*3;j++){const a=j%3;pos[j]=b[a]+q[j]/65535*(b[a+3]-b[a])}
   let k=o+v*6;p.idx=new Uint16Array(buf,k,p.i);k+=p.i*2;p.col=new Uint8Array(buf,k,v*3);k+=v*3;p.sc=new Uint8Array(buf,k,v);k+=v;p.act=new Uint8Array(buf,k,v);p.pos=pos});
  this.data=meta;return meta})()},
 geo(p,xf){const g=new THREE.BufferGeometry();let pos=p.pos;if(xf){pos=new Float32Array(p.pos.length);const t=[0,0,0];for(let j=0;j<p.v;j++){xf(p.pos[j*3],p.pos[j*3+1],p.pos[j*3+2],t);pos[j*3]=t[0];pos[j*3+1]=t[1];pos[j*3+2]=t[2]}}
  g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('color',new THREE.BufferAttribute(p.col,3,true));g.setAttribute('sc',new THREE.BufferAttribute(p.sc,1));g.setAttribute('act',new THREE.BufferAttribute(p.act,1,true));g.setAttribute('hp',new THREE.BufferAttribute(p.pos,3));g.setIndex(new THREE.BufferAttribute(p.idx,1));g.computeVertexNormals();g.computeBoundingSphere();return g},
 uniforms(){const v4=()=>[0,1,2,3].map(()=>new THREE.Vector4());return{uWin:{value:v4()},uWinN:{value:v4()},uOn:{value:new THREE.Vector4()},uBeat:{value:new THREE.Vector4()},uC:{value:[0,1,2,3].map(()=>new THREE.Vector3())},uAx:{value:new THREE.Vector3(0,-1,0)},uWave:{value:-1},uTex:{value:1}}},
 // kinds: 1 chamber wall, 4 great vessel wall, 5 leaflet, 6 papillary/trabecula, 7 chordae, 8 coronary artery, 9 cardiac vein, 10 conduction
 mat(kind,U){const P={vertexColors:true,side:THREE.DoubleSide,roughness:.5,clearcoat:.3,clearcoatRoughness:.4};
  if(kind===5)Object.assign(P,{roughness:.32,clearcoat:.5,sheen:new THREE.Color(0x9aa6c0)});
  if(kind===7)Object.assign(P,{roughness:.35,clearcoat:.4});
  if(kind===8||kind===9)Object.assign(P,{roughness:.28,clearcoat:.7,clearcoatRoughness:.25});
  if(kind===10)Object.assign(P,{roughness:.4,emissive:new THREE.Color(0x3a2a00)});
  if(kind===4)Object.assign(P,{roughness:.42,clearcoat:.45,clearcoatRoughness:.3});
  if(kind===1)Object.assign(P,{roughness:.55,clearcoat:.18,clearcoatRoughness:.5});
  const m=new THREE.MeshPhysicalMaterial(P);m.extensions={derivatives:true};m.defines={KIND:kind};m.customProgramCacheKey=()=>'atlas'+kind;
  m.onBeforeCompile=sh=>{Object.assign(sh.uniforms,U);
   sh.vertexShader=sh.vertexShader.replace('#include <common>',`#include <common>
attribute float sc;attribute float act;attribute vec3 hp;varying float vSide;varying float vAct;varying vec3 vHP;uniform vec4 uBeat;uniform vec3 uC[4];uniform vec3 uAx;`)
    .replace('#include <begin_vertex>',`#include <begin_vertex>
vSide=mod(sc,2.);vAct=act;vHP=hp;float ch=floor(sc/2.+.01);
if(ch>.5){int ci=int(ch)-1;vec3 cc=ci==0?uC[0]:ci==1?uC[1]:ci==2?uC[2]:uC[3];float amt=ci==0?uBeat.x:ci==1?uBeat.y:ci==2?uBeat.z:uBeat.w;vec3 d=transformed-cc;
 if(ci<2){float a=dot(d,uAx);vec3 rd=d-uAx*a;transformed=cc+uAx*a*(1.-amt*.3)+rd*(1.-amt);}else transformed=cc+d*(1.-amt);}`);
   sh.fragmentShader=sh.fragmentShader.replace('#include <common>',`#include <common>
uniform vec4 uWin[4];uniform vec4 uWinN[4];uniform vec4 uOn;uniform float uWave;uniform float uTex;uniform vec3 uAx;varying float vSide;varying float vAct;varying vec3 vHP;
float ah(vec3 p){p=fract(p*0.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float an(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(ah(i),ah(i+vec3(1,0,0)),f.x),mix(ah(i+vec3(0,1,0)),ah(i+vec3(1,1,0)),f.x),f.y),mix(mix(ah(i+vec3(0,0,1)),ah(i+vec3(1,0,1)),f.x),mix(ah(i+vec3(0,1,1)),ah(i+vec3(1,1,1)),f.x),f.y),f.z);}
float af(vec3 p){return .5*an(p)+.25*an(p*2.03)+.125*an(p*4.01)+.0625*an(p*8.02);}
float inWin(vec3 p){for(int i=0;i<4;i++){if(uOn[i]>.5){vec3 d=p-uWin[i].xyz;vec3 n=uWinN[i].xyz;float al=dot(d,n);vec3 pr=d-al*n;float r=uWin[i].w*(1.+.06*(an(p*3.)-.5));if(length(pr)<r&&al>-uWinN[i].w&&al<3.)return 1.;}}return 0.;}
float hgt(vec3 p){float h=0.;
#if KIND==1
 if(vSide>.5){vec3 ax=normalize(uAx);float a=dot(p,ax);vec3 r=p-ax*a;float n=an(r*2.2+ax*a*.35)*.75+an(r*4.5+3.)*.25;h=pow(1.-abs(n*2.-1.),4.)*.13;}
 else h=an(p*2.2)*.035+an(p*9.)*.004;
#elif KIND==4
 h=an(p*3.)*.012;
#elif KIND==6
 h=af(vec3(p.x*7.,p.y*2.,p.z*7.))*.05;
#endif
 return h;}`)
    .replace('void main() {','void main() {\n#if KIND==1||KIND==8||KIND==9\n if(inWin(vHP)>.5)discard;\n#endif')
    .replace('#include <color_fragment>',`#include <color_fragment>
if(uTex>.5){
#if KIND==1||KIND==4
 if(!gl_FrontFacing){float s=an(vHP*vec3(14.,3.,14.));diffuseColor.rgb=mix(vec3(.55,.16,.15),vec3(.66,.24,.22),s)*(.9+.2*an(vHP*40.));}
#endif
#if KIND==1
 if(gl_FrontFacing&&vSide<.5){float f=an(vHP*1.8);diffuseColor.rgb*=.94+.1*f;}
#endif
#if KIND==10
 float g=uWave<0.?0.:smoothstep(.12,0.,abs(vAct-uWave))+step(vAct,uWave)*.25;diffuseColor.rgb=mix(diffuseColor.rgb,vec3(1.,.96,.7),clamp(g,0.,1.));
#endif
}`)
    .replace('#include <normal_fragment_maps>',`#include <normal_fragment_maps>
if(uTex>.5){float hh=hgt(vHP);vec3 sx=dFdx(-vViewPosition),sy=dFdy(-vViewPosition);float dhx=dFdx(hh),dhy=dFdy(hh);vec3 R1=cross(sy,normal),R2=cross(normal,sx);float det=dot(sx,R1);vec3 grd=sign(det)*(dhx*R1+dhy*R2);normal=normalize(abs(det)*normal-grd);}`)
    .replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
#if KIND==10
 if(uWave>=0.)totalEmissiveRadiance+=vec3(.9,.7,.1)*smoothstep(.1,0.,abs(vAct-uWave))*1.4;
#endif`)};
  return m},
 DESC:[[/left ventricle/i,'The strongest chamber. Its wall is about 1 cm thick and pumps oxygen-rich blood into the aorta at about 120 mmHg. Through the window you can see the mitral valve, its chordae and the two papillary muscles.'],
  [/right ventricle/i,'A thinner, crescent-shaped chamber that pumps blood to the lungs at about 25 mmHg. Inside: the tricuspid valve, chordae, three papillary muscles and the moderator band.'],
  [/left atrium/i,'Receives oxygen-rich blood from the four pulmonary veins and tops up the left ventricle through the mitral valve.'],
  [/right atrium/i,'Receives used blood from the superior and inferior venae cavae and the coronary sinus. The SA node, the natural pacemaker, sits in its wall.'],
  [/mitral/i,'The mitral (bicuspid) valve has two leaflets between the left atrium and ventricle. Chordae tendineae tether its edges to the papillary muscles so it does not flip back into the atrium.'],
  [/tricuspid/i,'The tricuspid valve has three leaflets between the right atrium and ventricle. It opens in diastole and closes at the first heart sound.'],
  [/pulmonary valve/i,'Three half-moon cusps at the exit of the right ventricle. They close at the second heart sound.'],
  [/coronary leaflet|non-coronary/i,'One of the three cusps of the aortic valve. The coronary arteries arise just above the left and right cusps.'],
  [/chordae/i,'Chordae tendineae: fine fibrous cords from the papillary muscles to the valve leaflets, like the strings of a parachute.'],
  [/papillary/i,'A papillary muscle: it contracts with the ventricle and pulls on the chordae so the valve stays shut during systole.'],
  [/septomarginal|moderator/i,'The moderator band (septomarginal trabecula) crosses the right ventricle and carries the right bundle branch to the anterior papillary muscle.'],
  [/conduction/i,'The conduction system: the SA node fires, the AV node delays, then the bundle of His, the left and right bundle branches and the Purkinje fibres spread the impulse so the ventricles squeeze from the apex up. Watch the glowing wave each beat.'],
  [/interventricular artery|LAD/i,'The LAD (anterior interventricular artery) runs down the front groove and supplies the front of the left ventricle and most of the septum. A blockage here is a "widow-maker" heart attack.'],
  [/circumflex/i,'The circumflex artery curves around the left atrioventricular groove and supplies the side and back of the left ventricle.'],
  [/right coronary|inferolateral branch/i,'The right coronary artery runs in the right atrioventricular groove. It supplies the right ventricle, the bottom of the heart and, in most people, the SA and AV nodes.'],
  [/left coronary artery/i,'The left main coronary artery is short and splits into the LAD and the circumflex artery.'],
  [/septal branches/i,'Septal branches of the LAD dive into the interventricular septum.'],
  [/cardiac vein|vein of left ventricle/i,'A cardiac vein: it carries used blood from the heart muscle to the coronary sinus.'],
  [/coronary sinus/i,'The coronary sinus collects blood from the cardiac veins and empties into the right atrium.'],
  [/arch of aorta/i,'The aortic arch gives off three branches: the brachiocephalic trunk, the left common carotid artery and the left subclavian artery.'],
  [/ascending aorta/i,'The first part of the aorta, rising from the left ventricle. The coronary arteries branch off at its root.'],
  [/descending aorta/i,'The descending (thoracic) aorta runs down behind the heart to the abdomen.'],
  [/pulmonary trunk|bifurcation of pulmonary/i,'Carries oxygen-poor blood from the right ventricle and splits into the right and left pulmonary arteries.'],
  [/pulmonary artery/i,'Takes oxygen-poor blood to one lung.'],
  [/pulmonary vein/i,'One of four pulmonary veins bringing oxygen-rich blood from the lungs to the left atrium.'],
  [/superior vena cava/i,'Returns blood from the head, neck and arms to the right atrium.'],
  [/inferior vena cava/i,'Returns blood from the lower body to the right atrium.'],
  [/carotid/i,'A common carotid artery: the main supply to the head and neck.'],
  [/subclavian/i,'A subclavian artery: supplies the arm and gives off the vertebral artery to the brain.'],
  [/brachiocephalic/i,'The brachiocephalic trunk: the first branch of the arch, splitting into the right subclavian and right common carotid arteries.']],
 desc(n){const d=this.DESC.find(([re])=>re.test(n));return d?d[1]:''}};
