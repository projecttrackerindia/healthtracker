"""Regenerate the pre-compressed copies (.br and .gz) of every text file under web/ and site/.

The server sends `index.html.br` instead of `index.html` to any browser that accepts Brotli, so an edited
`index.html` with an old `.br` beside it means users keep getting the OLD page. Run this after every edit:

    python tools/compress.py          # rewrite stale copies
    python tools/compress.py --check  # exit 1 if any copy is stale (use in CI / before pushing)

server.py also checks at start-up and never serves a stale copy, so a forgotten run cannot reach users.
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = [ROOT / "web", ROOT / "site"]
TEXT = {".html", ".js", ".css", ".json", ".svg", ".webmanifest", ".txt"}

try:
    import brotli  # type: ignore
except ImportError:  # pragma: no cover
    brotli = None


def sources():
    for d in DIRS:
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in TEXT:
                yield p


def stale(src: Path) -> list[Path]:
    data = src.read_bytes()
    out = []
    for suf, dec in ((".br", brotli.decompress if brotli else None), (".gz", gzip.decompress)):
        alt = src.with_name(src.name + suf)
        if not alt.exists():
            continue
        try:
            if dec is None or dec(alt.read_bytes()) != data:
                out.append(alt)
        except Exception:
            out.append(alt)
    return out



def main() -> int:
    check = "--check" in sys.argv
    bad = [(s, a) for s in sources() for a in stale(s)]
    if check:
        for s, a in bad:
            print(f"STALE {a.relative_to(ROOT)}")
        return 1 if bad else 0
    if not brotli:
        print("pip install brotli first", file=sys.stderr)
        return 2
    done = set()
    for s, a in bad:
        if s in done:
            continue
        data = s.read_bytes()
        for suf in (".br", ".gz"):
            alt = s.with_name(s.name + suf)
            # .br and .gz are a pair: a file with only a .br leaves every browser that does not accept brotli
            # downloading the raw original. index.html was 1.57 MB that way. Create the missing twin.
            if not alt.exists() and not s.with_name(s.name + (".gz" if suf == ".br" else ".br")).exists():
                continue  # this file is not meant to have pre-compressed copies at all
            if suf == ".br":
                alt.write_bytes(brotli.compress(data, quality=11))
            else:
                alt.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
        done.add(s)
        print(f"refreshed {s.relative_to(ROOT)}")
    print(f"{len(done)} file(s) refreshed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
