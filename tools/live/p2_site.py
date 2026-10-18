"""Landing page: family invitation links (/join/<token>) and the privacy wording for synced records."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "site" / "index.html"
s = F.read_text(encoding="utf-8")
if "<!--live-p2-->" in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# invitation: remember the token, show who invited, join after sign-up or sign-in, then open the app
one("let ME=null;const next=new URLSearchParams(location.search).get('next');const NEXT=next&&next.startsWith('/')&&!next.startsWith('//')?next:'/app';",
    "let ME=null;const next=new URLSearchParams(location.search).get('next');const NEXT=next&&next.startsWith('/')&&!next.startsWith('//')?next:'/app';\n"
    "const JOINM=/^\\/join\\/([A-Za-z0-9_-]{16,64})$/.exec(location.pathname);let INVITE=JOINM?JOINM[1]:null;try{if(INVITE)sessionStorage.setItem('tht-invite',INVITE);else INVITE=sessionStorage.getItem('tht-invite')}catch(e){}\n"
    "async function joinFamily(){if(!INVITE)return false;try{const r=await fetch('/api/v1/family/join',{method:'POST',headers:{'content-type':'application/json','x-tht':'1'},credentials:'same-origin',body:JSON.stringify({token:INVITE})});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Could not join');"
    "try{sessionStorage.removeItem('tht-invite');sessionStorage.setItem('tht-joined','1');localStorage.setItem('dk6.join','1');localStorage.removeItem('dk6.sync');if(j.householdKey){const s=JSON.parse(localStorage.getItem('dk6')||'null');if(s){s.key=j.householdKey;localStorage.setItem('dk6',JSON.stringify(s))}else localStorage.setItem('dk6',JSON.stringify({v:1,lang:'en',active:'m1',created:Date.now(),mig:2,key:j.householdKey,members:[{id:'m1',pid:null,name:'You',rel:'You',age:0,sex:'male',w:0,h:0,av:'YO',c:'',shared:true}]}))}}catch(e){}return true}"
    "catch(e){try{sessionStorage.removeItem('tht-invite')}catch(_){}alert(e.message);return false}}")
one("const finish=async(r,offer=true)=>{clearAuthState();ME=r.user;if(offer&&THT.passkey.supported()&&!ME.passkeys&&await THT.passkey.platform().catch(()=>false)){show('offer');return}location.href=NEXT};",
    "const finish=async(r,offer=true)=>{clearAuthState();ME=r.user;if(INVITE){await joinFamily();location.href='/app';return}if(offer&&THT.passkey.supported()&&!ME.passkeys&&await THT.passkey.platform().catch(()=>false)){show('offer');return}location.href=NEXT};")
one("if(!restoreAuthState()){const route={'/signin':'signin','/signup':'signup','/reset':'reset'}[location.pathname];if(route)open(route)}",
    "if(!restoreAuthState()){const route={'/signin':'signin','/signup':'signup','/reset':'reset'}[location.pathname];if(route)open(route)}\n"
    "if(JOINM){fetch('/api/v1/family/invite/'+INVITE).then(r=>r.json().then(j=>({ok:r.ok,j}))).then(({ok,j})=>{if(!ok){INVITE=null;try{sessionStorage.removeItem('tht-invite')}catch(e){}open('signup');say(j.detail||'This invitation is no longer valid.');return}"
    "const who=String(j.by||'A family member').replace(/[<>&]/g,''),nm=String(j.name||'').replace(/[<>&]/g,'');if(ME){joinFamily().then(ok=>{if(ok)location.href='/app'});return}open('signup');const h=document.querySelector('#fUp h2'),p=document.querySelector('#fUp .sub');if(h)h.textContent='Join your family';if(p)p.textContent=who+' set up a profile for '+(nm||'you')+'. Create your account to see it on your phone.';"
    "if(nm){const n=document.getElementById('un');if(n&&!n.value)n.value=nm}const back=document.querySelector('#fUp .foot');if(back)back.insertAdjacentHTML('afterend','<p class=\"foot\">Already have an account? <a class=\"lnk\" data-v-go=\"signin\">Sign in</a> and you will be added to the family.</p>')}).catch(()=>{})}")

# privacy wording: records sync once you sign in
s = s.replace("Health records stay on your device", "Encrypted, stored in India")
one("<b>Records stay with you</b><p>Reports, results and your health card live on your device. You choose what leaves it.</p>",
    "<b>Encrypted, stored in India</b><p>Without an account, records stay on your device. When you sign in they are encrypted and backed up in India, so your family sees the same records on every phone.</p>")
one("<summary>Where are my health records stored?</summary><p>Reports, photos, results and your Medical ID are stored in your browser on your device. Our server stores your account, orders, plan and ratings. When you choose to analyse a document with AI, it is sent for that one analysis and not kept.</p>",
    "<summary>Where are my health records stored?</summary><p>Without an account, everything stays in your browser on your device. When you sign in, your family's profiles, results, medicines and cards are encrypted and stored on our servers in India, so each family member sees them on their own phone. Photos and PDFs stay on the device where they were added. A document you analyse with AI is sent for that one reading and not kept.</p>")
s = s.replace("</body>", "<!--live-p2-->\n</body>", 1)
F.write_text(s, encoding="utf-8")
print("landing patched")
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
