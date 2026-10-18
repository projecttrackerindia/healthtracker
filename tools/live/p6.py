"""Round 7 patch for web/index.html (applies on top of main): assistant tab, inbox, partner flows."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p6*/"
s = W.read_text(encoding="utf-8")
if "/*live-p5*/" not in s:
    sys.exit("apply p5 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# Home: the assistant is its own tab next to the 3D body; navigation remembers the page on <body>
one("nb=!(pg||hl||p==='dash'||p==='lab')", "nb=!(pg||hl||p==='dash'||p==='lab'||p==='assist')")
one("function go(p,opt={}){page=p;", "function go(p,opt={}){page=p;document.body.dataset.page=p;try{if(SX.inboxSeen)setTimeout(()=>SX.inboxSeen(p),0)}catch(e){}")
one("SX.extend('dash',{before(){return agentHTML(SX.me())}", "SX.extend('assist',{before(){return agentHTML(SX.me())}")
one("if(page!=='dash')go('dash');else render();", "if(page!=='assist')go('assist');else render();")
one('data-sx="agtab:today">${P(\'Today\')}', 'data-sx="agtab:today">${P(\'Insight\')}')
one("SX.extend('dash',{mounted(){const f=document.querySelector('.lv5-agent form.lv5-ask')", "SX.extend('assist',{mounted(){const f=document.querySelector('.lv5-agent form.lv5-ask')")
one("const PLACES={};let plSel=null;", "const PLACES={};window.__lv6places=PLACES;let plSel=null;")
# orders say who they are for and which prescriptions were shared
one("const rxDocs=m=>S.vault.filter(v=>v.m===m.id&&v.kind==='Prescription');", "const rxDocs=m=>S.vault.filter(v=>v.m===m.id&&v.kind==='Prescription');SX.rxSel=()=>chosen.rxsel;")
one("body:{store:s.id,kind:'medicine',items,address:addr,member:SX.me().name,rxShared:needsRx}",
    "body:{store:s.id,kind:'medicine',items,address:addr,member:SX.me().name,memberId:SX.me().id,rxShared:needsRx,rxDocs:[...new Set([...S.cart.map(c=>c.rxdoc),...Object.values((SX.rxSel&&SX.rxSel())||{})].filter(Boolean))]}")
one("body:{store:sel.id,kind:'lab',items:sel.lines.map(x=>({code:x.code})),address:S.addr||'',member:SX.me().",
    "body:{store:sel.id,kind:'lab',items:sel.lines.map(x=>({code:x.code})),memberId:SX.me().id,address:S.addr||'',member:SX.me().")
# feedback: the lab-finder belongs on Nearby labs, not on Lab results
one("SX.extend('tests',{after:labCTA});SX.extend('insights',{after:labCTA});", "SX.extend('nearlabs',{after:labCTA});")
# history moved to its own tab
one("SX.extend('appts',{after(){const m=SX.me(),all=((S.appts||{})[m.id]||[]),tm=SX.today(),past=", "SX.extend('appts_history_old',{after(){const m=SX.me(),all=((S.appts||{})[m.id]||[]),tm=SX.today(),past=")
# booking search filters the map list
one("const all=[...(d.partners||[]),...(d.places||[])].slice(0,24),sel=all.find(x=>x.id===plSel)||null;", "const all=[...(d.partners||[]),...(d.places||[])].filter(x=>!opt.filter||opt.filter(x)).slice(0,24),sel=all.find(x=>x.id===plSel)||null;")
one("placesHTML('hospital',P('Hospitals and clinics around you'),{partnerAct:'bookat',partnerCta:P('Book a visit')})", "placesHTML('hospital',P('Hospitals and clinics around you'),{partnerAct:'bookat',partnerCta:P('Book a visit'),filter:p=>!SX.bookFilter||SX.bookFilter(p)})")
# insurance cards: a clean face until opened — insurer, plan, valid till MM/YYYY
one(" const holder=f.holder||c.holder||'';\n return `<div class=\"lv2-card ${T.cls} ${opt.cls||''}\" data-cid=\"${c.id}\">",
    " const holder=f.holder||c.holder||'';\n if(!shown&&opt.flat&&c.type!=='abha'){const vt=f.valid_to?(window.SX&&SX.mmyy?SX.mmyy(f.valid_to):f.valid_to):'';return `<div class=\"lv2-card ${T.cls} lv2-min ${opt.cls||''}\" data-cid=\"${c.id}\"><div class=\"lv2-card-top\"><span class=\"lv2-card-t\"><i aria-hidden=\"true\">${T.ic}</i><b>${E(title)}</b></span><span class=\"lv2-card-k\">${E(T.k)}</span></div><div class=\"lv2-min-b\">${sub?`<small>${E(sub)}</small>`:''}${vt?`<b>${P('Valid till')} ${E(vt)}</b>`:''}</div></div>`}\n return `<div class=\"lv2-card ${T.cls} ${opt.cls||''}\" data-cid=\"${c.id}\">")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live7-css">' + (HERE / "live7.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live7.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
