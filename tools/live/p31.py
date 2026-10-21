"""Round 31 patch: the shop comes first — Book a test, Order medicines, and every suggestion ends in a basket."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p31*/"
s = W.read_text(encoding="utf-8")
if "/*live-p30*/" not in s:
    sys.exit("apply p30 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str, what: str) -> None:
    global s
    if s.count(old) != 1:
        sys.exit(f"{what}: anchor found {s.count(old)}×")
    s = s.replace(old, new)


# 1. the price sheet can be opened with a lab already chosen
one("SX.act.labs=([codes])=>{LABQ={codes:String(codes||'').split('+').filter(Boolean),home:true,sel:'',slot:''};LABS=null;labSheet();loadLabs()};",
    "SX.act.labs=([codes,sel])=>{LABQ={codes:String(codes||'').split('+').filter(Boolean),home:true,sel:sel||'',slot:''};LABS=null;labSheet();loadLabs()};\n"
    "SX.labOpen=(codes,sel)=>SX.act.labs([Array.isArray(codes)?codes.join('+'):codes,sel]);", "lab sheet")
# 2. the checks-due engine and the medicine catalogue become readable from a layer
one("SX.act.sugbook=([id])=>{const m=SX.me(),s=suggestions(m).find(x=>x.id===id);if(!s)return;bookPre={sp:s.sp,why:s.t};go('appts')};",
    "SX.act.sugbook=([id])=>{const m=SX.me(),s=suggestions(m).find(x=>x.id===id);if(!s)return;bookPre={sp:s.sp,why:s.t};go('appts')};\n"
    "SX.suggestions=suggestions;", "suggestions export")
one("SX.act.refill=([id])=>{const x=meds(SX.me()).find(a=>a.id===id);if(!x)return;fQ=x.n;fCat='All';go('finder')};",
    "SX.act.refill=([id])=>{const x=meds(SX.me()).find(a=>a.id===id);if(!x)return;fQ=x.n;fCat='All';go('finder')};\n"
    "SX.medCatalog=()=>C;", "catalogue export")
# 3. the map of nearby labs is reusable on the new page
one("SX.act.labgo=()=>{go('tests')};", "SX.placesHTML=placesHTML;SX.act.labgo=()=>{go('tests')};", "places export")
# 4. the price sheet only quotes a typical price when there is one to quote
one("""${L.approx?P('Showing')+' '+E(L.city)+' · '+P('typical price for these tests'):E(L.city)+' · '+P('typical price for these tests')} \u2248 ${money(L.labs[0]?L.labs[0].typical:0)}""",
    """${L.approx?P('Showing')+' '+E(L.city):E(L.city)}${L.labs[0]&&L.labs[0].typical?' \u00b7 '+P('typical price for these tests')+' \u2248 '+money(L.labs[0].typical):''}""", "typical price")

# 5. signing out lands on the sign-in screen, not the marketing page (the app is where you were)
one("SX.act.signout=async()=>{try{await loadAuthJs();await THT.api('/logout',{})}catch(e){}location.href='/'};",
    "SX.act.signout=async()=>{try{await loadAuthJs();await THT.api('/logout',{})}catch(e){}location.href='/signin'};", "sign out")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live31-css">' + (HERE / "live31.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live31.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
