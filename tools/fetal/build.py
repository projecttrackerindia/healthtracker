"""Week-by-week fetal rig + womb data for the pregnancy 3D views.

Input : /tmp/wk/wNN.json, made by tools/fetal/dump.py (the app's own baby and mother models, decoded in a browser).
Output: web/a/pbr-wNN.<hash>.json per week and the manifest printed as JSON (week -> file name).

Per week it holds:
- bone weights for the baby mesh (head, upper arm, forearm+hand, thigh, shin+foot, chest; torso is the rest),
  found by surface (geodesic) distance from each hand, foot and the head, so touching parts never mix,
- joint pivots, limb tips and the arm angles that bring the thumb to the mouth,
- the womb wall (an ellipsoid around the baby), the placenta from that week's mother model pressed into the wall,
  and the cord path from the navel to the middle of the placenta.
Weeks 6-8 (embryo) get only the womb; the placenta first appears in the mother models at week 10.

Week 24 is the reference: its joints were placed by hand and checked; other weeks get them through an affine
registration of week 24 onto that week (all weeks 9-40 share one pose that grows), then snapped to the mesh.
"""
import json, sys, base64, hashlib, os
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

WK = '/tmp/wk'; OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'web', 'a')
# Week-24 reference, in week-24 baby coordinates (metres)
J24 = {"arm": {"L": {"tip": [0.0171, 0.005, 0.0243], "elbow": [0.066, -0.019, -0.027], "shoulder": [0.047, 0.018, -0.062]},
               "R": {"tip": [-0.0171, 0.005, 0.0243], "elbow": [-0.066, -0.019, -0.027], "shoulder": [-0.047, 0.018, -0.062]}},
       "leg": {"L": {"tip": [0.0319, -0.0375, 0.1031], "knee": [0.032, -0.026, 0.028], "hip": [0.036, -0.058, -0.05]},
               "R": {"tip": [-0.0319, -0.0375, 0.1031], "knee": [-0.032, -0.026, 0.028], "hip": [-0.036, -0.058, -0.05]}},
       "head": {"tip": [0, 0.1141, -0.0377], "neck": [0, 0.034, -0.072], "chin": [0, 0.0, -0.006]},
       "chest": [0, -0.01, -0.07], "mouth": [0.0, -0.0005, 0.0045], "thumbR": [-0.0137, 0.0058, 0.0193]}
# womb + placenta placement at week 24 (relative to the baby's box centre), scaled by baby size for other weeks
NAVEL24 = [-0.015, -0.035, -0.015]
WOMB24 = {"c": [0, 0, 0.008], "r": [0.158, 0.205, 0.152], "pdir": [-0.026, -0.027, -0.142]}

b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def load(w):
    d = json.load(open(f'{WK}/w{w:02d}.json'))
    P = np.array(d['baby']['P'], np.float64).reshape(-1, 3); I = np.array(d['baby']['I']).reshape(-1, 3)
    return d, P, I

def weld(P, I):
    key = np.round(P / 1e-6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    Q = P[first]; T = inv[I]; n = len(Q)
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]); L = np.linalg.norm(Q[e[:, 0]] - Q[e[:, 1]], axis=1)
    G = coo_matrix((np.r_[L, L], (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    return Q, inv, G

def affine_icp(S, T, it=25):
    """Affine map (3x4) taking point set S onto point set T."""
    tree = cKDTree(T)
    s0, t0 = (S.max(0) + S.min(0)) / 2, (T.max(0) + T.min(0)) / 2; k = np.ptp(T, 0) / np.ptp(S, 0)
    A = np.c_[np.diag(k), t0 - k * s0]
    Sh = np.c_[S, np.ones(len(S))]
    for _ in range(it):
        X = Sh @ A.T; _, j = tree.query(X)
        A = np.linalg.lstsq(Sh, T[j], rcond=None)[0].T
    return A

def rig_week(w, P, I, A, H):
    """Bone weights + joints for one week; A maps week-24 points into this week, H = size ratio to week 24."""
    m = lambda p: A @ np.r_[p, 1]
    Q, inv, G = weld(P, I); geo = lambda src: dijkstra(G, indices=src, directed=False)
    near = lambda p: int(np.argmin(np.linalg.norm(Q - p, axis=1)))
    span = np.ptp(Q, 0).max()
    def tip(p, side_x, rad):
        q = m(p); c = np.linalg.norm(Q - q, axis=1) < rad * span
        if side_x: c &= np.sign(Q[:, 0]) == np.sign(side_x)
        idx = np.where(c)[0]
        return Q[idx[np.argmax(Q[idx, 2])]] if len(idx) else q
    W = {}; bones = {}; tips = {'hand': {}, 'foot': {}}
    ring = 0.0025 * H
    for side, sg in (('L', 1), ('R', -1)):
        for kind, a, b, blends, nm in (('arm', 'elbow', 'shoulder', (0.004, 0.006), ('fore', 'upper')), ('leg', 'knee', 'hip', (0.005, 0.008), ('shin', 'thigh'))):
            j = J24[kind][side]
            t = tip(j['tip'], sg, 0.10 if kind == 'arm' else 0.14)
            tips['hand' if kind == 'arm' else 'foot'][side] = t.tolist()
            g = geo(near(t)); gj = [g[near(m(j[a]))], g[near(m(j[b]))]]
            cent = []
            for gv in gj:
                r = (np.abs(g - gv) < ring) & (sg * Q[:, 0] > 0.004 * H)
                cent.append(Q[r].mean(0) if r.sum() > 3 else m(j[a if not cent else b]))
            wd = smooth(gj[0] + blends[0] * H, gj[0] - blends[0] * H, g)
            wp = np.clip(smooth(gj[1] + blends[1] * H, gj[1] - blends[1] * H, g) - wd, 0, 1)
            W[nm[0] + side] = wd; W[nm[1] + side] = wp
            bones[nm[0] + side] = {'pivot': cent[0].tolist(), 'parent': nm[1] + side}
            bones[nm[1] + side] = {'pivot': cent[1].tolist(), 'parent': 'torso'}
    a, b = m(J24['head']['neck']), m(J24['head']['chin'])
    t = (b - a) / np.linalg.norm(b - a); nrm = np.array([0, t[2], -t[1]]); nrm = nrm if nrm[1] > 0 else -nrm
    limbs = np.clip(sum(W.values()), 0, 1)
    W['head'] = smooth(-0.004 * H, 0.006 * H, (Q - a) @ nrm) * (1 - limbs)
    bones['head'] = {'pivot': ((a + b) / 2 + nrm * 0.004 * H).tolist(), 'parent': 'torso'}
    ch = m(J24['chest']); dist = np.linalg.norm(Q - ch, axis=1)
    W['chest'] = np.clip(smooth(0.06 * H, 0.03 * H, dist) * (1 - np.clip(sum(W.values()), 0, 1)), 0, 1)
    bones['chest'] = {'pivot': ch.tolist(), 'parent': 'torso'}
    part = [k for k in W if k != 'chest']; tot = sum(W[k] for k in part); over = tot > 1
    for k in part: W[k][over] /= tot[over]
    W['torso'] = np.clip(1 - sum(W[k] for k in part), 0, 1); bones['torso'] = {'pivot': [0, 0, 0], 'parent': None}
    names = list(bones)
    wq = {k: np.round(W[k][inv] * 255).astype(np.uint8) for k in names}
    return names, bones, tips, wq, {k: W[k][inv] for k in names}

def axrot(axis, deg):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); t = np.radians(deg); c, s = np.cos(t), np.sin(t); x, y, z = a
    return np.array([[c + x*x*(1-c), x*y*(1-c) - z*s, x*z*(1-c) + y*s], [y*x*(1-c) + z*s, c + y*y*(1-c), y*z*(1-c) - x*s], [z*x*(1-c) - y*s, z*y*(1-c) + x*s, c + z*z*(1-c)]])
def about(p, axis, deg):
    M = np.eye(4); R = axrot(axis, deg); M[:3, :3] = R; M[:3, 3] = p - R @ p; return M

def thumb_ik(P, Wf, bones, tips, A, H):
    m = lambda p: A @ np.r_[p, 1]
    sh = np.array(bones['upperR']['pivot']); el = np.array(bones['foreR']['pivot']); tip = np.array(tips['hand']['R'])
    AX = np.cross(el - sh, tip - el); AX /= np.linalg.norm(AX)
    fr = np.where(Wf['foreR'] > .9)[0]
    thumb = P[fr[np.argmin(np.linalg.norm(P[fr] - m(J24['thumbR']), axis=1))]]
    hd = P[Wf['head'] > .95]; hc = (hd.max(0) + hd.min(0)) / 2; hr = (hd.max(0) - hd.min(0)) / 2 * 0.93
    mouth = m(J24['mouth'])
    hand = fr[np.linalg.norm(P[fr] - tip, axis=1) < 0.02 * H]
    samp = P[hand[::4]]; samp = samp[np.linalg.norm(samp - thumb, axis=1) > 0.006 * H]; Hh = np.c_[samp, np.ones(len(samp))].T
    best = None
    for shd in range(-30, 71, 3):
        for spd in range(-40, 41, 4):
            u = about(sh, [0, 1, 0], -spd) @ about(sh, AX, shd)
            for eld in range(-70, 71, 3):
                M = u @ about(el, AX, eld); tp = (M @ np.r_[thumb, 1])[:3]; e = np.linalg.norm(tp - mouth)
                if e > 0.012 * H: continue
                q = (M @ Hh)[:3].T; inside = int(((((q - hc) / hr) ** 2).sum(1) < 1).sum())
                cost = e / H + 0.004 * inside + 1e-5 * (abs(shd) + abs(spd) + abs(eld))
                if best is None or cost < best[0]: best = (cost, shd, spd, eld)
    return {'sh': best[1], 'sp': best[2], 'el': best[3]} if best else {'sh': 0, 'sp': 0, 'el': 0}

def procrustes(A, B):
    ca, cb = A.mean(0), B.mean(0); U, S, Vt = np.linalg.svd((A - ca).T @ (B - cb)); d = np.sign(np.linalg.det(U @ Vt))
    D = np.diag([1, 1, d]); R = U @ D @ Vt; s = (S * np.diag(D)).sum() / ((A - ca) ** 2).sum()
    return lambda X: s * (X - ca) @ R + cb, s

def womb_and_placenta(d, P, H, cb, navel_hint=None):
    """Womb ellipsoid around the baby; that week's placenta pressed into the wall; cord ends."""
    E0 = cb + np.array(WOMB24['c']) * H; R = np.array(WOMB24['r']) * H
    # make sure the baby (and a turned baby) fits with room to spare
    hx, hy, hz = np.ptp(P, 0) / 2; rxz = max(hx, hz) * 1.32 + 0.03 * H
    R = np.maximum(R, [rxz, hy * 1.42, rxz])
    out = {'womb': {'c': E0.tolist(), 'r': R.tolist()}}
    if 'Placenta' not in d: return out
    Bm = np.array(d['Baby']['P']).reshape(-1, 3)
    if len(Bm) != len(P): return out
    f, _ = procrustes(Bm, P)
    PL = f(np.array(d['Placenta']['P']).reshape(-1, 3)); PLi = np.array(d['Placenta']['I'])
    C = f(np.array(d['Umbilical_Cord']['P']).reshape(-1, 3))
    dB, _ = cKDTree(P).query(C); navel = C[dB < dB.min() + 0.002 * H].mean(0)
    if navel_hint is not None: navel = navel_hint
    # orientation: fetal side faces the womb centre
    cp = PL.mean(0); ev, V = np.linalg.eigh(np.cov((PL - cp).T)); n = V[:, 0]; n = n if n @ (cb - cp) > 0 else -n
    back = (PL - cp) @ n < 0
    e = lambda X: np.sqrt((((X - E0) / R) ** 2).sum(1))
    def toE(X, k): return E0 + (X - E0) * (k / e(X))[:, None]
    tgt = toE((E0 + np.array(WOMB24['pdir']) * H)[None], 1.0)[0]
    g = (tgt - E0) / R ** 2; nin = -g / np.linalg.norm(g)
    v = np.cross(n, nin); s = np.linalg.norm(v); c = n @ nin
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); Rot = np.eye(3) + K + K @ K * ((1 - c) / max(s * s, 1e-12))
    m0 = PL[back].mean(0); P1 = (PL - m0) @ Rot.T + tgt
    P2 = P1.copy(); P2[back] = toE(P1[back], 1.004)
    sh = P2[back] - P1[back]; idx = cKDTree(P1[back]).query(P1[~back])[1]; P2[~back] = P1[~back] + sh[idx]
    # smooth the fetal side, keep it just inside the wall
    key = np.round(P2 / 1e-7).astype(np.int64); _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); inv = inv.ravel()
    Q = P2[first]; T = inv[PLi.reshape(-1, 3)]; nb = [set() for _ in range(len(Q))]
    for a_, b_, c_ in T: nb[a_] |= {b_, c_}; nb[b_] |= {a_, c_}; nb[c_] |= {a_, b_}
    nb = [np.array(sorted(x)) for x in nb]; fixed = e(Q) > 0.999
    for _ in range(6):
        avg = np.array([Q[x].mean(0) if len(x) else Q[i] for i, x in enumerate(nb)])
        Q[~fixed] = Q[~fixed] * .5 + avg[~fixed] * .5
        ee = e(Q); o = (~fixed) & (ee > 0.975); Q[o] = E0 + (Q[o] - E0) * (0.975 / ee[o])[:, None]
    P3 = Q[inv]
    # keep clear of the baby: if it touches, slide the wall point a little outwards
    clr = cKDTree(P).query(P3)[0].min()
    mat = P3[e(P3) > 0.999]; pc = mat.mean(0) if len(mat) else tgt; pr = float(np.linalg.norm(mat - pc, axis=1).max()) if len(mat) else 0.05 * H
    fetal = P3[e(P3) <= 0.999]; ins = fetal[np.argmin(np.linalg.norm(fetal - (pc + (E0 - pc) * 0.2), axis=1))] if len(fetal) else pc
    # cord path: cubic Bezier navel -> insertion, control points chosen for clearance from the body
    tree = cKDTree(P); ptree = cKDTree(P3); ts = np.linspace(0, 1, 160)
    def bez(p0, p1, p2, p3, t): t = t[:, None]; return (1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t*t*p2 + t**3*p3
    nin_c = (E0 - ins); nin_c /= np.linalg.norm(nin_c)
    belly = navel - cb; belly[1] = 0; belly = belly / (np.linalg.norm(belly) + 1e-9)
    best = None
    for sx in np.linspace(-1, 1, 9):
        for sz in np.linspace(-.4, 1, 8):
            for h in (.3, .55):
                p1 = navel + (belly * 0.05 + np.array([sx * 0.07, 0.01, sz * 0.07])) * H
                p2 = ins + nin_c * 0.05 * H + np.array([sx * 0.07 * h, 0, sz * 0.07 * h]) * H
                Cv = bez(navel, p1, p2, ins, ts); d1 = tree.query(Cv[10:])[0].min(); d2 = ptree.query(Cv[:-12])[0].min()
                inw = (e(Cv[:-25]) < 0.97).all()
                sc = min(d1, d2) + (0 if inw else -1)
                if best is None or sc > best[0]: best = (sc, p1, p2)
    out.update({'placenta': {'p': b64(P3.astype(np.float32)), 'i': b64(PLi.astype(np.uint16)), 'clear': round(float(clr), 4)},
                'cord': {'navel': navel.tolist(), 'c1': best[1].tolist(), 'c2': best[2].tolist(), 'ins': ins.tolist(), 'r': 0.0042 * H, 'clear': round(float(best[0]), 4)}})
    out['womb'].update({'pc': pc.tolist(), 'pr': pr})
    return out

def main(weeks):
    _, P24, I24 = load(24); size24 = np.linalg.norm(np.ptp(P24, 0))
    man = {}
    for w in weeks:
        d, P, I = load(w); H = np.linalg.norm(np.ptp(P, 0)) / size24; cb = (P.max(0) + P.min(0)) / 2
        rec = {'v': 1, 'w': w, 'n': len(P), 'size': float(np.ptp(P, 0).max())}
        if w >= 9:
            A = np.c_[np.eye(3), np.zeros(3)] if w == 24 else affine_icp(P24, P)
            names, bones, tips, wq, Wf = rig_week(w, P, I, A, H)
            rec.update({'names': names, 'bones': bones, 'tips': tips, 'wb': {k: b64(v) for k, v in wq.items()},
                        'ik': thumb_ik(P, Wf, bones, tips, A, H)})
            # navel: week-24 navel carried over, then put on the belly surface (torso skin, just outside it)
            nv = A @ np.r_[NAVEL24, 1]; tor = np.where(Wf['torso'] > .9)[0]; k = tor[np.argmin(np.linalg.norm(P[tor] - nv, axis=1))]
            navel = P[k]
        else: navel = None
        rec.update(womb_and_placenta(d, P, H, cb, navel))
        rec['centre'] = cb.tolist()
        s = json.dumps(rec, separators=(',', ':')).encode()
        name = f'pbr-w{w:02d}.{hashlib.sha256(s).hexdigest()[:8]}.json'
        for old in os.listdir(OUT):
            if old.startswith(f'pbr-w{w:02d}.') : os.remove(os.path.join(OUT, old))
        open(os.path.join(OUT, name), 'wb').write(s); man[str(w)] = name
        print(w, name, len(s) // 1024, 'KB', 'ik', rec.get('ik'), 'placenta clear', rec.get('placenta', {}).get('clear'), 'cord clear', rec.get('cord', {}).get('clear'), file=sys.stderr)
    print(json.dumps(man))

if __name__ == '__main__':
    ws = [int(x) for x in sys.argv[1:]] or list(range(6, 41))
    main(ws)
