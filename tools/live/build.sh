#!/bin/sh
# Rebuild web/index.html from the base that has only the first live layer (p0), then apply p1 and p2.
set -e
cd "$(dirname "$0")/../.."
git show 40871ca:web/index.html > web/index.html
python3 tools/live/p1.py >/dev/null
python3 tools/live/p2.py >/dev/null
python3 tools/compress.py --check && echo "web/index.html rebuilt"
