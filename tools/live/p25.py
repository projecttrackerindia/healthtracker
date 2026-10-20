"""Round 25 patch: doctor summary share links; the old "For the doctor" card is replaced."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p25*/"
s = W.read_text(encoding="utf-8")
if "/*live-p24*/" not in s:
    sys.exit("apply p24 first")
if MARK in s:
    sys.exit("already applied")
# the summary builder hands its HTML to a grabber when one is set (the share link needs the page, not a pop-up)
old_open = "const w=window.open('','_blank');if(!w){toast(P('Allow pop-ups to open the summary'));return}"
if s.count(old_open) != 1:
    sys.exit("summary anchor")
s = s.replace(old_open, "if(SX.__summaryGrab){SX.__summaryGrab(html);return}" + old_open)
# the old card is replaced by the new one (same place on Home)
old_card = """SX.extend('dash',{after(){const m=SX.me();return `<div class="card"><div class="hd"><h3>${P('For the doctor')}</h3></div><p class="mute sm" style="margin:0 0 10px">${P('One clean page: allergies, medicines, latest results, readings, insurance and contacts.')}</p><button class="btn s sm" data-sx="summary:${m.id}">🖨️ ${P('Doctor summary')}</button></div>`}});"""
if s.count(old_card) != 1:
    sys.exit("doctor card anchor")
s = s.replace(old_card, "")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live25-css">' + (HERE / "live25.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live25.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
