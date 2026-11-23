"""Real body sections for the cross-section view: Visible Human Project male cryosections (US National Library of Medicine;
no licence needed since 2019; NLM asks to be acknowledged). One every 8 mm, the blue embedding gel and the label card
removed, the same crop and scale for every slice so they line up as you slide.

    python3 tools/make_sections.py /path/to/a_vm####.png ...   (downloaded from data.lhncbc.nlm.nih.gov)
writes web/a/vh/vh-####.<h>.webp and web/a/vh-sections.<h>.json
"""
import glob, hashlib, io, json, os, re, sys
import numpy as np
from PIL import Image
from scipy import ndimage

A = os.path.join(os.path.dirname(__file__), '..', 'web', 'a')
OUT = os.path.join(A, 'vh')
CROP = (0.06, 0.0, 0.94, 0.80)        # x0, y0, x1, y1 of the 2048 x 1216 frame: the table, without the label card
W = 640


def process(path):
    im = Image.open(path).convert('RGB'); im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)   # work at half size: plenty for a 640 px picture
    a = np.asarray(im).astype(np.int16)
    H0, W0 = a.shape[:2]
    x0, y0, x1, y1 = int(CROP[0] * W0), int(CROP[1] * H0), int(CROP[2] * W0), int(CROP[3] * H0)
    a = a[y0:y1, x0:x1]; r, g, b = a[..., 0], a[..., 1], a[..., 2]
    gel = (b > r + 15) & (b > 50)   # the blue gel, pale where it is thin; fat and muscle are never bluer than red
    dark = a.max(-1) < 45
    tissue = ~gel & ~dark
    tissue = ndimage.binary_opening(tissue, iterations=1)
    lab, n = ndimage.label(tissue)
    if n:
        sizes = ndimage.sum(tissue, lab, range(1, n + 1))
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}   # the label card and table corners touch the frame; the body never does
        ok = [i + 1 for i in range(n) if sizes[i] > 750 and ((i + 1) not in edge or sizes[i] > 0.05 * lab.size)]   # small bits on the frame edge go; the body stays even if gel joins it to the edge
        keep = np.isin(lab, ok)
    else:
        keep = tissue
    keep = ndimage.binary_fill_holes(keep)
    keep = ndimage.binary_dilation(keep, iterations=1)
    alpha = ndimage.gaussian_filter(keep.astype(np.float32), .8)
    rgba = np.dstack([a.clip(0, 255).astype(np.uint8), (alpha * 255).clip(0, 255).astype(np.uint8)])
    # the slices are photographed with the back at the top; flip so the front is at the top and the right side on the left,
    # the way CT scans are shown (seen from the feet)
    out = Image.fromarray(rgba, 'RGBA').transpose(Image.FLIP_TOP_BOTTOM)
    h = round(out.height * W / out.width)
    return out.resize((W, h), Image.LANCZOS), keep.any()


def main(files):
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, 'vh-*.webp')): os.remove(old)
    man = {}
    for f in sorted(files):
        n = int(re.search(r'vm(\d+)', f).group(1))
        img, ok = process(f)
        if not ok: continue
        buf = io.BytesIO(); img.save(buf, 'WEBP', quality=78, method=6); d = buf.getvalue()
        name = f'vh-{n}.{hashlib.sha256(d).hexdigest()[:8]}.webp'
        open(os.path.join(OUT, name), 'wb').write(d); man[n] = '/a/vh/' + name
    js = json.dumps({'source': 'Visible Human Project, US National Library of Medicine', 'mm_per_slice': 1, 'first': 1001, 'last': 2878,
                     'w': W, 'slices': man}, separators=(',', ':')).encode()
    h = hashlib.sha256(js).hexdigest()[:8]
    for old in glob.glob(os.path.join(A, 'vh-sections.*.json')): os.remove(old)
    open(os.path.join(A, f'vh-sections.{h}.json'), 'wb').write(js)
    print(len(man), 'slices', f'/a/vh-sections.{h}.json', round(sum(os.path.getsize(os.path.join(OUT, os.path.basename(v))) for v in man.values()) / 1e6, 1), 'MB')


if __name__ == '__main__':
    main(sys.argv[1:])
