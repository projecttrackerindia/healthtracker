"""Full-detail female body: the female body's own skin and organs (HuBMAP / Z-Anatomy female model) with the male
atlas's 2,710-structure muscles, bones, vessels and nerves reshaped into the female body (Z-Anatomy / BodyParts3D,
CC BY-SA 4.0). The reshaping (scale the trunk, widen the pelvis, carry arms and legs on their joints) was fitted
against the female skin on the design canvas; see FIT below. Male-only structures are left out.

    python3 tools/make_female.py
writes web/a/female-full.<h>.bin + names-ff.<h>.json (fast body) and web/a/hdf-l1..5.<h>.bin (sharper layers),
and prints the paths for body.html.
"""
import glob, gzip, hashlib, json, os, re, struct
import numpy as np

A = os.path.join(os.path.dirname(__file__), '..', 'web', 'a')
MALE_ONLY = re.compile(r'cremaster|dartos|scrot|penis|penile|testi|prostat|spermatic|deferens|seminal|epididym|glans|corpus cavernosum|corpus spongiosum|bulb of penis', re.I)
P = dict(sx=1.1, sz=1.22, zoff=.03, px=1.14, armDeg=17, arm=(.47, 1.96, -.09), tip=(1.19, -.21), armLen=1.07, legDeg=1.4, hip=(.17, .07), hipTo=(.31, -.04), ankleY=-2.62)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fit(V, b):
    """V: (n,3) male coordinates of one part, b: its bounds. Returns female coordinates. Same maths as the canvas."""
    p = P
    ux, uy = p['tip'][0] - p['arm'][0], p['tip'][1] - p['arm'][1]; ul = np.hypot(ux, uy); nx, ny = ux / ul, uy / ul
    cx, cy = abs((b[0] + b[3]) / 2), (b[1] + b[4]) / 2
    ex, ey = cx - p['arm'][0], cy - p['arm'][1]; tc = ex * nx + ey * ny; dc = abs(ex * ny - ey * nx); h = b[4] - b[1]
    mnx = min(abs(b[0]), abs(b[3])) if np.sign(b[0]) == np.sign(b[3]) else 0
    wc = max(float(ss(.04, .14, tc) * ss(.3, .2, dc) * (1 if h < 1.2 else 0) * ss(.3, .4, mnx)), 1.0 if (cx > .6 and cy < 1.9) else 0.0)
    wlc = 1.0 if (b[4] < p['hip'][1] - .02 and cx < .62 and min(abs(b[0]), abs(b[3])) > .03 and np.sign(b[0]) == np.sign(b[3])) else 0.0
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    sd = np.where(x < 0, -1.0, 1.0); ax = np.abs(x)
    k = ss(2.42, 2.12, y) * ss(-.55, -.15, y); kp = ss(.75, .45, y) * ss(-.45, -.2, y)
    sx = (1 + (p['sx'] - 1) * k) * (1 + (p['px'] - 1) * kp); sz = 1 + (p['sz'] - 1) * k
    T0, T1, T2 = ax * sx, y.copy(), z * sz + p['zoff'] * k
    dx0, dy0 = ax - p['arm'][0], y - p['arm'][1]; t = dx0 * nx + dy0 * ny; d = np.abs(dx0 * ny - dy0 * nx)
    wa = np.maximum.reduce([ss(-.07, .06, t) * ss(.2, .12, d), np.full_like(x, wc), ss(.56, .64, ax) * ss(1.9, 1.7, y)])
    if (wa > 0).any():
        sh0, sh1 = p['arm'][0] * (p['sx'] - 1), p['arm'][2] * (p['sz'] - 1) + p['zoff']
        pv0, pv1 = p['arm'][0] * p['sx'], p['arm'][1]
        A0, A1, A2 = ax + sh0, y.copy(), z + sh1
        A0 = pv0 + (A0 - pv0) * p['armLen']; A1 = pv1 + (A1 - pv1) * p['armLen']
        a = np.radians(p['armDeg']); c, s = np.cos(a), np.sin(a)
        r0 = pv0 + (A0 - pv0) * c - (A1 - pv1) * s; r1 = pv1 + (A0 - pv0) * s + (A1 - pv1) * c
        T0 = T0 + (r0 - T0) * wa; T1 = T1 + (r1 - T1) * wa; T2 = T2 + (A2 - T2) * wa
    wl = np.maximum.reduce([np.full_like(x, wlc), ss(p['hip'][1] + .14, p['hip'][1] - .12, y) * ss(p['hip'][0] - .04, p['hip'][0] + .05, ax),
                            ss(p['hip'][1] - .12, p['hip'][1] - .32, y) * ss(.02, .08, ax) * ss(.72, .62, ax)]) * (1 - wa)
    if (wl > 0).any():
        L = (p['hipTo'][1] - p['ankleY']) / (p['hip'][1] - p['ankleY'])
        Ly = np.where(y > p['ankleY'], p['ankleY'] + (y - p['ankleY']) * L, y)
        Lx = ax + (p['hipTo'][0] - p['hip'][0] * p['px'])
        a = np.radians(p['legDeg']); c, s = np.cos(a), np.sin(a)
        r0 = p['hipTo'][0] + (Lx - p['hipTo'][0]) * c - (Ly - p['hipTo'][1]) * s
        r1 = p['hipTo'][1] + (Lx - p['hipTo'][0]) * s + (Ly - p['hipTo'][1]) * c
        T0 = T0 + (r0 - T0) * wl; T1 = T1 + (r1 - T1) * wl
    return np.stack([sd * T0, T1, T2], 1)


def load(path):
    raw = gzip.open(path).read(); jl = struct.unpack('<I', raw[:4])[0]
    return raw, 4 + jl, json.loads(raw[4:4 + jl])['parts']


def verts(raw, base, p):
    q = np.frombuffer(raw, dtype=np.uint16, count=p['v'] * 3, offset=base + p['o']).reshape(-1, 3) / 65535.0
    b = np.array(p['b']); return b[:3] + q * (b[3:] - b[:3])


def idx(raw, base, p):
    return raw[base + p['o'] + p['v'] * 6: base + p['o'] + p['v'] * 6 + p['i'] * 2]


def pack(parts):
    """parts: list of (meta dict without o/b, V float (n,3), index bytes). Quantise per part like the body files."""
    head, chunks, off = [], [], 0
    for m, V, I in parts:
        lo, hi = V.min(0), V.max(0); span = np.where(hi - lo > 1e-9, hi - lo, 1e-9)
        q = np.round((V - lo) / span * 65535).astype(np.uint16).tobytes()
        data = q + I; pad = (-len(data)) % 4
        head.append(dict(m, v=len(V), i=len(I) // 2, o=off, b=[round(float(x), 5) for x in list(lo) + list(hi)]))
        chunks.append(data + b'\0' * pad); off += len(data) + pad
    js = json.dumps({'parts': head}, separators=(',', ':')).encode(); js += b' ' * ((-(4 + len(js))) % 4)
    return gzip.compress(struct.pack('<I', len(js)) + js + b''.join(chunks), 9, mtime=0)


def write(stem, blob, ext='bin'):
    h = hashlib.sha256(blob).hexdigest()[:8]
    for old in glob.glob(os.path.join(A, f'{stem}.*.{ext}')): os.remove(old)
    name = f'{stem}.{h}.{ext}'; open(os.path.join(A, name), 'wb').write(blob); return '/a/' + name


def main():
    fraw, fbase, FP = load(sorted(glob.glob(os.path.join(A, 'female.*.bin')))[0])
    fnames = json.load(open(sorted(glob.glob(os.path.join(A, 'names-f.*.json')))[0]))
    mraw, mbase, MP = load(sorted(glob.glob(os.path.join(A, 'body-lite.*.bin')))[0])
    mnames = json.load(open(sorted(glob.glob(os.path.join(A, 'names.*.json')))[0]))
    names, parts = [], []
    for k, p in enumerate(FP):                               # the female body's own skin and organs
        if p.get('l', 1) in (0, 3):
            names.append(fnames[k]); parts.append(({'l': p.get('l', 1)}, verts(fraw, fbase, p), idx(fraw, fbase, p)))
    mk = {}                                                  # male part index -> index in the new names list
    for k, p in enumerate(MP):
        if p.get('l', 1) in (1, 2, 4, 5) and not MALE_ONLY.search(mnames[k]):
            mk[k] = len(names); names.append(mnames[k])
            parts.append(({'l': p.get('l', 1)}, fit(verts(mraw, mbase, p), p['b']), idx(mraw, mbase, p)))
    fast = write('female-full', pack(parts))
    nj = json.dumps(names, separators=(',', ':')).encode()
    namesf = write('names-ff', nj, 'json')
    print(fast, namesf, len(names), 'structures')
    # sharper layers: the male HD packs, reshaped, with k pointing into the new names list
    hdl = {}
    for layer in (1, 2, 4, 5):
        src = sorted(glob.glob(os.path.join(A, f'hd-l{layer}.*.bin')))[0]
        raw, base, HP = load(src)
        out = []
        for p in HP:
            if p['k'] not in mk: continue
            out.append(({'k': mk[p['k']], 'l': layer}, fit(verts(raw, base, p), MP[p['k']]['b']), idx(raw, base, p)))
        hdl[str(layer)] = write(f'hdf-l{layer}', pack(out))
        print(hdl[str(layer)], len(out))
    print('FEMALE_FULL=' + json.dumps({'bin': fast, 'names': namesf, 'hdl': hdl}, separators=(',', ':')))


if __name__ == '__main__':
    main()
