"""Round 27: medicine interactions. Run: python -m pytest -q tests/test_round27.py"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_interactions_layer():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p27*/" in html and "SX.medInteract=" in html and "SX.medPairs=" in html
    assert "SX.medInteract(m,o.n,id)" in html         # hand-typed medicines are checked at save
    if not shutil.which("node"):
        return
    js = r"""
const fs=require('fs');const html=fs.readFileSync(process.argv[process.argv.length-1],'utf8');
const i=html.indexOf('/*live-p27*/');const nxt=html.indexOf('/*live-p',i+10);const j=nxt>0?nxt:html.indexOf('SX.boot();\n})();',i);const src=html.slice(i,j);
const S={meds:{d2:[{id:'a',n:'Telma 40',gen:'telmisartan',dose:'40 mg'},{id:'b',n:'Warfarin 5',gen:'warfarin'},{id:'c',n:'Thyronorm 50',gen:'levothyroxine'},{id:'d',n:'Calcium + D3',gen:'calcium'},{id:'e',n:'Dolo 650',gen:'paracetamol'}]}};
const SX={p:s=>s,S,extend(){},me:()=>({id:'d2',name:'V'}),medWarn:()=>[{lv:'warn',t:'base'}]};
new Function('SX','S','E','P',src)(SX,S,s=>String(s),SX.p);
const pairs=SX.medPairs({id:'d2'});
const has=(a,b)=>pairs.some(w=>w.t.startsWith(a+' + '+b)||w.t.startsWith(b+' + '+a));
if(!has('Thyronorm 50','Calcium + D3'))throw new Error('levothyroxine + calcium missed: '+JSON.stringify(pairs.map(w=>w.t)));
if(pairs.some(w=>/Dolo 650 \+ Dolo 650/.test(w.t)))throw new Error('self pair');
// adding ibuprofen to a warfarin + telmisartan list: stop (warfarin) first, then warn (ARB)
const w=SX.medInteract({id:'d2'},'Brufen 400 (ibuprofen)');
if(w.length<2||w[0].lv!=='stop'||!/Warfarin/.test(w[0].t)||!w.some(x=>/Telma 40/.test(x.t)&&x.lv==='warn'))throw new Error('ibuprofen: '+JSON.stringify(w));
// a second paracetamol flags the daily total; an unrelated medicine flags nothing
if(!SX.medInteract({id:'d2'},'Crocin Advance').some(x=>/under 3 g/.test(x.t)))throw new Error('paracetamol pair');
if(SX.medInteract({id:'d2'},'Cetirizine 10').length)throw new Error('false positive');
// the catalogue path keeps the base warnings and adds the pairs
const mw=SX.medWarn({id:'d2'},{n:'Ibuprofen',gen:'ibuprofen'});if(mw[0].t!=='base'||!mw.some(x=>/Warfarin/.test(x.t)))throw new Error('medWarn chain');
// nitrate + sildenafil is a stop
S.meds.d2=[{id:'n',n:'Sorbitrate',gen:'isosorbide'}];if(SX.medInteract({id:'d2'},'Sildenafil 50')[0].lv!=='stop')throw new Error('nitrate');
console.log('ok');
"""
    r = subprocess.run(["node", "-e", js, "--", str(ROOT / "web" / "index.html")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr
