"""Round 6 patch for web/index.html. From round 6 on, web/index.html on main is the source: this applies on top of it
(no rebuild from an older base, because fixes were committed directly to the file in between)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p5*/"
s = W.read_text(encoding="utf-8")
if "/*live-p4*/" not in s:
    sys.exit("apply p4 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# adding a family member crashed: walletSel lives in the Cards layer, not in the family form's scope
one("if(!id){walletSel='hc:'+m.id;go('wallet')}}", "if(!id){if(SX.walletSelect)SX.walletSelect('hc:'+m.id);go('wallet')}}")
one("let walletSel='';", "let walletSel='';SX.walletSelect=v=>{walletSel=v};")
# care mode follows navigation
one("function go(p,opt={}){page=p;", "function go(p,opt={}){page=p;try{if(SX.careHook)setTimeout(SX.careHook,0)}catch(e){}")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live6-css">' + (HERE / "live6.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live6.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
