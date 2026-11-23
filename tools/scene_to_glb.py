"""Turn a scene exported from the 3D design harness (JSON: parts with positions, normals, baked colours)
into a close-up model in the same shape as the other close-ups: one node per structure, with extras
{anatomy_kind, display_name, description, system, source}. Then compress it with gltfpack (meshopt).

    python3 tools/scene_to_glb.py scene.json web/a/x-ear  "Source line"
"""
import hashlib, json, os, struct, subprocess, sys, glob
import numpy as np


def weld(P, N, C):
    key = np.round(P / (np.abs(P).max() * 1e-6 + 1e-12)).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return P[first], N[first], C[first], inv.ravel().astype(np.uint32)


def main(src, out_stem, source, simplify=None, yaw=0, pitch=0):
    """yaw, pitch: the design view (degrees) to turn to the front, so the close-up opens on that view"""
    y, pt = np.radians(float(yaw)), np.radians(float(pitch))
    Ry = np.array([[np.cos(-y), 0, np.sin(-y)], [0, 1, 0], [-np.sin(-y), 0, np.cos(-y)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(pt), -np.sin(pt)], [0, np.sin(pt), np.cos(pt)]])
    ROT = Rx @ Ry
    d = json.load(open(src))
    parts = d['parts']
    for p in parts:
        p['pos'] = (np.array(p['pos'], np.float64).reshape(-1, 3) @ ROT.T).ravel().tolist()
        p['nrm'] = (np.array(p['nrm'], np.float64).reshape(-1, 3) @ ROT.T).ravel().tolist()
    allp = np.concatenate([np.array(p['pos'], np.float64).reshape(-1, 3) for p in parts])
    c = (allp.min(0) + allp.max(0)) / 2
    size = (allp.max(0) - allp.min(0)).max()
    k = 0.3 / size                                   # every close-up is stored about 30 cm across; the viewer scales it
    nodes, meshes, acc, views, mats, bins = [], [], [], [], [], bytearray()
    def view(b, t):
        nonlocal bins
        o = len(bins); bins += b; bins += b'\0' * ((-len(bins)) % 4)
        views.append({'buffer': 0, 'byteOffset': o, 'byteLength': len(b), 'target': t}); return len(views) - 1
    groups = {}
    for p in parts:
        groups.setdefault(p['name'] or 'Part', []).append(p)
    for name, ps in groups.items():
        prims = []
        for p in ps:
            P = (np.array(p['pos'], np.float64).reshape(-1, 3) - c) * k
            N = np.array(p['nrm'], np.float32).reshape(-1, 3)
            C = np.array(p['col'], np.float32).reshape(-1, 3)
            P, N, C, I = weld(P, N, C)
            P = P.astype(np.float32)
            a0 = len(acc)
            acc += [{'bufferView': view(P.tobytes(), 34962), 'componentType': 5126, 'count': len(P), 'type': 'VEC3', 'min': P.min(0).tolist(), 'max': P.max(0).tolist()},
                    {'bufferView': view(N.tobytes(), 34962), 'componentType': 5126, 'count': len(N), 'type': 'VEC3'},
                    {'bufferView': view(C.tobytes(), 34962), 'componentType': 5126, 'count': len(C), 'type': 'VEC3'},
                    {'bufferView': view(I.tobytes(), 34963), 'componentType': 5125, 'count': len(I), 'type': 'SCALAR'}]
            m = {'name': f'm{len(mats)}', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, float(p['opacity'])], 'metallicFactor': 0, 'roughnessFactor': float(p['rough'])},
                 'doubleSided': p['side'] == 'double', 'extensions': {'KHR_materials_clearcoat': {'clearcoatFactor': float(p['clear']), 'clearcoatRoughnessFactor': 0.3}}}
            if p['opacity'] < 1: m['alphaMode'] = 'BLEND'
            mats.append(m)
            prims.append({'attributes': {'POSITION': a0, 'NORMAL': a0 + 1, 'COLOR_0': a0 + 2}, 'indices': a0 + 3, 'material': len(mats) - 1})
        meshes.append({'primitives': prims, 'name': name})
        p0 = ps[0]
        nodes.append({'mesh': len(meshes) - 1, 'name': name})
        nodes.append({'name': name.replace(' ', '_'), 'children': [len(nodes) - 1],
                      'extras': {'anatomy_kind': p0['kind'], 'display_name': name, 'description': p0['desc'], 'system': p0.get('system') or '', 'source': source}})
    nodes.append({'name': os.path.basename(out_stem), 'children': [i for i, n in enumerate(nodes) if 'extras' in n],
                  'extras': {'metres_per_unit': d.get('meta', {}).get('mpu', 0) / k if d.get('meta', {}).get('mpu') else None}})
    gl = {'asset': {'version': '2.0', 'generator': 'Urban Health scene_to_glb.py'}, 'extensionsUsed': ['KHR_materials_clearcoat'], 'scene': 0,
          'scenes': [{'nodes': [len(nodes) - 1]}], 'nodes': nodes, 'meshes': meshes, 'materials': mats, 'accessors': acc, 'bufferViews': views, 'buffers': [{'byteLength': len(bins)}]}
    js = json.dumps(gl, separators=(',', ':')).encode(); js += b' ' * ((-len(js)) % 4)
    raw = out_stem + '.raw.glb'
    open(raw, 'wb').write(struct.pack('<III', 0x46546C67, 2, 28 + len(js) + len(bins)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(bins), 0x004E4942) + bytes(bins))
    tmp = out_stem + '.tmp.glb'
    args = ['gltfpack', '-i', raw, '-o', tmp, '-cc', '-kn', '-km', '-ke', '-vc', '12', '-vp', '16']
    if simplify and float(simplify) < 1: args += ['-si', str(simplify)]
    subprocess.run(args, check=True, capture_output=True)
    os.remove(raw)
    h = hashlib.sha256(open(tmp, 'rb').read()).hexdigest()[:8]
    for old in glob.glob(out_stem + '.*.glb'):
        if old != tmp: os.remove(old)
    final = f'{out_stem}.{h}.glb'; os.rename(tmp, final)
    print(os.path.basename(final), len(groups), 'structures', round(os.path.getsize(final) / 1e6, 2), 'MB')


if __name__ == '__main__':
    main(*sys.argv[1:7])
