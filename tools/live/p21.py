"""Round 21 patch: SOS that acts (countdown → call + alert + live page), email on emergency contacts."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p21*/"
s = W.read_text(encoding="utf-8")
if "/*live-p20*/" not in s:
    sys.exit("apply p20 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# emergency contacts carry an email: the server mails them the instant SOS is pressed
one('''<label class="full">Mobile number<input name="ph" inputmode="tel" placeholder="98765 43210 or +91 98765 43210" value="${E(ed?ed.ph:'')}" autocomplete="off"></label>''',
    '''<label class="full">Mobile number<input name="ph" inputmode="tel" placeholder="98765 43210 or +91 98765 43210" value="${E(ed?ed.ph:'')}" autocomplete="off"></label>
   <label class="full">Email <small class="mute">· gets the alert the moment SOS is pressed</small><input name="em" type="email" inputmode="email" placeholder="name@example.com" value="${E(ed?ed.em||'':'')}" autocomplete="off"></label>''')
one('''const m=SX.me(),cs=contactsOf(m.id),fd=new FormData(f),n=String(fd.get('n')||'').trim().slice(0,40),rel=String(fd.get('rel')||'Other'),raw=String(fd.get('ph')||'').trim();''',
    '''const m=SX.me(),cs=contactsOf(m.id),fd=new FormData(f),n=String(fd.get('n')||'').trim().slice(0,40),rel=String(fd.get('rel')||'Other'),raw=String(fd.get('ph')||'').trim(),em=String(fd.get('em')||'').trim().toLowerCase().slice(0,160);
 if(em&&!/^[^@\\s]+@[^@\\s]+\\.[a-z]{2,}$/.test(em)){toast('That email does not look right');return}''')
one('''if(editC){const c=cs.find(x=>x.id===editC);if(c){c.n=n;c.rel=rel;c.ph=ph}editC=null;toast('Contact updated')}else{cs.push({id:uid('c'),n,rel,ph,notify:true});toast('Contact added')}''',
    '''if(editC){const c=cs.find(x=>x.id===editC);if(c){c.n=n;c.rel=rel;c.ph=ph;c.em=em}editC=null;toast('Contact updated')}else{cs.push({id:uid('c'),n,rel,ph,em,notify:true});toast('Contact added')}''')
one('''<small>${c.ph?`<a href="tel:${E(c.ph)}">${E(phoneShow(c.ph))}</a>`:'<span style="color:var(--amber)">No phone number yet</span>'}</small>''',
    '''<small>${c.ph?`<a href="tel:${E(c.ph)}">${E(phoneShow(c.ph))}</a>`:'<span style="color:var(--amber)">No phone number yet</span>'}${c.em?` · ${E(c.em)}`:''}</small>''')
# the Safety page's "Open SOS" copy: it now acts, so say so
s = s.replace("Gets your location and Medical ID ready as a text message. Nothing is sent until you tap Send in your messaging app.",
              "Counts down from 3, then calls, shares your live location and tells everyone you chose — email and app alerts go out by themselves.")   # page copy + its phrase table
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live21-css">' + (HERE / "live21.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live21.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
