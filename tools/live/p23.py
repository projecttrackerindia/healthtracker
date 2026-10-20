"""Round 23 patch: lab trends (sparklines + full chart by year)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p23*/"
s = W.read_text(encoding="utf-8")
if "/*live-p22*/" not in s:
    sys.exit("apply p22 first")
if MARK in s:
    sys.exit("already applied")
# demo: the sample family lacked every module's defaults (S.rem.off etc.), so the bell crashed; re-run the seeds after loading it
old_shape = "const shape={};Object.keys(S).forEach(k=>{const v=S[k];shape[k]=Array.isArray(v)?[]:(v&&typeof v==='object')?{}:v});"
if s.count(old_shape) != 1:
    sys.exit("demo shape anchor")
# keep the *structure* of every section (notes.seen, rem.off, …) but none of the family's data: strings/numbers/booleans are blanked, arrays emptied
s = s.replace(old_shape, "const blank=(v,d)=>Array.isArray(v)?[]:(v&&typeof v==='object')?(d>4?{}:Object.fromEntries(Object.keys(v).map(k=>[k,blank(v[k],d+1)]))):typeof v==='string'?'':typeof v==='number'?0:typeof v==='boolean'?false:v;const shape={};Object.keys(S).forEach(k=>{shape[k]=blank(S[k],0)});")
old_demo = "Object.assign(S,shape,sample(),{net:keep.net||{},lang:keep.lang||'en'});"
if s.count(old_demo) != 1:
    sys.exit("demo anchor")
s = s.replace(old_demo, old_demo + "(SX.seeds||[]).forEach(f=>{try{f(S)}catch(e){}});")
# the sample family's "You" has a complete health card, so the demo never opens the mandatory first-step form
s = s.replace("{id:'d1',pid:null,name:'Meera Raghavan',rel:'You',age:36,sex:'female',w:61,h:162,av:'MR',c:'',shared:true}",
              "{id:'d1',pid:null,name:'Meera Raghavan',rel:'You',age:36,sex:'female',w:61,h:162,av:'MR',c:'',shared:true,dob:'1990-04-12',sexOk:true,ph:'+919876500000'}")
s = s.replace("key:DEMO_KEY,demo:true,consent:{},net:{}}",
              "key:DEMO_KEY,demo:true,consent:{sos_location:true,sos_medid:true,doctor_share:false,pharmacy_rx:true},net:{},mid:{d1:{blood:'O+',allergies:['Penicillin'],conditions:[],donor:'',doctor:'',notes:'',policy:''},d2:{blood:'B+',allergies:[],conditions:['High blood pressure'],donor:'',doctor:'',notes:'',policy:''},d3:{blood:'A+',allergies:[],conditions:['Type 2 diabetes'],donor:'',doctor:'',notes:'',policy:''},d4:{blood:'O+',allergies:[],conditions:[],donor:'',doctor:'',notes:'',policy:''}}}")
# the demo banner shared its class name with <body> (body.lv16-demo), so the banner's white text colour painted the whole page
if s.count("b.className='lv16-demo'") != 1 or s.count(".lv16-demo{") != 2:
    sys.exit("demo banner anchors")
s = s.replace("b.className='lv16-demo'", "b.className='lv16-demobar'").replace(".lv16-demo{", ".lv16-demobar{").replace(".lv16-demo b{", ".lv16-demobar b{").replace(".lv16-demo .btn{", ".lv16-demobar .btn{")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live23-css">' + (HERE / "live23.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live23.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
