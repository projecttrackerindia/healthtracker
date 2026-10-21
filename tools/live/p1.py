"""Round 2 patch for web/index.html (run once from the repository root after p0: python tools/live/p1.py).

Body follows the person (no sex switch), richer family form, contacts, pregnancy mode, cards & insurance, notifications,
baby skin and female arm shape. Every replacement must match exactly once or nothing is written.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p1*/"

s = W.read_text(encoding="utf-8")
if "/*live-p0*/" not in s:
    sys.exit("apply p0 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str) -> None:
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:100]!r}")
    s = s.replace(old, new)


# 1. family form: date of birth, sex, blood group, mobile
i = s.index("function memberForm(m){")
j = s.index("SX.reg('family'", i)
s = s[:i] + (HERE / "family_form.js").read_text(encoding="utf-8") + s[j:]
k = s.index("SX.chg.fsave=")
l = s.index("\n", s.index("SX.paintWho()};", k))
s = s[:k] + (HERE / "family_save.js").read_text(encoding="utf-8").rstrip("\n") + s[l:]

# 2. no sex switch in the Anatomy Lab panel; the model follows the person
one("<h4>Model</h4>${sexSeg()}<h4>Layers ", "<h4>Layers ")
one("""This system isn't in the ${A.sex} dataset. <button class="btn p sm" data-sex="${A.sex==='male'?'female':'male'}">Switch to ${A.sex==='male'?'female':'male'}</button></p>""",
    """This system is not shown in the ${A.sex==='male'?'male':'female'} model.</p>""")

# 3. reminders: the old fixed-time card and ticker are replaced by the notification centre
one("""  <div class="card wide"><div class="hd"><h3>Reminders</h3><label class="sx-sw"><input type="checkbox" data-sxc="remtog" ${S.rem.on?'checked':''} aria-label="Remind me while Urban Health is open"><i></i></label></div>
   <p class="mute sm" style="margin:0">Morning 8 AM · Afternoon 2 PM · Evening 6 PM · Night 9 PM. Reminders appear while Urban Health is open in a tab or installed app. Phone notifications when the app is closed need the push service, which is coming soon.</p></div>`},""", "`},")
one("setInterval(remTick,30000);", "/* remTick: replaced by the notification centre in live layer 2 */")

# 4. baby skin: softer, less plastic (lower clearcoat, warm sheen, gentler rim light)
one("const fetMat=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.52,clearcoat:.22,clearcoatRoughness:.45,emissive:0x220606,side:THREE.DoubleSide});",
    "const fetMat=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.6,clearcoat:.1,clearcoatRoughness:.7,sheen:new THREE.Color(0x5a3a34),emissive:0x1c0606,side:THREE.DoubleSide});")
one("totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.0,.55,.5)*frm*.55;", "totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.0,.6,.55)*frm*.4;")

# 5. female arms: a gentler taper from shoulder to wrist (the fitted warp pinched the elbow and thinned the forearm)
a = s.index('<script id="fwarp" type="application/json">') + len('<script id="fwarp" type="application/json">')
b = s.index("</script>", a)
J = json.loads(s[a:b])
ss = lambda x0, x1, x: (lambda t: t * t * (3 - 2 * t))(min(1, max(0, (x - x0) / (x1 - x0))))
for side in ("1", "-1"):
    n = len(J["ARM"][side]["su"])
    J["ARM"][side]["su"] = [round(1.08 + (0.86 - 1.08) * ss(0.38, 0.78, i / (n - 1)), 4) for i in range(n)]
    J["ARM"][side]["sv"] = [round(1.10 + (0.90 - 1.10) * ss(0.38, 0.80, i / (n - 1)), 4) for i in range(n)]
s = s[:a] + json.dumps(J, separators=(",", ":")) + s[b:]

# 6. our mark on the health card made by the first live layer (the fresh-card reveal uses it)
one('<span class="lv-card-brand"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-5 3 10 2-5h7"/></svg>urbanhealth</span>',
    '<span class="lv-card-brand"><svg viewBox="0 0 64 64" aria-hidden="true"><path d="M21.5 15a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4v34a4 4 0 0 1-4 4h-3a4 4 0 0 1-4-4V37.5H13a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h8.5z" fill="currentColor"/><path d="M32 32h5l3.2-8 4.6 16 3.2-8h0.4" fill="none" stroke="currentColor" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="55.2" cy="32" r="3.3" fill="currentColor"/></svg><b>Urban <i>Health</i></b></span>')

# 7. the layer itself
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live2.js").read_text(encoding="utf-8") + "\n" + BOOT)
one("</head>", '<style id="live2-css">' + (HERE / "live2.css").read_text(encoding="utf-8") + "</style>\n</head>")

W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
