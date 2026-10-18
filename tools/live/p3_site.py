"""Landing page, round 5: name as on Aadhaar, email and mobile both required and both verified at sign-up."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "site" / "index.html"
s = F.read_text(encoding="utf-8")
if "<!--live-p3-->" in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


one('<div class="fld"><label for="un">Full name</label><div class="inp"><input id="un" autocomplete="name" required maxlength="80"></div></div>',
    '<div class="fld"><label for="un">Full name <small class="mute">as on Aadhaar</small></label><div class="inp"><input id="un" autocomplete="name" required maxlength="80" placeholder="Exactly as printed on your Aadhaar"></div></div>')
one('<div class="fld"><label for="ue">Email</label><div class="inp"><input id="ue" type="email" autocomplete="email" inputmode="email" placeholder="you@example.com"></div></div>',
    '<div class="fld"><label for="ue">Email</label><div class="inp"><input id="ue" type="email" autocomplete="email" inputmode="email" placeholder="you@example.com" required></div></div>')
# client-side: email is required
one("if(B.email&&!/^[^@\\s]+@[^@\\s]+\\.[a-z]{2,}$/i.test(B.email)){say('That email address does not look right.');$('#ue').focus();return}",
    "if(!/^[^@\\s]+@[^@\\s]+\\.[a-z]{2,}$/i.test(B.email)){say(B.email?'That email address does not look right.':'Please enter your email address.');$('#ue').focus();return}")
# after the first code: if the server sent a second code (mobile), ask for it before entering the app
one("const finish=async(r,offer=true)=>{clearAuthState();ME=r.user;",
    "const finish=async(r,offer=true)=>{clearAuthState();ME=r.user;if(r.verifyNext&&r.verifyNext.flow){flow=r.verifyNext.flow;codeKind='second';lastId=r.verifyNext.channel;const h=r.verifyNext.channel==='phone'?'Verify your mobile':'Verify your email',sub=`One more step. Enter the 6-digit code we sent to ${r.verifyNext.sentTo}.`;codeView(h,sub);saveAuthState(h,sub);demo(r.verifyNext);return}")
one(" try{if(codeKind==='signup'){finish(await THT.api('/signup/verify',{flow,code:c}))}",
    " try{if(codeKind==='signup'){finish(await THT.api('/signup/verify',{flow,code:c}))}\n  else if(codeKind==='second'){await THT.api('/contact/verify',{flow,code:c});finish({user:ME||(await THT.api('/me')).user})}")
# resend for the second code; back from it goes to the app (the account already exists)
one("async function resend(){hush();try{if(codeKind==='signup'){",
    "async function resend(){hush();try{if(codeKind==='second'){const me=ME||(await THT.api('/me')).user;const r=await THT.api('/contact/start',{value:lastId==='phone'?me.phone:me.email});flow=r.flow;demo(r);const h=$('#codeH').textContent,sub='We sent a new code to '+r.sentTo+'.';codeView(h,sub);saveAuthState(h,sub)}else if(codeKind==='signup'){")
one("$('#codeBack').onclick=()=>{clearAuthState();show(codeKind==='signup'?'signup':codeKind==='reset'?'reset':'signin')};",
    "$('#codeBack').onclick=()=>{clearAuthState();if(codeKind==='second'){location.href=NEXT;return}show(codeKind==='signup'?'signup':codeKind==='reset'?'reset':'signin')};")
one("function restoreAuthState(){try{const s=JSON.parse(sessionStorage.getItem(AS_KEY));if(s&&s.flow&&s.codeKind&&Date.now()-s.t<10*60*1000){flow=s.flow;codeKind=s.codeKind;lastId=s.lastId;open(codeKind==='signup'?'signup':codeKind==='reset'?'reset':'signin');",
    "function restoreAuthState(){try{const s=JSON.parse(sessionStorage.getItem(AS_KEY));if(s&&s.flow&&s.codeKind&&Date.now()-s.t<10*60*1000){flow=s.flow;codeKind=s.codeKind;lastId=s.lastId;open(codeKind==='signup'||codeKind==='second'?'signup':codeKind==='reset'?'reset':'signin');")
s = s.replace("<!--live-p2-->", "<!--live-p2-->\n<!--live-p3-->", 1)
F.write_text(s, encoding="utf-8")
print("landing patched (round 5)")
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
