"""Round 29 patch: the phone fixes — zoom lock, body framing, instant SOS, Devices install card, Google map hospitals, layer 29."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p29*/"
s = W.read_text(encoding="utf-8")
if "/*live-p28*/" not in s:
    sys.exit("apply p28 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str, what: str) -> None:
    global s
    if s.count(old) != 1:
        sys.exit(f"{what}: anchor found {s.count(old)}×")
    s = s.replace(old, new)


# 1. a mobile app does not zoom
one('<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
    '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">', "viewport")
# 2. the 3D body on a portrait phone: a wider vertical view and the frame pushed down so the head clears the search bar
one("const fit=()=>{const w=stage.clientWidth,h=stage.clientHeight;R.setSize(w,h,false);C.aspect=w/h;C.updateProjectionMatrix()};",
    "const fit=()=>{const w=stage.clientWidth,h=stage.clientHeight;R.setSize(w,h,false);C.aspect=w/h;const ph=w>0&&h>0&&w/h<.85;C.fov=ph?33:30;if(ph)C.setViewOffset(w,h,0,-Math.round(h*.05),w,h);else if(C.view&&C.view.enabled)C.clearViewOffset();C.updateProjectionMatrix()};", "body fit")
# 3. SOS: no countdown — the press is the alert; the call does not hold up the alert; the alert carries the location we already have
start = s.find("const t=callTarget(m);let n=3;")
end = s.find("else el.textContent=n},1000)};", start)
if start < 0 or end < 0 or end - start > 2000:
    sys.exit("sos countdown anchor")
s = s[:start] + "fire(m)};" + s[end + len("else el.textContent=n},1000)};"):]
one("async function fire(m){const t=callTarget(m),cs=SX.contactsOf(m.id).filter(c=>c.notify);",
    "async function fire(m){try{SX.siren&&SX.siren.start()}catch(e){}const t=callTarget(m),cs=SX.contactsOf(m.id).filter(c=>c.notify);", "sos fire")
one(" A.how=await placeCall(t.num);paint(m);", " placeCall(t.num).then(h=>{A.how=h;paint(m)});", "sos call")
one(" const loc=A.loc||await locate(6000);A.loc=loc;",
    " const loc=A.loc||(S.net&&S.net.geo?{lat:S.net.geo.lat,lng:S.net.geo.lng,acc:0}:null)||await locate(4000);A.loc=loc;", "sos loc")
one("SX.act.sossafe=async()=>{if(!A)return;A.active=false;", "SX.act.sossafe=async()=>{if(!A)return;A.active=false;try{SX.siren&&SX.siren.stop()}catch(e){}", "sos safe")
one("A.hosp=(r.items||[]).slice(0,3)", "A.hosp=((r.places||[]).concat(r.partners||[])).sort((a,b)=>a.km-b.km).slice(0,3)", "sos hospitals")
# 4. Google map: no made-up map id (it only silences the console on the free map)
one(",mapId:'THT'}", "}", "map id")
# 5. Devices: install the way this phone installs — no Android download on an iPhone, no "coming" badges inside the app
one("""<div class="lv11-dl">${a.available?`<a class="btn p sm" href="${E(a.url)}">🤖 ${P('Download for Android')} <small>v${E(a.version)} · ${(a.size/1048576).toFixed(1)} MB</small></a>`:`<span class="btn s sm" aria-disabled="true">🤖 ${P('Android app — publishing soon')}</span>`}${a.play?`<a class="btn s sm" href="${E(a.play)}" target="_blank" rel="noopener">Google Play</a>`:''}${i.appstore?`<a class="btn p sm" href="${E(i.appstore)}" target="_blank" rel="noopener"> App Store</a>`:i.testflight?`<a class="btn s sm" href="${E(i.testflight)}" target="_blank" rel="noopener"> TestFlight beta</a>`:`<span class="btn s sm" aria-disabled="true"> ${P('iPhone app — coming')}</span>`}</div>
   ${isIOS&&!native?`<small>${P('iPhone today: Share → Add to Home Screen installs this as an app; Apple Health sync arrives with the App Store app.')}</small>`:''}""",
    """<div class="lv11-dl">${isIOS?'':a.available?`<a class="btn p sm" href="${E(a.url)}">🤖 ${P('Download for Android')} <small>v${E(a.version)} · ${(a.size/1048576).toFixed(1)} MB</small></a>`:''}${!isIOS&&a.play?`<a class="btn s sm" href="${E(a.play)}" target="_blank" rel="noopener">Google Play</a>`:''}${isIOS&&i.appstore?`<a class="btn p sm" href="${E(i.appstore)}" target="_blank" rel="noopener"> App Store</a>`:isIOS&&i.testflight?`<a class="btn s sm" href="${E(i.testflight)}" target="_blank" rel="noopener"> TestFlight beta</a>`:''}</div>
   ${isIOS&&!matchMedia('(display-mode: standalone)').matches?`<div class="lv29-ios"><i>📲</i><div class="grow"><b>${P('Install on this iPhone')}</b><small class="mute">${P('Share → Add to Home Screen. Full-screen, with your sign-in kept.')}</small></div><button class="btn p sm" data-sx="a2hs">${P('How')}</button></div>`:''}""", "devices install")

# the hand-written strings this layer adds (whatever p28 did not already inline)
import json  # noqa: E402

sys.path.insert(0, str(ROOT / "tools" / "i18n"))
from core import CORE  # noqa: E402

fresh = {k: v for k, v in CORE.items() if json.dumps(k, ensure_ascii=False) + ":" not in s}
print(f"layer 29 adds {len(fresh)} hand-written phrases")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live29-css">' + (HERE / "live29.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
layer = (HERE / "live29.js").read_text(encoding="utf-8").replace("/*LV29_CORE*/{}/*/LV29_CORE*/", json.dumps(fresh, ensure_ascii=False))
s = s.replace(BOOT, MARK + "\n" + layer + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
