"""Round 17 patch: phone shell v2 — app bar with the page title, pinned Health Card with SOS, sub-tabs in the bar, keyboard-aware assistant, viewer-first Body and Heart Lab."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p17*/"
s = W.read_text(encoding="utf-8")
if "/*live-p16*/" not in s:
    sys.exit("apply p16 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# swipe between sub-tabs works on the strip wherever it lives (it moves into the app bar on phones)
one("const tabs=[...document.querySelectorAll('#page>.sx-tabs button')].filter(b=>b.offsetParent);",
    "const tabs=[...document.querySelectorAll('#lv17tabs .sx-tabs button,#page>.sx-tabs button')].filter(b=>b.offsetParent);")
# pull-to-refresh showed a 'Refreshing…' pill on ordinary iOS scrolls; sync is automatic, the gesture goes
one("if(dy>90&&!pulling){pulling=1;", "if(false){pulling=1;")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live17-css">' + (HERE / "live17.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live17.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
