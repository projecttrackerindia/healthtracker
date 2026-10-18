"""Round 3 patch for web/index.html (after p0 and p1): family sync, cycle tracker, booking, Heart Lab gate, AI reader,
pregnancy trackers and wording. Every replacement must match exactly once or nothing is written."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p2*/"
s = W.read_text(encoding="utf-8")
if "/*live-p1*/" not in s:
    sys.exit("apply p1 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:100]!r}")
    s = s.replace(old, new)


# pregnancy hero: no "sample profile", a Home button instead of "Exit mode", booking goes to our Booking tab
one('<small class="kicker">🤰 PREGNANCY MODE · SAMPLE PROFILE</small>', '<small class="kicker">🤰 PREGNANCY</small>')
one('<button class="btn s sm" ${pa(\'exit\')}>Exit mode</button>', '<button class="btn s sm" ${pa(\'exit\')}>Home</button>')
one('<button class="chip" data-act="book:fk">📅 Book OB visit</button>', '<button class="chip" data-sx="tab:book">📅 Book a visit</button>')
# trackers strip between the hero and the tabs
one(""" <div class="card"><div class="ptabs" id="ptabs" role="tablist">""", """ ${window.SX&&SX.pregTrackers?SX.pregTrackers():''}
 <div class="card"><div class="ptabs" id="ptabs" role="tablist">""")

# the layer
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live3.js").read_text(encoding="utf-8") + "\n" + BOOT)
one("</head>", '<style id="live3-css">' + (HERE / "live3.css").read_text(encoding="utf-8") + "</style>\n</head>")

W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
