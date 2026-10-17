const fs=require('fs'),re=require('path');
const html=fs.readFileSync('/home/claude/work/new.html','utf8');
const J=JSON.parse(html.match(/<script id="fwarp" type="application\/json">([\s\S]*?)<\/script>/)[1]);if(process.env.H)J.H=JSON.parse(fs.readFileSync('H.json','utf8'));
const src=process.argv[2]||'old';
let code;
if(src==='old'){const i=html.indexOf('function makeFemWarp(J){');const j=html.indexOf("if(typeof module!=='undefined')",i);code=html.slice(i,j)}
else code=fs.readFileSync(src,'utf8');
const mk=new Function(code+';return makeFemWarp')();
const W=mk(J);
const parts=JSON.parse(fs.readFileSync('hand_parts.json','utf8'));
const o=[0,0,0];
const out=parts.map(p=>({n:p.n,l:p.l,f:p.f,v:p.v.map(v=>{W(v[0],v[1],v[2],o);return [o[0],o[1],o[2]]})}));
fs.writeFileSync(process.argv[3]||'warped_old.json',JSON.stringify(out));
console.log('ok',out.length);
