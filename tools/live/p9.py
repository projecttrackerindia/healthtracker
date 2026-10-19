"""Round 10 patch for web/index.html (applies on top of main): Android bridge, video consults, acting assistant, weekly
report, Medical ID QR, medicine safety, policy reading, roles, export, UPI payments, DigiLocker."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p9*/"
s = W.read_text(encoding="utf-8")
if "/*live-p8*/" not in s:
    sys.exit("apply p8 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# an Aadhaar card type (filled from DigiLocker)
one("other:{n:'Other card',k:'CARD',ic:'💳',cls:'oth'}", "aadhaar:{n:'Aadhaar',k:'AADHAAR',ic:'🪪',cls:'oth'},other:{n:'Other card',k:'CARD',ic:'💳',cls:'oth'}")
# card detail: policy terms under insurance cards, live ABHA linking under the ABHA card
one("  ${c.type==='abha'?`<p class=\"mute sm\">${P('ABHA (Ayushman Bharat Health Account) lets hospitals",
    "  ${(c.type==='insurance'||c.type==='corporate')&&SX.policyHTML?SX.policyHTML(c):''}${c.type==='abha'&&SX.abhaHTML?SX.abhaHTML():''}\n  ${c.type==='abha'?`<p class=\"mute sm\">${P('ABHA (Ayushman Bharat Health Account) lets hospitals")
# assistant answers carry commands; the chat shows them as buttons
one("(S.ask[m.id]=S.ask[m.id]||[]).push({q,a:r.answer,src:r.sources,act:r.actions,urgent:r.urgent,focus:r.focus||[],t:Date.now()});",
    "(S.ask[m.id]=S.ask[m.id]||[]).push({q,a:r.answer,src:r.sources,act:r.actions,urgent:r.urgent,focus:r.focus||[],cmd:r.commands||[],t:Date.now()});")
one("${a.act&&a.act.length?`<ul>${a.act.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:''}<small>${E(fmtTime(a.t))}</small></div>`).join('')).join(''):",
    "${a.act&&a.act.length?`<ul>${a.act.map(x=>`<li>${E(x)}</li>`).join('')}</ul>`:''}${SX.cmdHTML?SX.cmdHTML(a):''}<small>${E(fmtTime(a.t))}</small></div>`).join('')).join(''):")
# every server notice is announced to later layers (prescriptions into the vault, consult prompts)
one("function absorb(n){const ref=n.ref||{};", "function absorb(n){const ref=n.ref||{};try{document.dispatchEvent(new CustomEvent('tht:notice',{detail:n}))}catch(e){}")
# saved addresses: picker in the pharmacy checkout and in home-collection lab bookings; orders carry the structured address
one("  <label class=\"full sx-h4\" style=\"display:block\">Delivery address<input id=\"caddr\" maxlength=\"160\"",
    "  ${SX.addrPick?SX.addrPick():''}<label class=\"full sx-h4\" style=\"display:block\">Delivery address<input id=\"caddr\" maxlength=\"160\"")
one(" ${LABQ.home&&sel.home?`<label class=\"sx-h4\" style=\"display:block\">${P('Collection slot')}",
    " ${LABQ.home&&sel.home&&SX.addrPick?`<p class=\"sx-h4\" style=\"margin:8px 0 2px\">${P('Collection address')}</p>`+SX.addrPick():''}${LABQ.home&&sel.home?`<label class=\"sx-h4\" style=\"display:block\">${P('Collection slot')}")
one("body:{store:s.id,kind:'medicine',items,address:addr,member:SX.me().name,memberId:SX.me().id,",
    "body:{store:s.id,kind:'medicine',items,address:addr,addr:SX.addrFor?SX.addrFor(addr):null,member:SX.me().name,memberId:SX.me().id,")
one("items:sel.lines.map(x=>({code:x.code})),memberId:SX.me().id,address:S.addr||'',member:SX.me().name,",
    "items:sel.lines.map(x=>({code:x.code})),memberId:SX.me().id,address:(LABQ.home&&sel.home&&SX.addrSel&&SX.addrSel()?SX.addrFmt(SX.addrSel()):S.addr)||'',addr:LABQ.home&&sel.home&&SX.addrSel?SX.addrSel():null,member:SX.me().name,")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live10-css">' + (HERE / "live10.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live10.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
