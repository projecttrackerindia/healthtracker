"""Passkey wording and flow on phones: Face ID / fingerprint language, no browser QR sheet when the account has no passkey yet."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
MARK = "/*live-p16*/"
s = W.read_text(encoding="utf-8")
if "/*live-p15*/" not in s:
    sys.exit("apply p15 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# the button says what the phone will actually do
one("<button type=\"button\" class=\"btn s lv15-pk\" id=\"lv15pk\">${P('Sign in with a passkey')}</button>",
    "<button type=\"button\" class=\"btn s lv15-pk\" id=\"lv15pk\">${(window.__pkName||(()=>P('Sign in with a passkey')))()}</button>")
# explicit tap: ask for the account first, so the server can say whether a passkey exists; never fall into the browser's QR sheet
one(" else{if(pkAbort){pkAbort.abort();pkAbort=null}const id=f&&f.id?f.id.value.trim():'';await THT.passkey.signin({id})}",
    " else{if(pkAbort){pkAbort.abort();pkAbort=null}const id=f&&f.id?f.id.value.trim():'';if(id.length<5){pkErr(f,P('Enter your email or mobile first, then tap again.'));if(f&&f.id)f.id.focus();return}await THT.passkey.signin({id})}")
# the offer after sign-in uses the same words
one("SX.modal(`<h2>${P('Sign in faster next time')}</h2><p class=\"mute\">${P('Create a passkey and sign in with your fingerprint, face or screen lock — no password to type. It stays on this device and syncs through your platform account.')}</p>",
    "SX.modal(`<h2>${(window.__pkOfferTitle||(()=>P('Sign in faster next time')))()}</h2><p class=\"mute\">${P('No password to type: the phone checks it is you and signs you in. It stays on this device and syncs through your Apple or Google account.')}</p>")
one("<button class=\"btn p\" id=\"pkyes\">${P('Create a passkey')}</button>", "<button class=\"btn p\" id=\"pkyes\">${(window.__pkYes||(()=>P('Set it up')))()}</button>")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
JS = r"""<script>(function(){var ua=navigator.userAgent||'',ios=/iPhone|iPad|iPod/.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1),mac=/Macintosh/.test(ua),and=/Android/.test(ua),win=/Windows/.test(ua);
var how=ios?'Face ID or Touch ID':mac?'Touch ID':and?'fingerprint or face':win?'Windows Hello':'fingerprint, face or screen lock';
window.__pkHow=how;window.__pkName=function(){return 'Sign in with '+how};window.__pkOfferTitle=function(){return 'Use '+how+' next time'};window.__pkYes=function(){return 'Set up '+how}})();</script>"""
s = s.replace(HEAD, JS + "\n" + HEAD)
s = s.replace(MARK if MARK in s else "SX.boot();\n})();", MARK + "\nSX.boot();\n})();", 1)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
