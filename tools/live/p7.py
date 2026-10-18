"""Round 8 patch for web/index.html (applies on top of main): assistant ↔ 3D focus, uniform cards, pregnancy as tabs,
pregnancy data into the family record."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p7*/"
s = W.read_text(encoding="utf-8")
if "/*live-p6*/" not in s:
    sys.exit("apply p6 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# pregnancy logs used to live only in this browser (localStorage); now they ride in the family record too
one("const st={get(k,d){try{const v=localStorage.getItem('dk-preg-'+k);return v?JSON.parse(v):d}catch(e){return d}},set(k,v){try{localStorage.setItem('dk-preg-'+k,JSON.stringify(v))}catch(e){}}};",
    "const st={get(k,d){try{try{const p=window.SX&&SX.S&&SX.S.pregst;if(p&&p[k]!==undefined)return p[k]}catch(_){}const v=localStorage.getItem('dk-preg-'+k);return v?JSON.parse(v):d}catch(e){return d}},set(k,v){try{localStorage.setItem('dk-preg-'+k,JSON.stringify(v))}catch(e){}try{if(window.SX&&SX.S){SX.S.pregst=SX.S.pregst||{};SX.S.pregst[k]=v;if(SX.save)SX.save()}}catch(e){}}};")
one("const saveLog=()=>st.set('log',LOG),saveProf=()=>st.set('prof',PROF);",
    "const saveLog=()=>st.set('log',LOG),saveProf=()=>st.set('prof',PROF);window.__preg={PS,LOG,PROF,ga,save:()=>saveLog(),T:null,AT:null};")
one("const T={};const AT={};", "const T={};const AT={};window.__preg.T=T;window.__preg.AT=AT;")
# the module's actions re-render the new tab pages too
one(" if(page==='preg'){render();if(toolsFocus){", " if(window.__pregPages&&__pregPages.has(page)){render();return}if(page==='preg'){render();if(toolsFocus){")
one("case'kickStart':PS.kick={n:0,s:Date.now()};break;", "case'kickStart':PS.kick={n:0,s:Date.now()};break;\n case'kickReset':PS.kick=null;break;")
# the Pregnancy page keeps the week guide, music, wellbeing and benefits; the trackers have their own tabs
one("const TABS=[['week','🗓️','Week'],['food','🥗','Food'],['water','💧','Water'],['music','🎵','Music'],['health','🩺','Health'],['tools','🧰','Tools'],['well','🧘','Wellbeing'],['birth','👶','Birth'],['ben','🎁','Benefits']];",
    "const TABS=[['week','🗓️','Week'],['music','🎵','Music'],['well','🧘','Wellbeing'],['ben','🎁','Benefits']];")
# the assistant remembers which body areas an answer or a report was about
one("(S.ask[m.id]=S.ask[m.id]||[]).push({q,a:r.answer,src:r.sources,act:r.actions,urgent:r.urgent,t:Date.now()});",
    "(S.ask[m.id]=S.ask[m.id]||[]).push({q,a:r.answer,src:r.sources,act:r.actions,urgent:r.urgent,focus:r.focus||[],t:Date.now()});")
one("entry.doctor=!!(ai.tests_needed&&ai.tests_needed.length)||(ai.warnings||[]).length>0;entry.urgent=false;",
    "entry.doctor=!!(ai.tests_needed&&ai.tests_needed.length)||(ai.warnings||[]).length>0;entry.urgent=false;entry.focus=(ai.focus||[]).slice(0,3);")
# insurance face: the holder's name too
one('<div class="lv2-min-b">${sub?`<small>${E(sub)}</small>`:\'\'}', '<div class="lv2-min-b">${holder?`<div class="lv2-card-name">${E(holder)}</div>`:\'\'}${sub?`<small>${E(sub)}</small>`:\'\'}')
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live8-css">' + (HERE / "live8.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live8.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
