"""Round 5 patch for web/index.html (after p0..p3): one identity, health assistant, device readings, honest plans."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p4*/"
s = W.read_text(encoding="utf-8")
if "/*live-p3*/" not in s:
    sys.exit("apply p3 first")
if MARK in s:
    sys.exit("already applied")
HEAD = '</head>\n<body>'
if s.count(HEAD) != 1:
    sys.exit("head anchor")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# the plan page: no "demo billing" wording in front of users
one("P('Demo billing: plans activate instantly and no money is taken. Razorpay is enabled by the administrator for live payments.')",
    "P('Plans activate after payment. Prices include GST.')")
s = s.replace(HEAD, '<style id="live5-css">' + (HERE / "live5.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live5.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
