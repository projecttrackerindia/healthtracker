"""Round 15 patch: splash + in-app sign-in, health score, consented summary to the doctor, pre-auth helper."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p14*/"
s = W.read_text(encoding="utf-8")
if "/*live-p13*/" not in s:
    sys.exit("apply p13 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# the family's consented summary goes to the doctor as soon as both sides are in the room
one("if(msg.type==='hello'){c.ice=msg;c.peer=msg.peerPresent;ensurePC();render();return}", "if(msg.type==='hello'){c.ice=msg;c.peer=msg.peerPresent;ensurePC();render();if(msg.peerPresent&&SX.shareCtx)setTimeout(()=>SX.shareCtx(c),600);return}")
one("if(msg.type==='peer'){c.peer=msg.present;if(!msg.present&&c.connected){c.connected=false;toast(P('The doctor left the call'));}render();return}", "if(msg.type==='peer'){c.peer=msg.present;if(!msg.present&&c.connected){c.connected=false;toast(P('The doctor left the call'));}if(msg.present&&SX.shareCtx)setTimeout(()=>SX.shareCtx(c),600);render();return}")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
LOGO = '<svg viewBox="0 0 64 64" width="96" height="96" aria-hidden="true"><rect width="64" height="64" rx="16" fill="#2F5BFF"/><path d="M21.5 15a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4v34a4 4 0 0 1-4 4h-3a4 4 0 0 1-4-4V37.5H13a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h8.5z" fill="#fff"/><path d="M32 32h5l3.2-8 4.6 16 3.2-8h0.4" fill="none" stroke="#fff" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="55.2" cy="32" r="3.3" fill="#fff"/></svg>'
# the splash is static markup at the top of <body>, so the logo shows while the rest of the page still parses
SPLASH = ('<div class="lv15-splash" id="lv15s"><div class="lv15-sl">' + LOGO + '<b>Urban <span>Health</span></b><small>Your family’s health, in one living view.</small></div><div class="lv15-sdot"><i></i><i></i><i></i></div></div>'
          '<script>(function(){var s=document.getElementById("lv15s");s.dataset.t=Date.now();try{if(sessionStorage.getItem("tht.splashed")==="1"||!matchMedia("(max-width:720px)").matches)s.style.display="none"}catch(e){}})();</script>')
s = s.replace(HEAD, '<style id="live15-css">' + (HERE / "live15.css").read_text(encoding="utf-8") + "</style>\n" + HEAD + "\n" + SPLASH)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live15.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
