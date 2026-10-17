"""Package the single-file app (new.html) into a light web app for Railway.

  new.html (55 MB, everything embedded)  ->  dokko/web/index.html (~1 MB) + dokko/web/a/* fingerprinted assets

* Model blobs are moved out of the HTML into immutable, fingerprinted files that are fetched on demand.
* Two body detail tiers: 'lite' (loaded by default, a few MB) and 'hd' (full atlas, loaded when asked / on fast links).
* three.js is a separate immutable file so returning visitors only re-download the app code.
* Fonts are self-hosted (no third-party requests).
* Every text file gets .br and .gz variants that server.py serves directly.
"""
import base64, gzip, hashlib, json, os, re, shutil, sys
import brotli

SRC = os.environ.get('SRC', '/home/claude/work/new.html')
OUT = '/home/claude/work/dokko/web'
BUILD = '/home/claude/build'
LITE = os.environ.get('LITE', f'{BUILD}/mdz_lite.b64')

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(f'{OUT}/a')
s = open(SRC, encoding='utf-8').read()
ASSET = {}


def put(name, data: bytes, ext: str) -> str:
    h = hashlib.sha256(data).hexdigest()[:8]
    fn = f'a/{name}.{h}.{ext}'
    open(f'{OUT}/{fn}', 'wb').write(data)
    return fn


def take(sid, name, kind):
    """Remove <script id=sid> from the page, store its payload as an asset, return the asset path."""
    global s
    m = re.search(r'<script id="%s" type="[^"]+">(.*?)</script>\n?' % sid, s, re.S)
    assert m, sid
    txt = m.group(1)
    data = base64.b64decode(txt) if kind == 'bin' else txt.encode('utf-8')
    s = s[:m.start()] + s[m.end():]
    return put(name, data, 'bin' if kind == 'bin' else 'json')


ASSET['#mdz:hd'] = take('mdz', 'body-hd', 'bin')
if os.path.exists(LITE):
    ASSET['#mdz:lite'] = put('body-lite', base64.b64decode(open(LITE).read()), 'bin')
else:
    print('!! no lite blob, hd only'); ASSET['#mdz:lite'] = ASSET['#mdz:hd']
ASSET['#nmz'] = take('nmz', 'names', 'json')
ASSET['#nmf'] = take('nmf', 'names-f', 'json')
ASSET['#latz'] = take('latz', 'latin', 'json')
ASSET['#mdlf'] = take('mdlf', 'female', 'bin')
ASSET['#heartz'] = take('heartz', 'heart-atlas', 'bin')
ASSET['#heartm'] = take('heartm', 'heart-phys', 'bin')

# ---- three.js -> its own immutable file -------------------------------------------------------------
m = re.search(r'<script>(\s*/\*\*\s*\n \* @license\n \* Copyright 2010-2021 Three\.js.*?)</script>', s, re.S)
assert m
three = put('three', m.group(1).encode('utf-8'), 'js')
s = s[:m.start()] + f'<script src="{three}"></script>' + s[m.end():]

# ---- fonts: self-host Geist (variable) ---------------------------------------------------------------
fonts_css = ''
fdir = '/home/claude/work/fonts'
if os.path.isdir(fdir):
    for fam, fn, mono in (('Geist', 'geist-latin-wght-normal.woff2', False), ('Geist Mono', 'geist-mono-latin-wght-normal.woff2', True)):
        p = f'{fdir}/{fn}'
        if os.path.exists(p):
            u = put(fn.split('-')[0] + ('-mono' if mono else ''), open(p, 'rb').read(), 'woff2')
            fonts_css += f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:100 900;font-display:swap;src:url({u}) format('woff2')}}"
# Indic fallbacks (Noto Sans, OFL). unicode-range means a file is fetched only when that script is on screen.
INDIC = (('Noto Sans Devanagari', 'deva', 'U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF'),
         ('Noto Sans Telugu', 'telu', 'U+0C00-0C7F,U+1CDA,U+200C-200D,U+25CC'))
if os.path.isdir(fdir):
    for fam, key, rng in INDIC:
        for w, wr in ((500, '100 600'), (700, '601 900')):
            p = f'{fdir}/notosans-{key}-{w}.woff2'
            if os.path.exists(p):
                u = put(f'notosans-{key}-{w}', open(p, 'rb').read(), 'woff2')
                fonts_css += f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{wr};font-display:swap;src:url({u}) format('woff2');unicode-range:{rng}}}"
s = re.sub(r"@import url\('https://fonts\.googleapis\.com[^']*'\);", lambda _: fonts_css, s)

# ---- asset loader (before any other script uses it) -----------------------------------------------------
LOADER = r"""<script>
window.ASSET=%s;
(()=>{const P={},J={};
 window.assetBlob=(id)=>P[id]??(P[id]=(async()=>{const u=ASSET[id];if(!u)throw Error('asset '+id);const r=await fetch(u);if(!r.ok)throw Error(u+' '+r.status);
  const len=+r.headers.get('content-length')||0,rd=r.body.getReader(),parts=[];let got=0;
  for(;;){const {done,value}=await rd.read();if(done)break;parts.push(value);got+=value.length;if(window.onAssetProgress)window.onAssetProgress(id,got,len)}
  return new Blob(parts)})());
 window.assetBuf=async(id)=>new Response((await assetBlob(id)).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
 window.assetJSON=(id)=>J[id]??(J[id]=fetch(ASSET[id]).then(r=>r.json()));
 /* body detail tier: 'lite' by default; 'hd' when the person asks, or on a fast, unmetered link */
 const c=navigator.connection||{},fast=!c.saveData&&(c.effectiveType==='4g'||!c.effectiveType)&&(navigator.deviceMemory||8)>=4&&innerWidth>900;
 let q='lite';try{q=localStorage.getItem('dk-q')||'lite'}catch(e){}
 window.QUALITY={get:()=>q,set:v=>{q=v;try{localStorage.setItem('dk-q',v)}catch(e){}},fast};
})();
</script>
""" % json.dumps(ASSET)
s = s.replace('<script src="' + three + '"></script>', LOADER + '<script src="' + three + '"></script>', 1)

# ---- patch loaders --------------------------------------------------------------------------------------
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:70], s.count(old))
    s = s.replace(old, new)

# ---- baby generator: no runtime string-eval (the CSP has no 'unsafe-eval') ---------------------------------
m = re.search(r'<script id="fxsrc" type="text/plain">(.*?)</script>', s, re.S)
assert m
s = s[:m.start()] + '<script>window.__FXF=function(){' + m.group(1) + ';return FX};</script>' + s[m.end():]
rep("const FX=new Function(document.getElementById('fxsrc').textContent+';return FX')();", "const FX=window.__FXF();")
rep("const src=$('#fxsrc').textContent+';onmessage=", "const src='self.FX=('+window.__FXF.toString()+')();onmessage=")

rep("async function gunz(id){const raw=Uint8Array.from(atob($(id).textContent),ch=>ch.charCodeAt(0));return new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()}",
    "async function gunz(id){return assetBuf(id)}")
rep("async function gz(id){const raw=Uint8Array.from(atob($(id).textContent),c=>c.charCodeAt(0));return new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()}",
    "async function gz(id){return assetBuf(id)}")
rep("const raw=Uint8Array.from(atob($('#heartz').textContent),c=>c.charCodeAt(0));const buf=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();",
    "const buf=await assetBuf('#heartz');")
rep("async function decode(){const raw=Uint8Array.from(atob($('#heartm').textContent),c=>c.charCodeAt(0));const buf=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();",
    "async function decode(){const buf=await assetBuf('#heartm');")
# body: pick the detail tier, fetch names
rep("ids=s=='male'?[['#mdz','#nmz']]:", "ids=s=='male'?[['#mdz:'+QUALITY.get(),'#nmz']]:")
rep("['#mdz','#nmz',(p,n)=>p.l!==0&&", "['#mdz:'+QUALITY.get(),'#nmz',(p,n)=>p.l!==0&&")
rep("names:JSON.parse($(n).textContent),keep,warp", "names:await assetJSON(n),keep,warp")
rep("names=JSON.parse($('#nmf').textContent);", "names=await assetJSON('#nmf');")
rep("let LAT={};try{LAT=JSON.parse($('#latz').textContent)}catch(e){}", "let LAT={};assetJSON('#latz').then(j=>{LAT=j}).catch(e=>{});")

open(f'{OUT}/index.html', 'w', encoding='utf-8').write(s)

# ---- manifest, service worker ----------------------------------------------------------------------------
assets = sorted(ASSET.values()) + [fn for fn in os.listdir(f'{OUT}/a')]
open(f'{OUT}/manifest.webmanifest', 'w').write(json.dumps({
    'name': 'TheHealthTracker', 'short_name': 'HealthTracker', 'description': 'Family health tracker with a 3D body, records, medicines and SOS.', 'start_url': '/app', 'scope': '/', 'display': 'standalone', 'background_color': '#f3f5fa', 'theme_color': '#2F5BFF',
    'icons': [{'src': 'icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any'},
              {'src': 'brand/png/user-icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
              {'src': 'brand/png/user-icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
              {'src': 'brand/png/user-icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}]}))
# ---- brand kit (logo system: users blue, partners teal, admin graphite) ----
BR='/home/claude/work/brand/out'
shutil.copytree(BR, f'{OUT}/brand', dirs_exist_ok=True)
shutil.copy(f'{BR}/svg/user-icon.svg', f'{OUT}/icon.svg')

ver = hashlib.sha256(s.encode()).hexdigest()[:8]
open(f'{OUT}/sw.js', 'w').write("""const V='dk-%s',SHELL=['/app','/manifest.webmanifest','/icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V&&x.startsWith('dk-')).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==location.origin||u.pathname.startsWith('/api/'))return;
 if(u.pathname.startsWith('/a/')){e.respondWith(caches.open(V).then(async c=>{const h=await c.match(e.request);if(h)return h;const r=await fetch(e.request);if(r.ok)c.put(e.request,r.clone());return r}));return}
 e.respondWith(fetch(e.request).then(r=>{if(r.ok&&u.pathname==='/app')caches.open(V).then(c=>c.put('/app',r.clone()));return r}).catch(()=>caches.match(e.request).then(h=>h||(u.pathname==='/app'?caches.match('/app'):h))))});
""" % ver)
s2 = open(f'{OUT}/index.html', encoding='utf-8').read()
s2 = s2.replace('<head>', '<head><base href="/">', 1)
s2 = s2.replace('</head>', '<link rel="manifest" href="manifest.webmanifest"><link rel="icon" href="icon.svg"><link rel="icon" type="image/png" sizes="32x32" href="brand/png/user-icon-32.png"><link rel="apple-touch-icon" href="brand/png/user-icon-180.png"><meta name="theme-color" content="#2F5BFF"></head>', 1)
s2 = s2.replace('</body>', '<script>' + open('/home/claude/work/quality.js').read() + '</script></body>', 1)
s2 = s2.replace('</body>', "<script>if('serviceWorker' in navigator&&location.protocol.startsWith('http'))addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}))</script></body>", 1)
open(f'{OUT}/index.html', 'w', encoding='utf-8').write(s2)

# ---- pre-compress text assets -------------------------------------------------------------------------------
tot = {}
for root, _, files in os.walk(OUT):
    for f in files:
        if f.endswith(('.br', '.gz')): continue
        p = os.path.join(root, f)
        if f.endswith(('.html', '.js', '.css', '.json', '.svg', '.webmanifest')):
            d = open(p, 'rb').read()
            open(p + '.br', 'wb').write(brotli.compress(d, quality=11))
            open(p + '.gz', 'wb').write(gzip.compress(d, 9))
for root, _, files in os.walk(OUT):
    for f in sorted(files):
        p = os.path.join(root, f); print(f'{os.path.getsize(p)/1e3:10.1f} KB  {os.path.relpath(p, OUT)}')
