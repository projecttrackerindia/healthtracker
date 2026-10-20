"""Round 23: lab trends; demo-mode fixes. Run: python -m pytest -q tests/test_round23.py"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_page_carries_layer_23_and_demo_fixes():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p23*/" in html and "SX.act.labtrend=" in html and "lv23-grid" in html
    # the demo banner no longer shares its class with <body>
    assert "b.className='lv16-demobar'" in html and ".lv16-demobar{" in html and "b.className='lv16-demo'" not in html
    # the sample family keeps every section's structure and has a complete health card
    assert "const blank=(v,d)=>" in html and "(SX.seeds||[]).forEach(f=>{try{f(S)}catch(e){}})" in html
    assert "dob:'1990-04-12',sexOk:true,ph:'+919876500000'" in html and "mid:{d1:{blood:'O+'" in html
    assert subprocess.run(["python3", str(ROOT / "tools" / "compress.py"), "--check"], capture_output=True).returncode == 0


def test_trend_chart_draws_band_points_and_years():
    if not shutil.which("node"):
        import pytest
        pytest.skip("node not installed")
    js = r"""
const fs=require('fs');const html=fs.readFileSync(process.argv[process.argv.length-1],'utf8');
const i=html.indexOf('/*live-p23*/');const nxt=html.indexOf('/*live-p',i+10);const j=nxt>0?nxt:html.indexOf('SX.boot();\n})();',i);const src=html.slice(i,j);
const S={results:{d2:[{id:'r1',k:'lab',key:'ldl',val:158,date:'2026-10-08'},{id:'r4',k:'lab',key:'ldl',val:176,date:'2026-04-03'},{id:'r5',k:'lab',key:'ldl',val:120,date:'2025-01-15'},{id:'h1',k:'lab',key:'hb',val:13.2,date:'2026-01-01'}]}};
const LABS={ldl:{n:'LDL cholesterol',u:'mg/dL',d:0,what:'bad'},hb:{n:'Haemoglobin',u:'g/dL',d:1}};
const SX={p:s=>s,S,LABS,extend(){},me:()=>({id:'d2',name:'V'}),labRange:k=>k==='ldl'?[null,129]:[13,17],labStatus:x=>({s:x.key==='ldl'?(x.val>129?'high':'in'):'in',mild:x.val<160}),modal(){},act:{}};
global.document={documentElement:{clientWidth:390}};global.E=s=>String(s);
new Function('SX','S','E','P',src)(SX,S,global.E,SX.p);
const keys=SX.labTrendKeys({id:'d2'});if(JSON.stringify(keys)!=='["ldl"]')throw new Error('keys '+JSON.stringify(keys));   // hb has one result only
const c=SX.labTrendChart({id:'d2'},'ldl');
const num=(re)=>+(c.match(re)||[])[1];
if(!/upper 129/.test(c))throw new Error('no band label');
const bandY=num(/<rect x="40" y="([\d.]+)"/), p120=num(/cy="([\d.]+)" r="4.5" fill="var\(--green\)"/), p176=num(/cy="([\d.]+)" r="4.5" fill="var\(--red\)"/);
if(!(p176<bandY&&bandY<p120))throw new Error(`geometry: 176@${p176} band@${bandY} 120@${p120}`);   // higher value is drawn higher; the in-range point sits inside the band
if(!/>2025<\/text>/.test(c)||!/>2026<\/text>/.test(c))throw new Error('year ticks');
if(!/>176<\/text>/.test(c)||!/>158<\/text>/.test(c))throw new Error('value labels');
console.log('ok');
"""
    r = subprocess.run(["node", "-e", js, "--", str(ROOT / "web" / "index.html")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr
