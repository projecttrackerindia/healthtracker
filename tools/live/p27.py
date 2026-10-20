"""Round 27 patch: medicine interactions, checked on the device."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p27*/"
s = W.read_text(encoding="utf-8")
if "/*live-p26*/" not in s:
    sys.exit("apply p26 first")
if MARK in s:
    sys.exit("already applied")
# the medicine form: a hand-typed medicine (not in the catalogue) is checked against the list too
old_w = "const w=cat?SX.medWarn(m,cat):[];if(w.length&&!id)toast('Saved. '+w[0].t.slice(0,110))"
if s.count(old_w) != 1:
    sys.exit("medsave anchor")
s = s.replace(old_w, "const w=cat?SX.medWarn(m,cat):(SX.medInteract?SX.medInteract(m,o.n,id):[]);if(w.length)toast((id?'Saved. ':'Saved. ')+w[0].t.slice(0,140))")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live27-css">' + (HERE / "live27.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live27.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
