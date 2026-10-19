"""Round 12 patch: Medical ID card, blood network, hospital-bag package, Devices keeps the 3D body, care icon."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p11*/"
s = W.read_text(encoding="utf-8")
if "/*live-p10*/" not in s:
    sys.exit("apply p10 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# Devices is a Home tab: keep the 3D body beside it like Today and Body
one("nb=!(pg||hl||p==='dash'||p==='lab'||p==='assist');", "nb=!(pg||hl||p==='dash'||p==='lab'||p==='assist'||p==='devices');")
# the UPI pay modal is reused by the shop
one("const subU=SX.act.sub;SX.act.sub=async a=>{", "SX.payModal=payModal;const subU=SX.act.sub;SX.act.sub=async a=>{")
# the hospital-bag package sits under the bag checklist on the birth plan
one("""${items.map(it=>`<label><input type="checkbox" ${pa('bag',encodeURIComponent(it))} ${LOG.bag.includes(it)?'checked':''}> ${it}</label>`).join('')}</div>`).join('')}</div>""",
    """${items.map(it=>`<label><input type="checkbox" ${pa('bag',encodeURIComponent(it))} ${LOG.bag.includes(it)?'checked':''}> ${it}</label>`).join('')}</div>`).join('')}</div>${SX.bagShopHTML?SX.bagShopHTML():''}""")
# a kinder Care icon: hands holding a heart
one("{k:'care',ic:'baby',tabs:['book','cycle','preg']}", "{k:'care',ic:'care',tabs:['book','cycle','preg']}")
one("I.shield='<path d=\"M12 3l7.5 2.8v5.6c0 4.4-3 8.2-7.5 9.6-4.5-1.4-7.5-5.2-7.5-9.6V5.8z\"/><path d=\"M12 8.2v4.6M12 15.8h.01\"/>';",
    "I.shield='<path d=\"M12 3l7.5 2.8v5.6c0 4.4-3 8.2-7.5 9.6-4.5-1.4-7.5-5.2-7.5-9.6V5.8z\"/><path d=\"M12 8.2v4.6M12 15.8h.01\"/>';I.care='<path d=\"M12 19.5s-5.5-3.6-5.5-7.6A2.75 2.75 0 0 1 12 9.6a2.75 2.75 0 0 1 5.5 2.3c0 4-5.5 7.6-5.5 7.6z\"/><path d=\"M4 14c-1.2-.9-2-2.2-2-3.7V6.5l2.6-1.6L7 6.3\"/><path d=\"M20 14c1.2-.9 2-2.2 2-3.7V6.5l-2.6-1.6L17 6.3\"/>';")
one("function pregNav(){const on=pregActive();CARE.ic=on?'preg':'baby';", "function pregNav(){const on=pregActive();CARE.ic=on?'preg':'care';")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live12-css">' + (HERE / "live12.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live12.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
