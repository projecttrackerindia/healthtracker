"""Cut the eye socket and the visual pathway out of the HD body model into a small asset for the 3D eye page.

    python tools/eye/orbit_asset.py        ->  web/a/eye-orbit.<hash>.bin   (prints the file name)

Coordinates are millimetres in the eye's own frame: +Y looks forward through the cornea, +Z points to the nose,
+X points up; the optic nerve leaves the globe level with the fovea (the model's slight tilt is removed).
Format (same as the body models): gzip( u32 header length | JSON header | per part: u16 xyz quantised to the part's
bounding box, then u16 triangle indices ).
"""
from __future__ import annotations

import gzip, hashlib, json, struct, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "web" / "a"
SRC, NAMES = A / "body-hd.5098f0cf.bin", A / "names.f459bcee.json"

ORB = ["rectus muscle", "oblique muscle", "levator palpebrae", "lacrimal gland", "lacrimal canaliculus", "lacrimal sac",
       "nasolacrimal duct", "optic nerve II", "oculomotor nerve III", "trochlear nerve IV", "abducens nerve VI", "ophthalmic nerve",
       "ophthalmic artery", "ophthalmic vein", "ciliary arteries", "central retinal artery", "lacrimal artery", "trochlea of superior oblique"]
PATH = ["Left optic nerve II", "Right optic chiasm", "Left optic chiasm", "Right optic tract", "Left optic tract", "Right lateral geniculate body",
        "Left lateral geniculate body", "Right calcarine sulcus", "Left calcarine sulcus", "Right cuneus", "Left cuneus", "Right lingual gyrus",
        "Left lingual gyrus", "Right occipital pole", "Left occipital pole"]


def main() -> str:
    buf = gzip.open(SRC).read()
    jl = struct.unpack("<I", buf[:4])[0]
    meta = json.loads(buf[4:4 + jl]); base = 4 + jl
    names = json.load(open(NAMES)); P = meta["parts"]; idx = {n: k for k, n in enumerate(names)}

    def G(k):
        p = P[k]; v, i, b = p["v"], p["i"], p["b"]; o = base + p["o"]
        q = np.frombuffer(buf, dtype="<u2", count=v * 3, offset=o).reshape(-1, 3).astype(np.float64)
        ix = np.frombuffer(buf, dtype="<u2", count=i, offset=o + v * 6).astype(np.int64)
        lo, hi = np.array(b[:3]), np.array(b[3:]); return lo + q / 65535 * (hi - lo), ix.reshape(-1, 3)

    def cen(n):
        p, _ = G(idx[n]); return (p.min(0) + p.max(0)) / 2

    sc = cen("Right sclera"); ps, _ = G(idx["Right sclera"]); R = np.percentile(np.linalg.norm(ps - sc, axis=1), 60)
    fw = cen("Right anterior segment of eyeball") - cen("Right posterior segment of eyeball"); fw /= np.linalg.norm(fw)
    nas = np.array([1.0, 0, 0]); nas -= fw * nas.dot(fw); nas /= np.linalg.norm(nas); up = np.cross(fw, nas)
    s = 12.0 / R; M = np.stack([up, fw, nas])
    t0 = lambda p: (p - sc) @ M.T * s
    pn = t0(G(idx["Right optic nerve II"])[0]); dn = np.linalg.norm(pn, axis=1); st = pn[(dn > 12.5) & (dn < 14.5)].mean(0)
    al = np.arctan2(st[0], -st[1]); ca, sa = np.cos(al), np.sin(al); Rz = np.array([[ca, sa, 0], [-sa, ca, 0], [0, 0, 1]])
    tomm = lambda p: t0(p) @ Rz.T

    want = [n for n in names if n.startswith("Right ") and any(w in n for w in ORB) and "nucleus" not in n] + PATH
    parts, blobs, off = [], [], 0
    for n in want:
        if n not in idx:
            continue
        p, t = G(idx[n]); pm = tomm(p)
        u, inv = np.unique(t.ravel(), return_inverse=True); pm = pm[u]; t = inv.reshape(-1, 3)
        lo, hi = pm.min(0), pm.max(0); q = np.round((pm - lo) / np.maximum(hi - lo, 1e-6) * 65535).astype("<u2")
        b = q.tobytes() + t.astype("<u2").tobytes()
        parts.append({"n": n, "v": len(pm), "i": int(t.size), "o": off, "b": [round(float(x), 4) for x in (*lo, *hi)]}); blobs.append(b); off += len(b)
    pn = tomm(G(idx["Right optic nerve II"])[0]); g = pn[np.abs(pn[:, 1] + 21) < 1.5].mean(0)
    rec = np.concatenate([tomm(G(idx["Right " + n])[0]) for n in ("lateral rectus muscle", "medial rectus muscle", "superior rectus muscle", "inferior rectus muscle")])
    k = float((np.percentile(np.linalg.norm(rec, axis=1), 4) - 0.4) / 12.0)
    head = json.dumps({"parts": parts, "ganglion": [round(float(x), 3) for x in (g[0], g[1], g[2] - 2.6)], "eyeK": round(k, 4)}, separators=(",", ":")).encode()
    head += b" " * ((-(4 + len(head))) % 4)  # keep the data 4-byte aligned for typed arrays
    raw = struct.pack("<I", len(head)) + head + b"".join(blobs)
    gz = gzip.compress(raw, 9, mtime=0)
    h = hashlib.sha256(gz).hexdigest()[:8]
    for old in A.glob("eye-orbit.*.bin"):
        old.unlink()
    out = A / f"eye-orbit.{h}.bin"; out.write_bytes(gz)
    print(out.name, len(gz), "bytes,", len(parts), "parts", file=sys.stderr)
    return out.name


if __name__ == "__main__":
    print(main())
