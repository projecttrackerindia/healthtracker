"""Round 35 patch: the map stops shaking, buttons stop folding, the test picker stops jumping."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p35*/"
s = W.read_text(encoding="utf-8")
if "/*live-p34*/" not in s:
    sys.exit("apply p34 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str, what: str) -> None:
    global s
    if s.count(old) != 1:
        sys.exit(f"{what}: anchor found {s.count(old)}x")
    s = s.replace(old, new)


# ---- the shake, half one: the label never blanks, so the sheet never changes height -------------------------
# Blanking to "Finding the address…" (2 lines) and back to a full address (3 lines) resized the sheet, which
# resized the map above it, which made Google Maps fire `idle`, which started another geocode. Keep the last
# address on screen and mark it busy instead.
one("const reverse=async()=>{const at={...cur};info=null;show();let r=null;",
    "const reverse=async()=>{const at={...cur};const box=document.querySelector('.lv29-sheet .lv29-addr');"
    "if(box)box.classList.add('busy');if(!info)show();let r=null;",
    "reverse: keep the last address")
one("if(at.lat!==cur.lat||at.lng!==cur.lng)return;info=r||{ok:false,label:''};show()};",
    "if(at.lat!==cur.lat||at.lng!==cur.lng)return;info=r||{ok:false,label:''};"
    "lastFix={lat:at.lat,lng:at.lng};if(box)box.classList.remove('busy');show()};",
    "reverse: remember what was resolved")

# ---- the shake, half two: `idle` only counts when the pin has really moved ----------------------------------
# A resize fires `idle` with the same centre. Six decimal places is ~0.1 m, so an exact compare never matches;
# 15 m is below the resolution of a street address and well above any resize jitter.
one("map.addListener('dragstart',()=>pm.classList.add('drag'));map.addListener('idle',()=>{pm.classList.remove('drag');const c=map.getCenter();if(!c)return;cur={lat:+c.lat().toFixed(6),lng:+c.lng().toFixed(6)};moved()})",
    "map.addListener('dragstart',()=>pm.classList.add('drag'));map.addListener('idle',()=>{pm.classList.remove('drag');const c=map.getCenter();if(!c)return;"
    "cur={lat:+c.lat().toFixed(6),lng:+c.lng().toFixed(6)};"
    "if(lastFix&&Math.hypot((cur.lat-lastFix.lat)*111320,(cur.lng-lastFix.lng)*105000)<15)return;"   # a resize is not a move
    "moved()})",
    "idle: ignore a centre that has not moved")
one("let cur=opt.center||SX.loc.get()||null,z=cur?16:5,info=null,map=null,drag=null,tdeb=null,sdeb=null,done=false,label=opt.label||'home';",
    "let cur=opt.center||SX.loc.get()||null,z=cur?16:5,info=null,map=null,drag=null,tdeb=null,sdeb=null,done=false,label=opt.label||'home',lastFix=null;",
    "mapPick: lastFix state")

# ---- the test picker must not rebuild the list under the finger ---------------------------------------------
# paint() replaced the sheet's whole innerHTML on every tap, so the list scrolled back to the top each time a
# test was selected. Toggle the chosen rows in place and rewrite only the two things that actually changed.
one("const paint=()=>{const w=document.querySelector('.sx-modal .sx-sheet');if(!w)return;w.innerHTML=body();wire()};",
    "const paint=()=>{const w=document.querySelector('.sx-modal .sx-sheet');if(!w)return;"
    "w.querySelectorAll('.lv34-t').forEach(b=>b.classList.toggle('on',sel.includes(b.dataset.t)));"
    "const sum=w.querySelector('.lv34-sum');"
    "if(sum)sum.innerHTML=`<b>${sel.length} ${sel.length===1?P('test'):P('tests')}</b><span>${P('about')} ${money(T.filter(t=>sel.includes(t.code)).reduce((a,t)=>a+t.typical,0))}</span>`;"
    "['lv34wa','lv34save'].forEach(id=>{const b=document.getElementById(id);if(b)b.disabled=!sel.length})};",
    "picker: toggle in place")


# ---- dark mode was switched off for everybody ---------------------------------------------------------------
# Two places wrote data-theme="light" whenever the saved value was not exactly "dark". The dark rules are
# guarded by :root:not([data-theme="light"]), so an explicit "light" overrides the phone's own setting: a
# device in dark mode still got the light app, and the "System" button in Settings did nothing because a
# MutationObserver put the attribute straight back. No attribute at all is what lets the phone decide.
one('<script>try{document.documentElement.dataset.theme=localStorage.getItem("tht.theme")==="dark"?"dark":"light"}catch(e){document.documentElement.dataset.theme="light"}</script>',
    '<script>try{var _t=localStorage.getItem("tht.theme");'
    'if(_t==="dark"||_t==="light")document.documentElement.dataset.theme=_t;'
    'else document.documentElement.removeAttribute("data-theme")}catch(e){}</script>',
    "theme boot: follow the phone")

one("{const r=document.documentElement,saved=ls('tht.theme');r.dataset.theme=saved==='dark'?'dark':'light';\n"
    " new MutationObserver(()=>{const t=r.dataset.theme;if(t==='dark'||t==='light')ls('tht.theme',t);else{r.dataset.theme='light';ls('tht.theme','light')}}).observe(r,{attributes:true,attributeFilter:['data-theme']})}",
    "{const r=document.documentElement,saved=ls('tht.theme');\n"
    " if(saved==='dark'||saved==='light')r.dataset.theme=saved;else r.removeAttribute('data-theme');\n"
    " new MutationObserver(()=>{const t=r.dataset.theme;if(t==='dark'||t==='light')ls('tht.theme',t);else ls('tht.theme','system')}).observe(r,{attributes:true,attributeFilter:['data-theme']})}",
    "theme persistence: System is a real choice")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live35-css">' + (HERE / "live35.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live35.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
