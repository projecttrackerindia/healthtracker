"""Round 26 patch: backed-up card and the copy by email."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p26*/"
s = W.read_text(encoding="utf-8")
if "/*live-p25*/" not in s:
    sys.exit("apply p25 first")
if MARK in s:
    sys.exit("already applied")
# the My-data page said there was no server copy; there is (encrypted record + 30 days of history)
old_txt = "There is no Urban Health server account in this build: nothing here leaves your device unless you export or share it."
if s.count(old_txt) != 1:
    sys.exit("data page anchor")
s = s.replace(old_txt, "When you are signed in, the record is also kept encrypted on our servers (with 30 days of history) so every family member sees the same thing; documents live in the vault. Nothing is shared unless you share it.")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live26-css">' + (HERE / "live26.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live26.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
