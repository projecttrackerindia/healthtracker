"""Build the elbow, wrist, ankle and neck close-ups from the HD body (Z-Anatomy / BodyParts3D, CC BY-SA 4.0).

Each close-up is a glTF file in the same shape as the other bone close-ups: one node per structure with
extras {anatomy_kind, display_name, description, system, label_anchor}, in metres, centred on the joint.
Long bones are cut where they leave the joint's box.

    python3 tools/make_joints.py      # writes web/a/joint-<name>.<hash>.glb and prints the map for organs2.js
"""
import gzip, hashlib, json, os, re, struct, glob
import numpy as np

A = os.path.join(os.path.dirname(__file__), '..', 'web', 'a')
UNIT = 1.75 / 6.134          # metres per body unit (the body model is 6.134 units tall)

# right side of the body is -x. box = x0,y0,z0,x1,y1,z1 in body units
JOINTS = {
    'elbow': ([-1.02, 0.66, -0.26, -0.62, 1.10, 0.16], 'Right elbow'),
    'wrist': ([-1.13, -0.16, -0.24, -0.78, 0.16, 0.20], 'Right wrist'),
    'ankle': ([-0.47, -3.07, -0.40, -0.08, -2.55, 0.26], 'Right ankle'),
    'neck':  ([-0.22, 2.02, -0.36, 0.22, 2.55, 0.12], 'Neck'),
    'skull': ([-0.40, 2.30, -0.45, 0.40, 3.10, 0.45], 'Skull'),
}
# what each close-up keeps: layers, and a name filter for the busy neck
ONLY = {'neck': (2, 4, 5), 'skull': (2,)}
SKULL = re.compile(r'frontal bone|parietal bone|occipital bone|temporal bone|sphenoid bone|ethmoid bone|zygomatic bone|maxilla|mandible|nasal bone|lacrimal bone|vomer|palatine bone|inferior nasal concha|tooth|teeth|hyoid', re.I)
# sheets that hide the joint, and the main named vessels and nerves worth showing at each joint
SHEET = re.compile(r'retinacul|aponeuros|fascia|interosseous membrane|sheath', re.I)
MAIN = {'elbow': re.compile(r'^Right (brachial artery|radial artery|ulnar artery|ulnar nerve|median nerve|radial nerve)$', re.I),
        'wrist': re.compile(r'^Right (radial artery|ulnar artery|median nerve|ulnar nerve|superficial palmar arch|deep palmar arch)$', re.I),
        'ankle': re.compile(r'^Right (posterior tibial artery|anterior tibial artery|dorsalis pedis artery|fibular artery|tibial nerve|deep fibular nerve|superficial fibular nerve|sural nerve|great saphenous vein|small saphenous vein)$', re.I)}
NECK = re.compile(r'vertebra|atlas|axis|dens|disc|ligament|membrane|capsule|occipital|spinal cord|spinal nerve|root|common carotid|internal carotid|external carotid|vertebral artery|internal jugular|hyoid|thyroid cartilage|cricoid|trachea', re.I)
KEEP = {1: True, 2: True, 4: True, 5: True}


def load():
    raw = gzip.open(sorted(glob.glob(os.path.join(A, 'body-hd.*.bin')))[0]).read()
    jl = struct.unpack('<I', raw[:4])[0]
    meta = json.loads(raw[4:4 + jl])
    names = json.load(open(sorted(glob.glob(os.path.join(A, 'names.*.json')))[0]))
    onto = json.load(open(sorted(glob.glob(os.path.join(A, 'onto.*.json')))[0]))
    return raw, 4 + jl, meta['parts'], names, onto


def kind_of(l, n):
    if l == 2:
        if re.search(r'cartilage|disc|menisc|labrum', n, re.I): return 'Cartilage'
        if re.search(r'capsule', n, re.I): return 'Capsule'
        if re.search(r'ligament|membrane|retinac', n, re.I): return 'Ligament'
        return 'Bone'
    if l == 1:
        return 'Tendon' if re.search(r'tendon|aponeuros|retinacul', n, re.I) else 'Muscle'
    if l == 4: return 'Vessel'
    if l == 5: return 'Nerve'
    return 'Organ'


MAT = {  # base colour (sRGB), roughness, alpha, clearcoat
    'Bone': ((0.84, 0.77, 0.63), 0.6, 1, 0.05), 'Cartilage': ((0.62, 0.74, 0.84), 0.25, 1, 0.6),
    'Ligament': ((0.70, 0.76, 0.80), 0.35, 0.62, 0.5), 'Capsule': ((0.72, 0.80, 0.88), 0.3, 0.22, 0.6),
    'Tendon': ((0.90, 0.86, 0.76), 0.3, 1, 0.5), 'Muscle': ((0.66, 0.22, 0.19), 0.5, 1, 0.3),
    'Vessel': ((0.75, 0.13, 0.17), 0.4, 1, 0.5), 'Nerve': ((0.88, 0.73, 0.24), 0.45, 1, 0.3)}
VEIN = (0.22, 0.32, 0.74)


def clean(n):
    return re.sub(r'\s+', ' ', n).strip()


def plain(n):
    n = re.sub(r'^(left|right) ', '', n, flags=re.I)
    return n[0].upper() + n[1:]


def clip_box(V, I, b0, b1):
    """Cut a mesh with the six planes of a box, splitting the triangles that cross a plane,
    so long bones end in a straight, clean cut instead of a ragged edge."""
    V = [tuple(v) for v in V]
    tris = [tuple(t) for t in I]
    cut = False
    for ax in range(3):
        for lim, keep_below in ((b1[ax], True), (b0[ax], False)):
            ins = lambda v: (v[ax] <= lim) if keep_below else (v[ax] >= lim)
            out = []
            cache = {}
            def mid(a, b):
                key = (min(a, b), max(a, b))
                if key not in cache:
                    pa, pb = V[a], V[b]
                    t = (lim - pa[ax]) / (pb[ax] - pa[ax])
                    V.append(tuple(pa[i] + (pb[i] - pa[i]) * t for i in range(3)))
                    cache[key] = len(V) - 1
                return cache[key]
            for t in tris:
                flags = [ins(V[i]) for i in t]
                n = sum(flags)
                if n == 3:
                    out.append(t); continue
                if n == 0:
                    cut = True; continue
                cut = True
                poly = []
                for e in range(3):
                    a, b = t[e], t[(e + 1) % 3]
                    if flags[e]: poly.append(a)
                    if flags[e] != flags[(e + 1) % 3]: poly.append(mid(a, b))
                for j in range(1, len(poly) - 1):
                    out.append((poly[0], poly[j], poly[j + 1]))
            tris = out
    V = np.array(V, dtype=np.float64)
    I = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return V, I, cut


def build(key, box, title, raw, base, P, names, onto):
    b0, b1 = np.array(box[:3]), np.array(box[3:])
    c = (b0 + b1) / 2
    nodes, meshes, accessors, views, mats, bins = [], [], [], [], [], bytearray()
    matidx = {}

    def add_view(data, target=None):
        nonlocal bins
        off = len(bins)
        bins += data
        bins += b'\0' * ((-len(bins)) % 4)
        v = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
        if target: v['target'] = target
        views.append(v)
        return len(views) - 1

    kept = 0
    for k, p in enumerate(P):
        l = p.get('l', 1)
        if l not in KEEP or l not in ONLY.get(key, (1, 2, 4, 5)):
            continue
        if key == 'neck' and not NECK.search(names[k]):
            continue
        if key == 'skull' and not SKULL.search(names[k]):
            continue
        if SHEET.search(names[k]):
            continue
        if l in (4, 5) and key in MAIN and not MAIN[key].search(names[k]):
            continue
        pb = np.array(p['b'])
        if (pb[3:] < b0).any() or (pb[:3] > b1).any():
            continue
        nm = names[k]
        kd = kind_of(l, nm)
        if l == 4 and kd == 'Vessel' and p['v'] < 40:
            continue
        q = np.frombuffer(raw, dtype=np.uint16, count=p['v'] * 3, offset=base + p['o']).reshape(-1, 3) / 65535.0
        V = pb[:3] + q * (pb[3:] - pb[:3])
        I = np.frombuffer(raw, dtype=np.uint16, count=p['i'], offset=base + p['o'] + p['v'] * 6).reshape(-1, 3).astype(np.int64)
        V, I, cut = clip_box(V, I, b0, b1)
        if len(I) < 8:
            continue
        used = np.unique(I)
        remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
        V = (V[used] - c) * UNIT
        I = remap[I]
        # smooth normals
        N = np.zeros_like(V)
        fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
        for j in range(3): np.add.at(N, I[:, j], fn)
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        # baked shading: creases darker (how far a vertex sits below its neighbours), plus a faint grain
        S = np.zeros_like(V); C = np.zeros(len(V)); E = np.zeros(len(V))
        for a_, b_ in ((0, 1), (1, 2), (2, 0)):
            ia, ib = I[:, a_], I[:, b_]
            L = np.linalg.norm(V[ia] - V[ib], axis=1)
            np.add.at(S, ia, V[ib]); np.add.at(S, ib, V[ia]); np.add.at(C, ia, 1); np.add.at(C, ib, 1); np.add.at(E, ia, L); np.add.at(E, ib, L)
        C = np.maximum(C, 1)
        d = ((S / C[:, None] - V) * N).sum(1) / np.maximum(E / C, 1e-6)
        shade = 1 - 0.5 * np.clip(d * 2.4, 0, 1)
        rng = np.random.default_rng(k)
        grain = 1 + 0.05 * (np.sin(V[:, 0] * 900) * np.sin(V[:, 1] * 760) * np.sin(V[:, 2] * 820)) + 0.02 * rng.standard_normal(len(V))
        col = np.clip(np.stack([shade * grain, shade * grain * 0.98, shade * grain * 0.96], 1), 0, 1).astype(np.float32)
        V32, N32, I32 = V.astype(np.float32), N.astype(np.float32), I.astype(np.uint32).ravel()
        pv = add_view(V32.tobytes(), 34962); nv = add_view(N32.tobytes(), 34962); iv = add_view(I32.tobytes(), 34963); cv = add_view(col.tobytes(), 34962)
        accessors += [{'bufferView': pv, 'componentType': 5126, 'count': len(V32), 'type': 'VEC3', 'min': V32.min(0).tolist(), 'max': V32.max(0).tolist()},
                      {'bufferView': nv, 'componentType': 5126, 'count': len(N32), 'type': 'VEC3'},
                      {'bufferView': iv, 'componentType': 5125, 'count': len(I32), 'type': 'SCALAR'},
                      {'bufferView': cv, 'componentType': 5126, 'count': len(col), 'type': 'VEC3'}]
        a0 = len(accessors) - 4
        mk = kd + ('-vein' if kd == 'Vessel' and re.search(r'vein|venous', nm, re.I) else '')
        if mk not in matidx:
            col, rough, alpha, cc = MAT[kd]
            if mk.endswith('-vein'): col = VEIN
            lin = [((x + 0.055) / 1.055) ** 2.4 for x in col]
            m = {'name': mk, 'pbrMetallicRoughness': {'baseColorFactor': lin + [alpha], 'metallicFactor': 0, 'roughnessFactor': rough},
                 'doubleSided': kd in ('Capsule', 'Ligament'), 'extensions': {'KHR_materials_clearcoat': {'clearcoatFactor': cc, 'clearcoatRoughnessFactor': 0.3}}}
            if alpha < 1: m['alphaMode'] = 'BLEND'
            mats.append(m); matidx[mk] = len(mats) - 1
        meshes.append({'primitives': [{'attributes': {'POSITION': a0, 'NORMAL': a0 + 1, 'COLOR_0': a0 + 3}, 'indices': a0 + 2, 'material': matidx[mk]}], 'name': ''})
        # label anchor: the vertex nearest the part's middle that faces the viewer most
        mid = V32.mean(0); d = np.linalg.norm(V32[:, :2] - mid[:2], axis=1)
        near = d < max(0.004, np.percentile(d, 25))
        anchor = V32[near][np.argmax(V32[near][:, 2])].tolist() if near.any() else mid.tolist()
        on = onto.get(nm) or onto.get(clean(nm)) or ['', []]
        desc = on[0].split('. ')[0].strip() + '.' if on and on[0] else f'{plain(nm)}: part of the {title.lower()}.'
        sysname = {'Bone': 'skeletal', 'Cartilage': 'skeletal', 'Ligament': 'skeletal', 'Capsule': 'skeletal', 'Tendon': 'muscular', 'Muscle': 'muscular', 'Vessel': 'cardiovascular', 'Nerve': 'nervous'}[kd]
        o2kind = {"Cartilage": "Cartilage", "Ligament": "Connective tissue", "Capsule": "Connective tissue", "Tendon": "Connective tissue", "Vessel": ("Vein" if re.search(r"vein|venous", nm, re.I) else "Artery")}.get(kd, kd)
        nodes.append({'mesh': len(meshes) - 1, 'name': ''})
        nodes.append({'name': f'{kd}_{re.sub(r"[^A-Za-z0-9]+", "", plain(nm).title())}_{"Left" if nm.lower().startswith("left") else "Right"}',
                      'children': [len(nodes) - 1],
                      'extras': {'anatomy_kind': o2kind, 'tissue': kd, 'display_name': clean(nm), 'description': desc,
                                 'kid_description': '', 'system': sysname, 'label_anchor': [round(x, 5) for x in anchor],
                                 'source': 'Z-Anatomy / BodyParts3D (CC BY-SA 4.0)', 'cut': bool(cut and kd == 'Bone')}})
        kept += 1
    root = {'name': key, 'children': [i for i, n in enumerate(nodes) if 'extras' in n]}
    nodes.append(root)
    gl = {'asset': {'version': '2.0', 'generator': 'Urban Health make_joints.py'}, 'extensionsUsed': ['KHR_materials_clearcoat'],
          'scene': 0, 'scenes': [{'name': key, 'nodes': [len(nodes) - 1]}], 'nodes': nodes, 'meshes': meshes,
          'materials': mats, 'accessors': accessors, 'bufferViews': views, 'buffers': [{'byteLength': len(bins)}]}
    js = json.dumps(gl, separators=(',', ':')).encode(); js += b' ' * ((-len(js)) % 4)
    glb = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bins)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(bins), 0x004E4942) + bytes(bins)
    for old in glob.glob(os.path.join(A, f'joint-{key}.*.glb')): os.remove(old)
    raw = os.path.join(A, f'joint-{key}.raw.glb'); tmp = os.path.join(A, f'joint-{key}.tmp.glb')
    open(raw, 'wb').write(glb)
    import subprocess   # meshopt compression, keeping names, materials and extras (the viewer already decodes meshopt)
    subprocess.run(['gltfpack', '-i', raw, '-o', tmp, '-cc', '-kn', '-km', '-ke', '-vc', '12', '-vp', '16'], check=True, capture_output=True)
    os.remove(raw); glb = open(tmp, 'rb').read(); os.remove(tmp)
    h = hashlib.sha256(glb).hexdigest()[:8]
    name = f'joint-{key}.{h}.glb'
    open(os.path.join(A, name), 'wb').write(glb)
    print(name, kept, 'structures', round(len(glb) / 1e6, 2), 'MB')
    return '/a/' + name


def main():
    raw, base, P, names, onto = load()
    out = {k: build(k, b, t, raw, base, P, names, onto) for k, (b, t) in JOINTS.items()}
    print('const JOINTF=' + json.dumps(out, separators=(',', ':')) + ';')


if __name__ == '__main__':
    main()
