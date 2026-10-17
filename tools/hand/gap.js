const fs=require('fs');
const html=fs.readFileSync('/home/claude/work/new.html','utf8');
const J=JSON.parse(html.match(/<script id="fwarp" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const mk=new Function(fs.readFileSync('fwarp_old.js','utf8')+';return makeFemWarp')();
const W=mk(J);const pose=JSON.parse(fs.readFileSync('icp_pose.json','utf8'))['-1'];
const o=[0,0,0];
function hp(v){const R=pose.R,s=pose.s,t=pose.t;return [0,1,2].map(i=>s*(R[i][0]*v[0]+R[i][1]*v[1]+R[i][2]*v[2])+t[i])}
const A=J.A['-1'];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
// sample male points along the forearm axis through the wrist: carpal centre and points up the forearm
const wc=[-0.91,0.02,0.065];
for(const dy of [0.7,0.5,0.35,0.2,0.1,0.05,0,-0.05,-0.12]){
  const p=[wc[0]+(-0.19)*dy*0, wc[1]+dy, wc[2]]; // straight up from wrist (y shift); crude but informative
  // slide along the arm direction instead
  const q=[wc[0]-A.dm[0]*(-dy)*1,wc[1]-A.dm[1]*(-dy),wc[2]-A.dm[2]*(-dy)];
  W(q[0],q[1],q[2],o);const tube=[...o];const h=hp(q);
  const d=[h[0]-tube[0],h[1]-tube[1],h[2]-tube[2]];
  console.log('dy',dy,'tube',tube.map(v=>v.toFixed(3)).join(','),'hand',h.map(v=>v.toFixed(3)).join(','),'gap',Math.hypot(...d).toFixed(3),'along df',dot(d,J.A['-1'].df).toFixed(3));
}
