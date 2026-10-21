"""Round 38 patch: who checked your prescription"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p38*/"
s = W.read_text(encoding="utf-8")
if "/*live-p37*/" not in s:
    sys.exit("apply p37 first")
if MARK in s:
    sys.exit("already applied")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live38-css">' + (HERE / "live38.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live38.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
