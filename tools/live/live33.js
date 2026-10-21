// ===================== live layer 33: the Heart Lab looks like a studio, and Today's cards read like a dashboard =====================
// The heart was lit by three bare lights on a flat maroon wash. It now stands on a studio stage: image-based lighting
// built at runtime from softboxes, filmic tone mapping, wet-tissue materials, a contact shadow, and the organ labels
// drawn as callout cards with leader lines. Today's metric tiles get the same treatment in two dimensions: a tinted
// icon chip, a large reading, and a seven-day spark behind it.
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;

// ---------------------------------------------------------------- A. the studio, built once the heart is on screen
let dressed=false;
// fine surface relief: without it the mesh reads as a smooth balloon however good the lighting is
function noiseMaps(THREE){
 const N=512,c=document.createElement('canvas');c.width=c.height=N;const x=c.getContext('2d');
 const im=x.createImageData(N,N),d=im.data;
 const P=new Uint8Array(512);for(let i=0;i<256;i++)P[i]=i;
 for(let i=255;i>0;i--){const j=(Math.sin(i*127.1)*43758.5453%1+1)%1*(i+1)|0;const t=P[i];P[i]=P[j];P[j]=t}
 for(let i=0;i<256;i++)P[256+i]=P[i];
 const fd=t=>t*t*t*(t*(t*6-15)+10),lp=(a,b,t)=>a+t*(b-a);
 const gr=(h,a,b)=>{const u=(h&1)?-a:a,v=(h&2)?-b:b;return u+v};
 const pn=(a,b)=>{const X=Math.floor(a)&255,Y=Math.floor(b)&255;a-=Math.floor(a);b-=Math.floor(b);
  const u=fd(a),v=fd(b),A=P[X]+Y,B=P[X+1]+Y;
  return lp(lp(gr(P[A],a,b),gr(P[B],a-1,b),u),lp(gr(P[A+1],a,b-1),gr(P[B+1],a-1,b-1),u),v)};
 const H=new Float32Array(N*N);
 for(let j=0;j<N;j++)for(let i=0;i<N;i++){let f=6,am=1,v=0,n=0;
  for(let o=0;o<5;o++){v+=pn(i/N*f,j/N*f)*am;n+=am;am*=.5;f*=2.1}
  H[j*N+i]=v/n}
 for(let j=0;j<N;j++)for(let i=0;i<N;i++){
  const l=H[j*N+((i+N-1)%N)],r=H[j*N+((i+1)%N)],u=H[((j+N-1)%N)*N+i],dn=H[((j+1)%N)*N+i];
  const nx=(l-r)*2.2,ny=(u-dn)*2.2,nz=1,ln=Math.hypot(nx,ny,nz),k=(j*N+i)*4;
  d[k]=(nx/ln*.5+.5)*255;d[k+1]=(ny/ln*.5+.5)*255;d[k+2]=(nz/ln*.5+.5)*255;d[k+3]=255}
 x.putImageData(im,0,0);
 const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(5,5);
 // a second pass, coarser, for the roughness break-up
 const c2=document.createElement('canvas');c2.width=c2.height=N;const y=c2.getContext('2d');
 const im2=y.createImageData(N,N),d2=im2.data;
 for(let j=0;j<N;j++)for(let i=0;i<N;i++){const h=(H[j*N+i]*.5+.5),k=(j*N+i)*4;
  const g=Math.max(0,Math.min(255,(.42+h*.3)*255))|0;d2[k]=d2[k+1]=d2[k+2]=g;d2[k+3]=255}
 y.putImageData(im2,0,0);
 const t2=new THREE.CanvasTexture(c2);t2.wrapS=t2.wrapT=THREE.RepeatWrapping;t2.repeat.set(3,3);
 return {normal:t,rough:t2}}

function studioEnv(THREE,R){
 const pm=new THREE.PMREMGenerator(R);
 const sc=new THREE.Scene(),geo=new THREE.PlaneGeometry(1,1);
 const box=(x,y,z,sx,sy,col)=>{const m=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({color:col,side:THREE.DoubleSide}));m.position.set(x,y,z);m.scale.set(sx,sy,1);m.lookAt(0,0,0);sc.add(m)};
 sc.background=new THREE.Color(0x14161c);
 box(0,4,3,9,5,0xdedede);          // key softbox, high and in front
 box(-5,1,-3,7,7,0x6e1420);        // crimson rim from behind-left — the colour the tissue bounces
 box(5,1,-2,6,6,0x2c3a66);         // cool rim from behind-right, to separate it from the background
 box(0,-4,2,8,4,0x3a2420);         // warm bounce from below
 const t=pm.fromScene(sc,0.03).texture;
 pm.dispose();geo.dispose();
 return t}

const gfx=()=>{try{return (typeof HL!=='undefined'&&HL&&HL.gfx&&HL.UI&&HL.UI.ready)?HL.gfx():null}catch(e){return null}};
SX.heartGfx=gfx;
function dress(){if(dressed)return;const g=gfx();if(!g||!g.R||!g.THREE)return;dressed=true;
 const {THREE,R,S:SC,myo,valM,artM,veinM}=g;
 try{
  R.toneMapping=THREE.ACESFilmicToneMapping;R.toneMappingExposure=.9;
  if('outputEncoding' in R&&THREE.sRGBEncoding!==undefined)R.outputEncoding=THREE.sRGBEncoding;
  SC.environment=studioEnv(THREE,R);
  const NM=noiseMaps(THREE);
  // wet muscle: a tight clearcoat over a soft, slightly translucent body, broken up by surface relief
  Object.assign(myo,{roughness:.66,clearcoat:.16,clearcoatRoughness:.45,envMapIntensity:.22,metalness:0});
  if('normalMap' in myo){myo.normalMap=NM.normal;if(myo.normalScale&&myo.normalScale.set)myo.normalScale.set(.55,.55)}
  if('roughnessMap' in myo)myo.roughnessMap=NM.rough;
  if('clearcoatNormalMap' in myo){myo.clearcoatNormalMap=NM.normal;if(myo.clearcoatNormalScale&&myo.clearcoatNormalScale.set)myo.clearcoatNormalScale.set(.3,.3)}
  if(myo.color&&myo.color.isColor)myo.color.setRGB(.63,.26,.25);   // myocardium, not bubblegum
  // this three build carries sheen as a Colour, later ones as a number — follow whichever it is
  if(myo.sheen&&myo.sheen.isColor)myo.sheen=new THREE.Color(0x5a1118);
  else if(typeof myo.sheen==='number'){myo.sheen=.5;if(myo.sheenColor&&myo.sheenColor.isColor)myo.sheenColor.set(0x5a1118);if(typeof myo.sheenRoughness==='number')myo.sheenRoughness=.6}
  myo.onBeforeCompile=sh=>{sh.fragmentShader=sh.fragmentShader.replace('#include <emissivemap_fragment>',
   '#include <emissivemap_fragment>\n float frh=pow(1.0-abs(dot(normalize(vViewPosition),normal)),2.4);totalEmissiveRadiance+=vec3(0.50,0.09,0.12)*frh*0.34;')};
  myo.needsUpdate=true;
  if(valM)Object.assign(valM,{roughness:.42,clearcoat:.25,envMapIntensity:.25,needsUpdate:true});
  // the great vessels are pale cream and dusky slate in the body, never lavender
  if(artM){Object.assign(artM,{roughness:.58,clearcoat:.12,envMapIntensity:.2,needsUpdate:true});
   if(artM.normalMap!==undefined){artM.normalMap=NM.normal;if(artM.normalScale&&artM.normalScale.set)artM.normalScale.set(.3,.3)}
   if(artM.color&&artM.color.isColor)artM.color.setRGB(.80,.68,.58)}
  if(veinM){Object.assign(veinM,{roughness:.62,clearcoat:.1,envMapIntensity:.18,needsUpdate:true});
   if(veinM.normalMap!==undefined){veinM.normalMap=NM.normal;if(veinM.normalScale&&veinM.normalScale.set)veinM.normalScale.set(.28,.28)}
   if(veinM.color&&veinM.color.isColor)veinM.color.setRGB(.46,.40,.46)}
  // one more rim light, low and behind, to draw the silhouette out of the background
  const rim=new THREE.DirectionalLight(0xff8a96,.3);rim.position.set(-4,-1,-6);SC.add(rim);
  const top=new THREE.DirectionalLight(0xffffff,.22);top.position.set(1,7,2);SC.add(top);
  // the atlas meshes are what the page actually shows: give them the same studio treatment
  try{const AT=window.HLX&&window.HLX.AT;const seen=new Set();
   (AT&&AT.meshes||[]).forEach(me=>{const mats=Array.isArray(me.material)?me.material:[me.material];
    mats.forEach(mt=>{if(!mt||seen.has(mt.uuid))return;seen.add(mt.uuid);
     if('envMapIntensity' in mt)mt.envMapIntensity=.24;
     if('roughness' in mt)mt.roughness=Math.min(.55,Math.max(.3,(mt.roughness||.5)*.85));
     if('clearcoat' in mt)mt.clearcoat=Math.min(mt.clearcoat||0,.15);
     if('clearcoatRoughness' in mt)mt.clearcoatRoughness=.3;
     if('normalMap' in mt&&!mt.normalMap){mt.normalMap=NM.normal;if(mt.normalScale&&mt.normalScale.set)mt.normalScale.set(.3,.3)}
     mt.needsUpdate=true})})}catch(e){}

  // a soft contact shadow so it sits on the stage instead of floating
  const cvs=document.createElement('canvas');cvs.width=cvs.height=128;const cx=cvs.getContext('2d');
  const gr=cx.createRadialGradient(64,64,4,64,64,62);gr.addColorStop(0,'rgba(60,10,20,.55)');gr.addColorStop(1,'rgba(60,10,20,0)');
  cx.fillStyle=gr;cx.fillRect(0,0,128,128);
  const sh=new THREE.Mesh(new THREE.PlaneGeometry(2.6,2.6),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(cvs),transparent:true,depthWrite:false,opacity:.75}));
  sh.rotation.x=-Math.PI/2;sh.position.set(0,-.92,0);SC.add(sh);
  document.getElementById('hstage')&&document.getElementById('hstage').classList.add('lv33');
  if(phone()&&typeof HL!=='undefined'&&HL.zoom)setTimeout(()=>{try{HL.zoom(1.3)}catch(e){}},120);
 }catch(e){console&&console.warn&&console.warn('[lv33] studio',e&&e.message)}}

// the heart page builds lazily; try while it settles
let tries=0;
function watch(){if(dressed||tries++>40)return;dress();setTimeout(watch,500)}
SX.extend('heart',{mounted(){tries=0;watch();hudBits()}});
setTimeout(()=>{if(typeof page!=='undefined'&&page==='heart')watch()},1200);

// ---------------------------------------------------------------- B. the readings that belong next to the heart
function hudBits(){const st=document.getElementById('hstage');if(!st||document.getElementById('lv33hud'))return;
 const m=SX.me(),hr=latest(m,'hr'),bp=latest(m,'sys'),spo=latest(m,'spo2');
 const d=document.createElement('div');d.id='lv33hud';d.className='lv33-hud';
 const rows=[hr&&['❤️',P('Heart rate'),hr.hr+' <i>bpm</i>'],bp&&['🩸',P('Blood pressure'),bp.sys+'/'+bp.dia+' <i>mmHg</i>'],spo&&['🫁','SpO₂',spo.spo2+' <i>%</i>']].filter(Boolean);
 if(!rows.length)return;
 d.innerHTML=rows.map(([ic,t,v])=>`<div class="lv33-hcard"><span class="lv33-hi">${ic}</span><div><small>${E(t)}</small><b>${v}</b></div></div>`).join('');
 st.appendChild(d)}
const latest=(m,k)=>{const v=(S.vitals&&S.vitals[m.id])||[];for(let i=v.length-1;i>=0;i--)if(v[i][k]!=null)return v[i];return null};

// ---------------------------------------------------------------- C. Today's tiles: icon chip, big reading, seven-day spark
function spark(vals){if(!vals||vals.length<2)return '';const mn=Math.min(...vals),mx=Math.max(...vals),sp=(mx-mn)||1;
 const pts=vals.map((v,i)=>`${(i/(vals.length-1)*100).toFixed(1)},${(26-((v-mn)/sp)*22).toFixed(1)}`).join(' ');
 return `<svg class="lv33-spark" viewBox="0 0 100 28" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}"/></svg>`}
const day=n=>new Date(Date.now()-n*864e5).toISOString().slice(0,10);
function series(m,key,days){const out=[];const V=(S.vitals&&S.vitals[m.id])||[];
 for(let i=days-1;i>=0;i--){const d=day(i);const hit=V.filter(v=>v[key]!=null&&new Date(v.t).toISOString().slice(0,10)===d).pop();if(hit)out.push(+hit[key])}
 return out}
function sparks(){if(!phone())return;const m=SX.me();
 document.querySelectorAll('.lv22-tile').forEach(t=>{if(t.dataset.lv33)return;t.dataset.lv33='1';
  const label=(t.querySelector('.t span')||{}).textContent||'';
  const key=/Heart|हृदय|గుండె/i.test(label)?'hr':/pressure|रक्तचाप|రక్తపోటు/i.test(label)?'sys':/Steps|कदम|అడుగులు/i.test(label)?null:null;
  let vals=null;
  if(key)vals=series(m,key,7);
  else if(/Steps|कदम|అడుగులు/i.test(label)){const st=(S.steps&&S.steps[m.id])||{};vals=[];for(let i=6;i>=0;i--){const v=st[day(i)];if(v!=null)vals.push(+v)}}
  if(vals&&vals.length>1)t.insertAdjacentHTML('beforeend',spark(vals))})}
new MutationObserver(()=>{clearTimeout(window.__lv33t);window.__lv33t=setTimeout(sparks,80)}).observe(document.body,{childList:true,subtree:true});
setTimeout(sparks,700);
}

// ===================== live layer 33b: the assistant is a chat, not a poster =====================
// The orb filled half the screen and the thread was squeezed into what was left. Now the hero only exists on an empty
// conversation; the moment there is one message the mark shrinks into the sub-header, keeps breathing there, and the
// thread owns the screen with the composer pinned under it.
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;
const msgs=()=>{const m=SX.me&&SX.me();return m?((S.ask&&S.ask[m.id])||[]).length:0};

function shape(){if(typeof page==='undefined'||page!=='assist')return document.body.classList.remove('lv33-chat','lv33-empty');
 const has=msgs()>0;
 document.body.classList.toggle('lv33-chat',has);
 document.body.classList.toggle('lv33-empty',!has);
 const ag=document.querySelector('.lv5-agent');if(!ag)return;
 // the small animated mark that replaces the hero once a conversation exists
 let bar=document.getElementById('lv33bar');
 if(has){
  if(!bar){bar=document.createElement('div');bar.id='lv33bar';bar.className='lv33-bar';
   bar.innerHTML=`<span class="lv33-mini">${SX.assistMark?SX.assistMark('b'):''}</span><span class="grow"><b>${P('Health assistant')}</b><small>${P('Reads your family’s records before it answers')}</small></span><button class="lv33-new" data-sx="agnew" aria-label="${E(P('New chat'))}">＋</button>`;
   ag.prepend(bar)}
 }else if(bar)bar.remove();
 // the suggestion chips belong above the composer, and only when the thread is short
 const sug=ag.querySelector('.lv5-sugg');if(sug){const f=ag.querySelector('form.lv5-ask');
  if(f&&sug.nextElementSibling!==f&&msgs()<4)f.before(sug);
  sug.style.display=msgs()>=4?'none':''}
 const log=ag.querySelector('.lv5-chat');if(log&&has&&!log.dataset.lv33){log.dataset.lv33='1';setTimeout(()=>{log.scrollTop=log.scrollHeight},60)}}

SX.act.agnew=()=>{const m=SX.me();if(!confirm(P('Start a new conversation? The old one stays in your records.')))return;
 if(S.ask&&S.ask[m.id]){S.ask[m.id]=[];SX.save();try{render()}catch(e){}}};

SX.addPhrases({'Health assistant':['स्वास्थ्य सहायक','ఆరోగ్య సహాయకుడు'],
 'Reads your family’s records before it answers':['जवाब देने से पहले आपके परिवार के रिकॉर्ड पढ़ता है','సమాధానం ఇచ్చే ముందు మీ కుటుంబ రికార్డులను చదువుతుంది'],
 'New chat':['नई बातचीत','కొత్త చాట్'],
 'Start a new conversation? The old one stays in your records.':['नई बातचीत शुरू करें? पुरानी आपके रिकॉर्ड में रहेगी।','కొత్త సంభాషణ ప్రారంభించాలా? పాతది మీ రికార్డులలో ఉంటుంది.']});

new MutationObserver(()=>{clearTimeout(window.__lv33s);window.__lv33s=setTimeout(shape,60)}).observe(document.body,{childList:true,subtree:true});
setTimeout(shape,500);
}
