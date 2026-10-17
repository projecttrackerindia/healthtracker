// ---- NX surface shading: baked AO, procedural bone porosity, cartilage sheen, ligament & muscle fibres ----
const NXSTR={value:1};
function nxShade(m){const prev=m.onBeforeCompile;m.onBeforeCompile=(sh,r)=>{if(prev&&prev!==THREE.Material.prototype.onBeforeCompile)prev(sh,r);sh.uniforms.nxStr=NXSTR;
 sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute float ao;attribute float kind;attribute vec3 fdir;varying float vAO;varying float vKind;varying vec3 vFd;varying vec3 vOP;')
  .replace('#include <begin_vertex>','#include <begin_vertex>\nvAO=ao;vKind=kind;vFd=fdir;vOP=position;');
 sh.fragmentShader=sh.fragmentShader.replace('#include <common>',`#include <common>
uniform float nxStr;varying float vAO;varying float vKind;varying vec3 vFd;varying vec3 vOP;
float nxh(vec3 p){p=fract(p*0.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float nxn(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);return mix(mix(mix(nxh(i),nxh(i+vec3(1,0,0)),f.x),mix(nxh(i+vec3(0,1,0)),nxh(i+vec3(1,1,0)),f.x),f.y),mix(mix(nxh(i+vec3(0,0,1)),nxh(i+vec3(1,0,1)),f.x),mix(nxh(i+vec3(0,1,1)),nxh(i+vec3(1,1,1)),f.x),f.y),f.z);}
float nxf(vec3 p){return .5*nxn(p)+.25*nxn(p*2.03)+.125*nxn(p*4.01)+.0625*nxn(p*8.02);}`)
  .replace('#include <color_fragment>',`#include <color_fragment>
float nk=floor(vKind+.5);
if(nxStr>.5){vec3 op=vOP;
 if(nk==1.){float m1=nxf(op*6.5);float m2=nxf(op*34.+3.1);float sp=smoothstep(.8,.95,nxn(op*260.))*smoothstep(.4,.7,m1);float st=smoothstep(.55,.8,nxf(op*14.+7.));
  diffuseColor.rgb*=mix(vec3(1.),vec3(.86,.77,.6),smoothstep(.3,.78,m1)*.65);
  diffuseColor.rgb*=1.-.12*m2-.14*sp;diffuseColor.rgb=mix(diffuseColor.rgb,diffuseColor.rgb*vec3(.9,.82,.7),st*.35);}
 else if(nk==2.){float m1=nxf(op*20.);diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.8,.87,.92),.3)*(.95+.07*m1);}
 else if(nk==3.||nk==4.){vec3 fd=normalize(vFd+vec3(1e-4));float t=dot(op,fd);vec3 q=op-fd*t;
  float s1=nxn(q*(nk==3.?420.:240.)+fd*t*5.);float s2=nxn(q*(nk==3.?950.:620.)+fd*t*11.+4.3);
  diffuseColor.rgb*=nk==3.?(.84+.12*s1+.06*s2):(.8+.16*s1+.08*s2);}
 else if(nk==5.){diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.96,.95,.9),.25);}
 diffuseColor.rgb*=mix(1.,vAO,.78);}`)
  .replace('#include <roughnessmap_fragment>',`#include <roughnessmap_fragment>
if(nxStr>.5){if(nk==2.)roughnessFactor=.3;else if(nk==5.)roughnessFactor=.2;else if(nk==3.)roughnessFactor=.38;else if(nk==1.)roughnessFactor=.68;else if(nk==4.)roughnessFactor=.52;}`)};m.needsUpdate=true}
