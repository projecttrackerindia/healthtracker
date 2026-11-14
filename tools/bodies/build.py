"""Age- and sex-specific bodies for the family 3D view (baby, child, teen), from MakeHuman (CC0).

    git clone --depth 1 --filter=blob:none --sparse https://github.com/makehumancommunity/makehuman /tmp/mh
    (cd /tmp/mh && git sparse-checkout set makehuman/data/3dobjs makehuman/data/targets/macrodetails makehuman/data/rigs)
    python tools/bodies/build.py

Writes web/a/kb-<band>-<sex>.<hash>.json and prints the manifest. Each file holds the skin (quantised
positions + triangles) and torso landmarks, as fractions of height, so the page can move the adult organs
into the child's torso. Adults keep the app's own anatomical body.
"""
import base64, hashlib, json, os, sys
import numpy as np

D = '/tmp/mh/makehuman/data'
OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'web', 'a')
KEEP = {'body'}  # no eyeballs: through the see-through skin they read as rings
RACES = {'caucasian': 1 / 3, 'asian': 1 / 3, 'african': 1 / 3}
BANDS = [('baby', 1), ('child', 7), ('teen', 15), ('adult', 32)]

verts, faces, grp = [], [], None
for line in open(f'{D}/3dobjs/base.obj'):
    if line.startswith('v '):
        verts.append([float(x) for x in line.split()[1:4]])
    elif line.startswith('g '):
        grp = line.split()[1].strip()
    elif line.startswith('f ') and grp in KEEP:
        faces.append([int(p.split('/')[0]) - 1 for p in line.split()[1:]])
V0 = np.array(verts, np.float64)
_cache = {}
def target(name):
    if name not in _cache:
        d = np.zeros_like(V0)
        for line in open(f'{D}/targets/macrodetails/{name}.target'):
            if line.strip() and line[0] != '#':
                i, x, y, z = line.split(); d[int(i)] = (float(x), float(y), float(z))
        _cache[name] = d
    return _cache[name]
def age_w(y):
    if y <= 1: return {'baby': 1}
    if y <= 11: t = (y - 1) / 10; return {'baby': 1 - t, 'child': t}
    if y <= 25: t = (y - 11) / 14; return {'child': 1 - t, 'young': t}
    t = min(1, (y - 25) / 65); return {'young': 1 - t, 'old': t}
SK = json.load(open(f'{D}/rigs/default.mhskel')); WT = json.load(open(f'{D}/rigs/default_weights.mhw'))['weights']
def kids(b): return [b] + [k for n, v in SK['bones'].items() if v['parent'] == b for k in kids(n)]
def joint(V, name): return V[SK['joints'][name]].mean(0)
def relax(V, deg=30):
    for side in ('L', 'R'):
        w = np.zeros(len(V))
        for b in kids(f'upperarm01.{side}'):
            for i, x in WT.get(b, []): w[i] += x
        w = np.clip(w, 0, 1); piv = joint(V, f'upperarm01.{side}____head'); a = np.radians(deg) * (-np.sign(piv[0]))
        c, s = np.cos(a), np.sin(a); d = V - piv
        R = np.stack([d[:, 0] * c - d[:, 1] * s, d[:, 0] * s + d[:, 1] * c, d[:, 2]], 1); V = V + w[:, None] * (R - d)
    return V
def body(sex, yrs):
    V = V0.copy()
    for r, wr in RACES.items():
        for a, wa in age_w(yrs).items(): V += wr * wa * target(f'{r}-{sex}-{a}')
    return relax(V)

tri = []
for f in faces: tri += [(f[0], f[i], f[i + 1]) for i in range(1, len(f) - 1)]
used = sorted({i for t in tri for i in t}); remap = {o: n for n, o in enumerate(used)}
T = np.array([[remap[i] for i in t] for t in tri], np.uint16)
man = {}
for sex in ('male', 'female'):
    for band, yrs in BANDS:
        Vf = body(sex, yrs); V = Vf[used]; y0 = V[:, 1].min(); H = V[:, 1].max() - y0
        J = lambda n: joint(Vf, n)
        hip = (J('upperleg01.L____head') + J('upperleg01.R____head')) / 2
        sh = (J('upperarm01.L____head') + J('upperarm01.R____head')) / 2
        shw = abs(J('upperarm01.L____head')[0] - J('upperarm01.R____head')[0])
        band_ = np.abs(V[:, 1] - (hip[1] * .35 + sh[1] * .65)) < .03 * H
        torso = V[band_ & (np.abs(V[:, 0]) < shw * .45)]
        lm = {'hip': (hip[1] - y0) / H, 'sh': (sh[1] - y0) / H, 'w': shw / H, 'd': float(np.ptp(torso[:, 2]) / H) if len(torso) else .12,
              'cz': float((torso[:, 2].mean() if len(torso) else 0) / H)}
        if band == 'adult':
            man[f'ref-{sex}'] = lm; continue
        b = np.r_[V.min(0), V.max(0)]
        q = np.round((V - b[:3]) / (b[3:] - b[:3]) * 65535).astype(np.uint16)
        rec = {'v': 1, 'band': band, 'sex': sex, 'b': b.round(5).tolist(), 'q': base64.b64encode(q.tobytes()).decode(),
               'i': base64.b64encode(T.tobytes()).decode(), 'lm': {k: round(float(v), 4) for k, v in lm.items()}}
        s = json.dumps(rec, separators=(',', ':')).encode(); name = f'kb-{band}-{sex}.{hashlib.sha256(s).hexdigest()[:8]}.json'
        for old in os.listdir(OUT):
            if old.startswith(f'kb-{band}-{sex}.'): os.remove(os.path.join(OUT, old))
        open(os.path.join(OUT, name), 'wb').write(s); man[f'{band}-{sex}'] = name
        print(band, sex, name, len(s) // 1024, 'KB', rec['lm'], file=sys.stderr)
man['ref-male'] = {k: round(float(v), 4) for k, v in man['ref-male'].items()}; man['ref-female'] = {k: round(float(v), 4) for k, v in man['ref-female'].items()}
print(json.dumps(man, separators=(',', ':')))
