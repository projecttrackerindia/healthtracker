"""Round 30 patch: the launch period — every feature free until 31 March 2027, no plan to buy."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p30*/"
s = W.read_text(encoding="utf-8")
if "/*live-p29*/" not in s:
    sys.exit("apply p29 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str, what: str) -> None:
    global s
    if s.count(old) != 1:
        sys.exit(f"{what}: anchor found {s.count(old)}×")
    s = s.replace(old, new)


# the page's own description of the Plan tab stops promising paid tiers
one("""SX.reg('plan',{head:()=>[P('Plan'),P('Free for the whole family. Paid plans add AI analysis, tracking and priority partners.')],""",
    """SX.reg('plan',{head:()=>[P('Plan'),P('What your family gets, and what it costs.')],""", "plan head")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live30-css">' + (HERE / "live30.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live30.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
