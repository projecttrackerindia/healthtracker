"""Round 28 patch: Hindi and Telugu — inline core + phrase table."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p28*/"
s = W.read_text(encoding="utf-8")
if "/*live-p27*/" not in s:
    sys.exit("apply p27 first")
if MARK in s:
    sys.exit("already applied")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live28-css">' + (HERE / "live28.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
import json
sys.path.insert(0, str(ROOT / "tools" / "i18n"))
from core import CORE  # noqa: E402
layer = (HERE / "live28.js").read_text(encoding="utf-8").replace("/*LV28_CORE*/{}/*/LV28_CORE*/", json.dumps(CORE, ensure_ascii=False))
s = s.replace(BOOT, MARK + "\n" + layer + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
