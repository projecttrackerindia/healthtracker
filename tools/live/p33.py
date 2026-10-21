"""Round 33 patch: the Heart Lab studio, Today's dashboard cards, and an assistant that is a chat first."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p33*/"
s = W.read_text(encoding="utf-8")
if "/*live-p32*/" not in s:
    sys.exit("apply p32 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str, what: str) -> None:
    global s
    if s.count(old) != 1:
        sys.exit(f"{what}: anchor found {s.count(old)}×")
    s = s.replace(old, new)


# the heart module hands out its renderer, scene and materials so a layer can light it properly
one("state:()=>ST,setCor:on=>{UI.cor=on;applyAtlas()}};",
    "state:()=>ST,setCor:on=>{UI.cor=on;applyAtlas()},gfx:()=>({THREE,R,S,cam,G,myo,valM,artM,veinM})};", "heart gfx")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live33-css">' + (HERE / "live33.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live33.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
