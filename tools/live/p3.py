"""Round 4 patch for web/index.html (after p0, p1, p2). Adds the fourth live layer and its styles; also the Share button
on vault rows is injected at runtime by the layer, so only the layer insertion is needed here."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p3*/"
s = W.read_text(encoding="utf-8")
if "/*live-p2*/" not in s:
    sys.exit("apply p2 first")
if MARK in s:
    sys.exit("already applied")
if s.count("</head>") != 1:
    sys.exit("head anchor")
def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# vault wording: documents sync for signed-in families
one("Files are stored in a private area of this browser, not on a server. Clearing site data removes them, so keep your originals.",
    "${window.SX&&SX.user?'Documents are encrypted and synced to your family (☁︎). Keep your paper originals.':'Files stay in a private area of this browser until you sign in; then they are encrypted and synced to your family.'}")
one('<span class="demo">ON THIS DEVICE</span>', '<span class="demo">${window.SX&&SX.user?\'SYNCED\':\'ON THIS DEVICE\'}</span>')
# offline: keep the signed-in state instead of showing "Sign in" when the network is down
one("catch(e){SX.user=null}paintAcct()", "catch(e){if(navigator.onLine)SX.user=null}paintAcct()")

s = s.replace("</head>", '<style id="live4-css">' + (HERE / "live4.css").read_text(encoding="utf-8") + "</style>\n</head>")
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live4.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
