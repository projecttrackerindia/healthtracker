"""Round 13 patch: phone-first shell."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p12*/"
s = W.read_text(encoding="utf-8")
if "/*live-p11*/" not in s:
    sys.exit("apply p11 first")
if MARK in s:
    sys.exit("already applied")
def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# every map goes through Google when the key is set
one("function mapHTML(center,items,opt={}){const z=opt.zoom||13,", "function mapHTML(center,items,opt={}){if(SX.gmapHTML&&SX.gmapsOn&&SX.gmapsOn())return SX.gmapHTML(center,items,opt);const z=opt.zoom||13,")
# (these two live in layers already baked into the file; the same edits were made in live10.js / live12.js for fresh builds)
one("['name','phone','line1','line2','landmark','area','city','state','pin'].forEach(k=>o[k]=String(fd.get(k)||'').trim());if(geo){o.lat=geo.lat;o.lng=geo.lng}",
    "['name','phone','line1','line2','landmark','area','city','state','pin'].forEach(k=>o[k]=String(fd.get(k)||'').trim());if(e.target.dataset.lat){geo={lat:+e.target.dataset.lat,lng:+e.target.dataset.lng}}if(geo){o.lat=geo.lat;o.lng=geo.lng}")
one("{h:200,zoom:Math.max(10,Math.min(14,Math.round(13-Math.log2(1+Math.hypot((S.net.geo.lat-q.lat)*111,(S.net.geo.lng-q.lng)*105))))),act:'bropen'}):''}",
    "{h:200,zoom:Math.max(10,Math.min(14,Math.round(13-Math.log2(1+Math.hypot((S.net.geo.lat-q.lat)*111,(S.net.geo.lng-q.lng)*105))))),act:'bropen',route:{from:{lat:S.net.geo.lat,lng:S.net.geo.lng},to:{lat:q.lat,lng:q.lng}}})+`<small class=\"mute lv13-eta\"></small>`:''}")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live13-css">' + (HERE / "live13.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live13.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
