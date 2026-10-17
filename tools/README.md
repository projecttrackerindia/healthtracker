# Build tools (reference only)

These scripts produced `web/` from the single-file prototype. You do **not** need them to run or deploy the app.

| File | What it does |
| --- | --- |
| `integrate.py` | Applies the app modules in `modules/` to the prototype HTML (hand warp, Heart Lab credit, page routing, pregnancy shortcut). |
| `slim.py` | Splits the prototype into the small shell plus fingerprinted assets in `web/a/`, self-hosts fonts, writes the service worker, and pre-compresses text files (Brotli and gzip). |
| `modules/` | App code that `integrate.py` injects. `fwarp_hand.js` + `fwarp_H.json` hold the female hand fit. |
| `anatomy/` | Mesh builders (body, heart, cartilage) including the Light detail tier. They need the Z-Anatomy and HuBMAP source files, which are not in this repository. |
| `hand/` | Offline tools used to fit and check the female hand mapping. |

Paths inside the scripts point at the original build machine (`/home/claude/work`); change them before re-running.
Rebuilding the models requires downloading the CC BY-SA 4.0 Z-Anatomy data again; the finished models are already in `web/a/`.
