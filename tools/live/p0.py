"""Round 1 production fixes for web/index.html (run once from the repository root: python tools/live/p0.py).

Every replacement must match exactly once, otherwise nothing is written. After it runs, tools/compress.py refreshes
the .br/.gz copies. Sources of the inserted code: tools/live/purge.js, live.js and live.css.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p0*/"

s = W.read_text(encoding="utf-8")
if MARK in s:
    sys.exit("already applied")

R: list[tuple[str, str]] = []

# 1. store: remove the sample household saved by earlier versions, once, before anything reads it
R.append(("if(!S)S=demo();\nSX.S=S;",
          MARK + "\n" + (HERE / "purge.js").read_text(encoding="utf-8") + "\nif(S)S=purgeSample(S);\nif(!S)S=demo();\nSX.S=S;"))

# 2. 3D body hotspots: no random heart rate, stress or joint scores. Only readings the person entered.
R.append(("const H=[{n:'Stress Level',ic:'🧠',v:()=>'28%'},{n:'Heart Rate',ic:'❤️',v:()=>hr+' bpm'},{n:'Blood Pressure',ic:'💉',v:()=>'120/80'},{n:'Blood Sugar',ic:'🩸',v:()=>'95 mg/dL'},{n:'Joint Health',ic:'🦵',v:()=>'92%'}];\nlet hr=72,cur=1;",
          "const LV=k=>window.SX&&SX.latestVital?SX.latestVital(k):null;\n"
          "const H=[{n:'',ic:'',v:()=>null},{n:'Heart rate',ic:'❤️',v:()=>LV('hr')},{n:'Blood pressure',ic:'💉',v:()=>LV('bp')},{n:'Blood sugar',ic:'🩸',v:()=>LV('glu')},{n:'',ic:'',v:()=>null}];\nlet hr=0,cur=1;"))
R.append(("function tip(){const h=H[cur];$('#tic').textContent=h.ic;$('#tn').textContent=h.n;$('#tv').textContent=h.v();H.forEach((x,i)=>x.el.classList.toggle('act',i==cur))}\nsetInterval(()=>{hr=68+Math.round(Math.random()*9);tip();const f=$('#fhr');if(f)f.textContent=hr+' bpm'},2500);",
          "function tip(){if(!H[cur].v()){const k=H.findIndex(x=>x.v());if(k>=0)cur=k}const h=H[cur];$('#tic').textContent=h.ic;$('#tn').textContent=h.n;$('#tv').textContent=h.v()||'';H.forEach((x,i)=>x.el.classList.toggle('act',i==cur))}\nsetInterval(tip,3000);"))
R.append(("o.el.style.cssText=`left:${o.x}px;top:${o.y}px;display:${dotsOn&&front?'block':'none'}`});\n const a=H[cur],t=$('#tip');t.style.display=dotsOn&&a.el.style.display!=='none'?'flex':'none';",
          "o.el.style.cssText=`left:${o.x}px;top:${o.y}px;display:${dotsOn&&front&&o.v()?'block':'none'}`});\n const a=H[cur],t=$('#tip');t.style.display=dotsOn&&a.el.style.display!=='none'&&a.v()?'flex':'none';"))

# 3. family form: a changed sex now switches the body (the old check ran after the value was overwritten)
R.append(("if(id){const m=SX.member(id);Object.assign(m,{name,age,sex,rel:m.rel==='You'?'You':rel,w,h,av:name.slice(0,2).toUpperCase()});const p=SX.pat(m);if(p){p.n=name;p.age=age}toast('Saved '+name);\n  if(sex!==m.sex)SX.pendingModel=true}",
          "if(id){const m=SX.member(id),sex0=m.sex;Object.assign(m,{name,age,sex,sexOk:true,rel:m.rel==='You'?'You':rel,w,h,av:name.slice(0,2).toUpperCase()});if(m.dob&&m.rel!=='You'&&Math.abs(SX.ageFrom(m.dob)-age)>0)delete m.dob;delete m.review;const p=SX.pat(m);if(p){p.n=name;p.age=age}toast('Saved '+name);\n  if(sex!==sex0&&m.id===S.active){SX.pendingModel=true;SX.applyModel()}}"))

# 4. Home: real readings, the health card, real visits
R.append(("function heroCard(m){const p=SX.pat(m)", "function heroCard(m){return SX.lvVitalsHero(m)}\nfunction heroCard0(m){const p=SX.pat(m)"))
R.append(("function vitalsCard(m){const p=SX.pat(m),bmi=SX.bmi(m);", "function vitalsCard(m){return SX.lvVitalsCard(m)}\nfunction vitalsCard0(m){const p=SX.pat(m),bmi=SX.bmi(m);"))
R.append(("function visitCard(m){const a=appts(m)[0],d=a?DOC[a.doc]:null;", "function visitCard(m){return SX.lvVisitCard(m)}\nfunction visitCard0(m){const a=appts(m)[0],d=a?DOC[a.doc]:null;"))
R.append(("render:()=>{const m=SX.me();return heroCard(m)+setupCard(m)", "render:()=>{const m=SX.me();return heroCard(m)+SX.lvCardTile(m)+setupCard(m)"))

# 5. AI wording: no provider or model names in the app (the privacy policy lists processors)
R.append(("SX.cfg.ai.engine==='claude'", "SX.cfg.ai.engine==='ai'"))
R.append(("and to the AI provider (Anthropic) for this one analysis", "and to our AI processing partner for this one analysis (listed in the privacy policy)"))
R.append(("eng=r.engine==='claude';", "eng=r.engine==='ai';"))
R.append(("(and the AI provider)", "(and our AI processing partner)"))

# 6. ordering: never fall back to made-up pharmacies or simulated orders
R.append(("${e.offline?P('No connection: the sample pharmacies below are used.'):P('Live prices are not available right now.')}</p>`;const ph=box.nextElementSibling;if(ph){ph.hidden=false;const h=box.previousElementSibling;if(h&&h.classList.contains('sx-h4'))h.hidden=false}return}",
          "${e.offline?P('No connection right now. Your basket is saved.'):P('Online ordering is not available in your area yet. Your basket is saved; you can show it at any pharmacy.')}</p>`;return}"))
R.append(("function paintLive(box){const L=LIVE;if(!L)return;const el=box.querySelector('.sx-livel');",
          "function paintLive(box){const L=LIVE;if(!L)return;const el=box.querySelector('.sx-livel');if(!L.stores||!L.stores.length){el.innerHTML=`<p class=\"mute sm\">${P('Online ordering is not available in your area yet. Your basket is saved; you can show it at any pharmacy.')}</p>`;return}"))
R.append(("Demo checkout. No real order is placed and no money is taken. Pay on delivery.", "Pay on delivery. The pharmacy confirms stock and the final price before dispatch."))
R.append(("Sample catalogue and demo prices.", "Prices are approximate MRP; the pharmacy confirms the final price."))
R.append(("(demo price)", "(approx. MRP)"))
R.append(("Track what you ordered. Sample pharmacies.", "Track what you ordered."))
R.append(("which is not part of this demo.", "which is coming soon."))

# 7. no "sample / demo" labels on a real person's data
R.append(('<span class="demo">SAMPLE FAMILY</span>', ''))
R.append(('<h3>Family access</h3><span class="demo">DEMO</span>', '<h3>Family access</h3>'))
R.append(("In the full product each adult decides this from their own account.", "When family sharing launches, each adult decides this from their own account."))
R.append(("Pharmacy orders and doctor bookings in this demo are simulated; nothing is sent.", "A pharmacy receives an order only when you place it, and only what that order needs."))
R.append(("When accounts launch, data will be stored in India and you will be asked before anything moves off this device.", "Health records stay on this device. You are asked before anything leaves it."))
R.append(("Sample people, results, doctors, pharmacies and prices are fictional. ", ""))
R.append((" · Sample patient data is fictional</small>", "</small>"))
R.append(("▶ Demo tour", "▶ Take a tour"))
R.append((" Patients, results, doctors and invoices are fictional sample data for this demo. This is not a diagnostic tool.", " TheHealthTracker gives information, not a diagnosis."))
R.append(("Visits and sharing','Book by specialty. Reports go to the doctor only if you tick share for that visit, and each share is written to your consent history.'",
          "Visits','Keep every doctor visit for the family in one place. The next one shows on Home.'"))

for old, new in R:
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:90]!r}")
    s = s.replace(old, new)

# "Press Demo tour any time" appears in the old and the new tour text
s = s.replace("Press Demo tour any time", "Press Take a tour any time")

# 8. the live layer goes inside the last six IIFE, right before boot
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, (HERE / "live.js").read_text(encoding="utf-8") + "\n" + BOOT)

# 9. styles
if s.count("</head>") != 1:
    sys.exit("head anchor not unique")
s = s.replace("</head>", '<style id="live-css">' + (HERE / "live.css").read_text(encoding="utf-8") + "</style>\n</head>")

W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT), f"({len(R)} replacements)")
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
