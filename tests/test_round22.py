"""Round 22: the phone design system. Run: python -m pytest -q tests/test_round22.py"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_page_carries_layer_22_light_first():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p22*/" in html and 'id="live22-css"' in html
    # Round 35 changed this deliberately. It used to force data-theme="light" whenever the saved value was
    # not exactly "dark", and because the dark rules are guarded by :root:not([data-theme="light"]) that
    # overrode the phone's own setting: a device in dark mode still got the light app. No attribute at all is
    # what lets the phone decide, so "light" and "dark" are now the only values ever written.
    assert 'if(_t==="dark"||_t==="light")document.documentElement.dataset.theme=_t' in html
    assert 'document.documentElement.removeAttribute("data-theme")' in html
    assert ":root,:root[data-theme=light]{--bg:#f4f6fb" in html and ":root[data-theme=dark]{--bg:#07080d" in html
    assert "fonts.googleapis.com/css2?family=Plus+Jakarta+Sans" in html
    assert "SX.ico=" in html and "#lv22add" in html and "lv22-tiles" in html and "lv22-fam" in html
    assert "const V='dk-r" in (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    assert subprocess.run(["python3", str(ROOT / "tools" / "compress.py"), "--check"], capture_output=True).returncode == 0


def test_layer_22_runs_against_a_fake_app():
    """The layer must load with no page: theme bootstrap, icon set, tiles and week strip on sample data."""
    if not shutil.which("node"):
        import pytest
        pytest.skip("node not installed")
    js = r"""
const fs=require('fs');const html=fs.readFileSync(process.argv[process.argv.length-1],'utf8');
const i=html.indexOf('/*live-p22*/');const nxt=html.indexOf('/*live-p',i+10);const j=nxt>0?nxt:html.indexOf('SX.boot();\n})();',i);
const src=html.slice(i,j);
const store={};global.localStorage={getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=String(v),removeItem:k=>delete store[k]};
const el=()=>({dataset:{},querySelectorAll:()=>[],querySelector:()=>null,appendChild(){},prepend(){},innerHTML:'',classList:{add(){},toggle(){}},setAttribute(){},getBoundingClientRect:()=>({height:0})});
global.document={documentElement:{dataset:{},removeAttribute(){delete this.dataset.theme},setAttribute(k,v){this.dataset.theme=v}},body:el(),getElementById:()=>el(),querySelector:()=>null,querySelectorAll:()=>[],createElement:()=>el()};
global.MutationObserver=class{observe(){}};global.matchMedia=()=>({matches:true});global.window=global;global.setTimeout=()=>0;global.setInterval=()=>0;
global.page='dash';global.render=()=>{};global.go=()=>{};global.toast=()=>{};
const S={members:[{id:'d1',name:'Meera Raghavan',rel:'You'},{id:'d2',name:'Vikram',rel:'Husband'}],active:'d1',steps:{d1:{[new Date().toISOString().slice(0,10)]:6420}},sleep:{},vitals:{d1:[{t:Date.now()-3600e3,hr:72},{t:Date.now()-7200e3,sys:142,dia:91}]}};
const SX={p:s=>s,S,extend(){},me:()=>S.members[0],avatar:(m,s)=>'<div class="av">'+m.name[0]+'</div>',modal(){},closeModal(){},user:null};
const E=s=>String(s);
new Function('SX','S','E','P',src)(SX,S,E,SX.p);
if(document.documentElement.dataset.theme!=='light')throw new Error('with nothing saved the theme must be light, because that is what this product ships as; a dark phone must not decide for someone who never opened Settings. got '+document.documentElement.dataset.theme);
const t=SX.lv22.tiles(S.members[0]);
if(!/6,420/.test(t)||!/64% of goal/.test(t))throw new Error('steps tile: '+t.slice(0,200));
if(!/142\/91/.test(t)||!/high · discuss with your doctor/.test(t))throw new Error('bp tile');
if(!/>72<small>bpm/.test(t))throw new Error('hr tile');
const w=SX.lv22.week(S.members[0]);if(!/1 of 7 days with readings/.test(w))throw new Error('week: '+w);
if(!/<svg/.test(SX.ico('home')))throw new Error('icon');
console.log('ok');
"""
    r = subprocess.run(["node", "-e", js, "--", str(ROOT / "web" / "index.html")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr
