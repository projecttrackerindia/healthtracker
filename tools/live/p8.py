"""Round 9 patch for web/index.html (applies on top of main): production hygiene in the client (upload backoff),
pregnancy page tidy, pregnancy tabs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p8*/"
s = W.read_text(encoding="utf-8")
if "/*live-p7*/" not in s:
    sys.exit("apply p7 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# uploads that fail for a server-side reason back off (30 s, 1 min, 2 min … up to an hour) instead of retrying every few seconds
one("catch(e){if(e.status===413||e.status===415||e.status===507){delete upq[id];saveQ();if(e.status===507)toast(e.message)}return false}}",
    "catch(e){if(e.status===413||e.status===415||e.status===507){delete upq[id];saveQ();if(e.status===507)toast(e.message)}else{const q=upq[id]||(upq[id]={n:'',t:Date.now()});q.f=(q.f||0)+1;q.next=Date.now()+Math.min(36e5,3e4*Math.pow(2,q.f-1));saveQ()}return false}}")
one("async function drain(){if(uploading||!SX.user||!navigator.onLine)return;uploading=true;try{for(const id of Object.keys(upq)){if(S.cloud[id]){delete upq[id];continue}await upload(id)}saveQ()}finally{uploading=false}}",
    "async function drain(){if(uploading||!SX.user||!navigator.onLine)return;uploading=true;try{for(const id of Object.keys(upq)){if(S.cloud[id]){delete upq[id];continue}if(upq[id]&&upq[id].next&&upq[id].next>Date.now())continue;await upload(id)}saveQ()}finally{uploading=false}}")
# pregnancy page: no internal tabs (they are tabs in the bar), no trackers card, shorter lab intro, no scroll jump
one("const TABS=[['week','🗓️','Week'],['music','🎵','Music'],['well','🧘','Wellbeing'],['ben','🎁','Benefits']];", "const TABS=[];")
one(" <div class=\"card\"><div class=\"ptabs\" id=\"ptabs\" role=\"tablist\">${TABS.map(([k,e,n])=>`<button role=\"tab\" class=\"${PS.tab===k?'on':''}\" ${pa('tab',k)}>${e} ${n}</button>`).join('')}</div><div id=\"ptab\">${(T[PS.tab]||T.week)()}</div></div>`};",
    " <div class=\"card\"><div class=\"ptabs\" id=\"ptabs\" hidden></div></div>`};")
one("AFTER.preg=()=>{const f=AT[PS.tab];if(f)f();const t=$('#ptabs .on');if(t)t.scrollIntoView({block:'nearest',inline:'center'})};", "AFTER.preg=()=>{};")
one("<p>Rotate, zoom toward the cursor, or select a structure to bring it into focus. All original week, nutrition, hydration, wellbeing and birth tools remain below.</p>",
    "<p>Rotate, zoom toward the cursor, or select a structure to bring it into focus.</p>")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live9-css">' + (HERE / "live9.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live9.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
