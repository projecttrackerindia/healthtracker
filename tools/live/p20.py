"""Round 20 patch: Firebase Phone Authentication on the in-app sign-in; the in-app two-step verify sent the wrong field name."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p20*/"
s = W.read_text(encoding="utf-8")
if "/*live-p19*/" not in s:
    sys.exit("apply p19 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# every start answer passes through SX.fbArm; every verify body through SX.fbBody (live15 → live20)
one("const r=await A('/otp/start',{id});flow=r.flow;", "const r=await SX.fbArm(await A('/otp/start',{id}));flow=r.flow;")
one("const r=await A('/password/login',{id:fd.get('id').trim(),password:fd.get('pw')});if(r.step){",
    "const r=await A('/password/login',{id:fd.get('id').trim(),password:fd.get('pw')});if(r.step){await SX.fbArm(r);")
one("password:fd.get('pw'),terms:!!fd.get('terms')});flow=r.flow;", "password:fd.get('pw'),terms:!!fd.get('terms')});await SX.fbArm(r);flow=r.flow;")
one("if(r.verifyNext&&r.verifyNext.flow){flow=r.verifyNext.flow;", "if(r.verifyNext&&r.verifyNext.flow){await SX.fbArm(r.verifyNext);flow=r.verifyNext.flow;")
one("r=await A('/signup/verify',{flow,code});", "r=await A('/signup/verify',await SX.fbBody(flow,code));")
one("await A('/contact/verify',{flow,code});", "await A('/contact/verify',await SX.fbBody(flow,code));")
one("await A('/step/verify',{step:flow,code});", "await A('/step/verify',await SX.fbBody(flow,code));")   # was {step:…}: the server reads `flow`
one("r=await A('/otp/verify',{flow,code});", "r=await A('/otp/verify',await SX.fbBody(flow,code));")
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live20.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
