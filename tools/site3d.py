"""Turn the 3D story website (the designer's single-file build) into the production home page.

    python tools/site3d.py <unzipped-website-folder>     # writes site/home/index.html + site/home/{m,img,js}/
    python tools/compress.py                             # then refresh the .br/.gz copies

The designer's build is one index.html plus m/*.js files that carry each 3D model as base64 text and pulls three.js
and Inter from public CDNs. In production nothing may come from a CDN (the CSP allows 'self' only, and the page must
not break when a CDN does), and base64 is a third heavier than the model itself. So this:

* decodes every model to a binary .glb with a content hash in its name (cached for good, fetched only when needed);
* serves three.js 0.160 (the version the page was built against) from /s/home/js/three-0.160.0/ through an import map;
* uses the system font on Apple devices and our own Geist elsewhere, instead of Inter from Google Fonts;
* keeps the live page's search, sharing and structured-data tags, so nothing changes for Google or WhatsApp previews;
* sends "Get started" and "Sign in" to the real app (/signup, /signin) instead of the demo screens;
* replaces the demo footer with the legal one: medical disclaimer, privacy, terms, grievance officer, app downloads.
"""
from __future__ import annotations

import base64
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "home"
THREE = Path("/tmp/three160/package")          # npm pack three@0.160.0 && tar xzf three-0.160.0.tgz
JS = OUT / "js" / "three-0.160.0"
ADDONS = ["loaders/GLTFLoader.js", "utils/BufferGeometryUtils.js", "libs/meshopt_decoder.module.js", "environments/RoomEnvironment.js"]


def h8(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:8]


def main(src: Path) -> None:
    s = (src / "index.html").read_text()
    live_head = (OUT / "index.html").read_text()
    live_head = live_head[:live_head.find("</head>")]

    # ---- models: base64 .js  ->  binary .glb ----
    (OUT / "m").mkdir(parents=True, exist_ok=True)
    for old in (OUT / "m").glob("*.glb"):
        old.unlink()
    models = {}
    for f in sorted((src / "m").glob("*.js")):
        t = f.read_text()
        m = re.fullmatch(r'\(window\.UHM=window\.UHM\|\|\{\}\)\["([\w-]+)"\]="([A-Za-z0-9+/=]+)";?\s*', t)
        assert m, f.name
        b = base64.b64decode(m.group(2))
        name = f"{m.group(1)}.{h8(b)}.glb"
        (OUT / "m" / name).write_bytes(b)
        models[m.group(1)] = name
    # ---- pictures ----
    (OUT / "img3d").mkdir(parents=True, exist_ok=True)
    for old in (OUT / "img3d").glob("*"):
        old.unlink()
    for f in sorted(src.glob("*.png")):
        b = f.read_bytes()
        name = f"{f.stem}.{h8(b)}.png"
        (OUT / "img3d" / name).write_bytes(b)
        s = s.replace(f'"{f.name}"', f'"/s/home/img3d/{name}"').replace(f"'{f.name}'", f"'/s/home/img3d/{name}'").replace(f"({f.name})", f"(/s/home/img3d/{name})")
    # ---- three.js, self-hosted ----
    if JS.exists():
        shutil.rmtree(JS)
    (JS / "addons").mkdir(parents=True)
    shutil.copy(THREE / "build" / "three.module.min.js", JS / "three.module.min.js")
    for a in ADDONS:
        d = JS / "addons" / a
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(THREE / "examples" / "jsm" / a, d)
    imap = ('<script type="importmap">{"imports":{"three":"/s/home/js/three-0.160.0/three.module.min.js",'
            '"three/addons/":"/s/home/js/three-0.160.0/addons/"}}</script>')
    s = s.replace("import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/+esm';", "import * as THREE from 'three';")
    s = s.replace("import {GLTFLoader} from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/GLTFLoader.js/+esm';", "import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';")
    s = s.replace("import {MeshoptDecoder} from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/libs/meshopt_decoder.module.js/+esm';", "import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';")
    s = s.replace("import {RoomEnvironment} from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/environments/RoomEnvironment.js/+esm';", "import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';")
    assert "cdn.jsdelivr" not in s
    # model bytes: fetch the .glb instead of injecting a base64 script
    a = s.index("const bytes=k=>bufP[k]||")
    b = s.index("\n", s.index("appendChild(s)}));", a)) + 1
    s = s[:a] + ("const MODELS=" + __import__("json").dumps(models, separators=(",", ":")) + ";\n"
                 "const bytes=k=>bufP[k]||(bufP[k]=fetch('/s/home/m/'+MODELS[k]).then(r=>{if(!r.ok)throw Error('model '+k);return r.arrayBuffer()}).then(b=>{const a=new Uint8Array(b);bufs[k]=a;return a}));\n") + s[b:]
    # ---- head: the live page's metadata, our fonts, the import map ----
    keep = [l for l in re.findall(r'<(?:meta|link|title)[^>]*>(?:[^<]*</title>)?|<script type="application/ld\+json">.*?</script>', live_head, re.S)
            if "stylesheet" not in l and "preload" not in l and 'charset' not in l and 'viewport' not in l]
    s = re.sub(r'<link rel="icon"[^>]*>\s*', "", s, count=1)
    s = re.sub(r"<title>Urban Health</title>", "", s)
    s = re.sub(r'<link rel="preconnect"[^>]*>', "", s)
    s = re.sub(r'<link href="https://fonts\.googleapis\.com[^>]*>', "", s)
    s = s.replace('--sf:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue","Inter",system-ui,sans-serif;',
                  '--sf:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Geist,system-ui,sans-serif;')
    font = ("<link rel=\"preload\" href=\"/s/fonts/geist.woff2\" as=\"font\" type=\"font/woff2\" crossorigin>"
            "<style>@font-face{font-family:Geist;src:url(/s/fonts/geist.woff2) format('woff2');font-weight:100 900;font-display:swap}</style>")
    s = s.replace('<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
                  '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n' + "\n".join(keep) + "\n" + font + "\n" + imap, 1)
    s = s.replace('<meta name="theme-color" content="#000000">', '<meta name="theme-color" content="#FFFFFF">')
    # ---- the real sign-in and sign-up ----
    s = s.replace('href="#create-account"', 'href="/signup"').replace('href="#sign-in"', 'href="/signin"')
    s = s.replace("function route(){", "function route(){if(/^#(sign-in|create-account)$/.test(location.hash)){location.replace(location.hash==='#sign-in'?'/signin':'/signup');return}", 1)
    # ---- footer ----
    a, b = s.index("<footer>"), s.index("</footer>") + len("</footer>")
    logo = re.search(r"<svg.*?</svg>", s[a:b], re.S).group(0)
    foot = f"""<footer><div class="wrap">
 <p class="fd">Urban Health helps you understand and organise health information. It does not diagnose and does not replace a doctor's advice, diagnosis or treatment. In an emergency, call <a href="tel:112">112</a>, or <a href="tel:108">108</a> for an ambulance. Doctors, values and fees shown on this page are examples.</p>
 <div class="fg">
  <div class="fb"><span class="fl">{logo}</span><span>Your family's health, in one secure place.</span><span>Made in India, for families across India. Your data stays in India.</span></div>
  <div><b>Use Urban Health</b><a href="/signup">Create an account</a><a href="/signin">Sign in</a><a href="/download/urbanhealth.apk">Android app</a></div>
  <div><b>For partners</b><a href="/partner">Partner sign-in</a><a href="/download/urbanhealth-partner.apk">Partner Android app</a><a href="mailto:partner@urbanhealth.in">partner@urbanhealth.in</a></div>
  <div><b>Trust</b><a href="/privacy">Privacy policy</a><a href="/terms">Terms of use</a><a href="mailto:support@urbanhealth.in">support@urbanhealth.in</a><span>Grievance Officer: same address, subject “Grievance”</span></div>
 </div>
 <span class="fc">Anatomy from BodyParts3D, © The Database Center for Life Science, CC BY 4.0. Baby model “Fetus” by gelmi.com.br, CC BY 4.0.</span>
 <span class="fc">© 2026 Urban Health · urbanhealth.in</span>
</div></footer>"""
    s = s[:a] + foot + s[b:]
    css = (".fd{margin:0 0 16px;font-size:12.5px;color:var(--ink2);max-width:880px}.fd a{color:var(--ink);font-weight:600}"
           ".fg{display:grid;grid-template-columns:1.4fr 1fr 1fr 1.2fr;gap:22px;padding:16px 0 18px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin-bottom:12px}"
           ".fg>div{display:flex;flex-direction:column;gap:7px;font-size:13px}.fg b{color:var(--ink);font-size:13px}.fg a{color:var(--ink2);text-decoration:none}.fg a:hover{color:var(--blue)}"
           ".fl svg{height:22px}.fl svg [fill='#fff']{fill:var(--ink)}.fc{font-size:11.5px;color:var(--ink3)}"
           "@media (max-width:900px){.fg{grid-template-columns:1fr 1fr}.fb{grid-column:1/-1}}")
    s = s.replace("footer .wrap{display:flex;flex-direction:column;gap:6px}", "footer .wrap{display:flex;flex-direction:column;gap:6px;max-width:1100px;margin:0 auto}" + css, 1)
    # phone: the organs can sit under the story words, so the words get a frosted card (the opening line keeps none)
    s = s.replace(".sx{left:20px;right:20px;width:auto;top:70px;transform:none}",
                  ".sx{left:14px;right:14px;width:auto;top:66px;transform:none;background:rgba(255,255,255,.78);-webkit-backdrop-filter:blur(18px) saturate(180%);backdrop-filter:blur(18px) saturate(180%);border-radius:22px;padding:14px 16px 16px;box-shadow:0 6px 24px rgba(0,0,0,.06)}"
                  ".sx.s0{background:none;-webkit-backdrop-filter:none;backdrop-filter:none;box-shadow:none;padding:0 22px}", 1)
    (OUT / "index.html").write_text(s)
    # the old page's own CSS/JS are no longer referenced
    for f in OUT.glob("site.*"):
        f.unlink()
    print("models:", len(models), "| html", len(s), "bytes")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
