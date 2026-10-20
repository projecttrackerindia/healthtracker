"""Round 28: Hindi and Telugu. Run: python -m pytest -q tests/test_round28.py"""
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round28.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "i18n"))
from core import CORE  # noqa: E402


def test_core_is_well_formed_and_matches_real_phrases():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    phrases = {p.replace("\\'", "'") for p in re.findall(r"P\('((?:[^'\\]|\\.)*)'\)", html)}
    assert len(CORE) >= 300
    hindi = re.compile(r"[ऀ-ॿ]"); telugu = re.compile(r"[ఀ-౿]")
    for en, (hi, te) in CORE.items():
        assert isinstance(hi, str) and isinstance(te, str) and hi.strip() and te.strip(), en
        assert hindi.search(hi) or en in ("SOS", "OK", "cm", "kg", "vs"), ("hindi?", en, hi)
        assert telugu.search(te) or en in ("SOS", "OK", "vs"), ("telugu?", en, te)
    missing = [k for k in CORE if k not in phrases]
    assert len(missing) <= 12, missing[:20]   # a few are fragments of SX.D() strings; the rest must be real P() keys


def test_table_served_and_inline_core_in_page():
    c = TestClient(server.app)
    r = c.get("/api/v1/i18n")
    assert r.status_code == 200 and r.headers["x-i18n-source"] in ("repo", "bucket")
    j = r.json()
    assert j["Sign in"] == ["साइन इन", "సైన్ ఇన్"] and j["SOS active"][1] == "SOS యాక్టివ్"
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p28*/" in html and "సైన్ ఇన్" in html and "/api/v1/i18n" in html and "data-sx=\"lang:${k}\"" in html
    assert json.loads((ROOT / "site" / "i18n" / "phrases.json").read_text(encoding="utf-8"))["Home"] == ["होम", "హోమ్"]
