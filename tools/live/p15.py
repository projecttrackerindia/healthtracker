"""Round 16a patch: a locked app while nobody is signed in; a demo family only when someone asks for it."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p15*/"
s = W.read_text(encoding="utf-8")
if "/*live-p14*/" not in s:
    sys.exit("apply p14 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# live15's own gate stood down: live16 decides for every screen size, and there is no "browse without an account" any more
one("async function gate(){if(!wantsAppFlow())return;", "async function gate(){return;")
one("${native?'':`<button class=\"lv15-skip\" id=\"lv15skip\">${P('Browse without an account')}</button>`}",
    "<button class=\"lv15-skip\" id=\"lv15skip\">${P('See a demo with a sample family')}</button>")
one("if(sk)sk.onclick=()=>{try{sessionStorage.setItem('tht.skipauth','1')}catch(e){}closeAuth()};",
    "if(sk)sk.onclick=()=>{if(SX.demo)SX.demo.enter()};")
one("function closeAuth(){const el=document.getElementById('lv15auth');if(el)el.remove();document.body.classList.remove('lv15-locked')}",
    "function closeAuth(){const el=document.getElementById('lv15auth');if(el)el.remove();document.body.classList.remove('lv15-locked')}window.__lv16auth=authScreen;")
# the splash shows on every screen size now that the sign-in lives in the app
one('if(sessionStorage.getItem("tht.splashed")==="1"||!matchMedia("(max-width:720px)").matches)s.style.display="none"',
    'if(sessionStorage.getItem("tht.splashed")==="1")s.style.display="none"')
one("if(splash){if(!wantsAppFlow()||splashed){splash.remove();splash=null}", "if(splash){if(splashed){splash.remove();splash=null}")
# a passkey button on the in-app sign-in (the screen had password and one-time code only)
one("<button class=\"btn p lv15-main\">${P('Sign in')}</button><div class=\"lv15-alt\">",
    "<button class=\"btn p lv15-main\">${P('Sign in')}</button><button type=\"button\" class=\"btn s lv15-pk\" id=\"lv15pk\">${P('Sign in with a passkey')}</button><div class=\"lv15-alt\">")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live16-css">' + (HERE / "live16.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live16.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
