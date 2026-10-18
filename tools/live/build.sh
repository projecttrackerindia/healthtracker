#!/bin/sh
# Since round 6, web/index.html on main IS the source (fixes were committed to it directly).
# New layers apply on top of the current file: python3 tools/live/p5.py (idempotent: refuses to apply twice).
# Do not rebuild from the old base (40871ca); that would drop the direct fixes.
set -e
cd "$(dirname "$0")/../.."
python3 tools/live/p5.py >/dev/null || true
python3 tools/compress.py --check && echo "web/index.html up to date"
