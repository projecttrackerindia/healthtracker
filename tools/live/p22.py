"""Round 22 patch: the phone design system (light first, icon set, app bar, floating tab bar, Home tiles, quick add, assistant hero)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p22*/"
s = W.read_text(encoding="utf-8")
if "/*live-p21*/" not in s:
    sys.exit("apply p21 first")
if MARK in s:
    sys.exit("already applied")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
# light is the default before the first paint (no flash of dark); the display font loads in parallel
s = s.replace(HEAD, '<script>try{document.documentElement.dataset.theme=localStorage.getItem("tht.theme")==="dark"?"dark":"light"}catch(e){document.documentElement.dataset.theme="light"}</script>\n'
                    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap">\n'
                    '<style id="live22-css">' + (HERE / "live22.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live22.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
