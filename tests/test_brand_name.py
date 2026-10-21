"""The old product name must not reach a user's screen, however it is spelled across markup.

This exists because the rename missed the same way four times, and a plain grep for "thehealthtracker"
returned zero every time:

    <b>the<span>health</span>tracker</b>     the splash and the auth header
    <b>the<i>health</i>tracker</b>           the health card
    the<span style="...">health</span>tracker   the header of every transactional email
    "Health tracker ID"                      the label on the member card

Each one renders as the old name and none of them contains it as a literal string. So this test flattens the
markup first and then looks, which is the only way to see what a person actually sees.

Run: python -m pytest -q tests/test_brand_name.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Everything a person can see: pages, the live layers they are built from, and the Python that renders email.
SURFACES = (
    list((ROOT / "web").glob("*.html")) + list((ROOT / "web").glob("*.js")) +
    list((ROOT / "site").glob("*.html")) + list((ROOT / "site").glob("*.js")) +
    [ROOT / "admin" / "index.html", ROOT / "tech" / "index.html", ROOT / "counter" / "index.html"] +
    list((ROOT / "partner").glob("*.html")) +
    [p for p in (ROOT / "tools" / "live").glob("*") if p.suffix in (".js", ".py", ".html")] +
    list((ROOT / "api").glob("*.py"))
)

# Deliberate survivals, each with the reason it has to stay.
ALLOWED = {
    "api/passwords.py": "healthtracker must stay banned as a password — it is still the obvious one for this product",
    "site/auth.js": "same banned-password list, client side",
    "api/apps.py": "the GitHub repo slug is still projecttrackerindia/healthtracker; the release URL is real",
}


def _flatten(s: str) -> str:
    """What the text reads as once markup and template punctuation are gone."""
    s = re.sub(r"<[^>]{1,200}>", "", s)
    return re.sub(r"[\s'\"`+${}()\\,.:;|/-]", "", s)


def _surfaces():
    for p in SURFACES:
        if p.exists() and p.is_file():
            yield p, str(p.relative_to(ROOT))


def test_no_surface_renders_the_old_product_name():
    bad = []
    for p, rel in _surfaces():
        if rel in ALLOWED:
            continue
        flat = _flatten(p.read_text(errors="ignore")).lower()
        if "thehealthtracker" in flat:
            bad.append(rel)
    assert not bad, (
        "the old product name still renders on: " + ", ".join(bad) +
        " — check for it split across tags, e.g. the<span>health</span>tracker"
    )


def test_no_surface_still_calls_the_card_a_health_tracker_id():
    """The member card's ID label carried the old name as ordinary words, so tag-flattening alone missed it."""
    bad = [rel for p, rel in _surfaces()
           if rel not in ALLOWED and re.search(r"health\s*tracker\s*id", p.read_text(errors="ignore"), re.I)]
    assert not bad, "the card ID is still labelled with the old name on: " + ", ".join(bad)


def test_no_surface_points_at_the_old_domain():
    bad = [rel for p, rel in _surfaces()
           if rel not in ALLOWED and "thehealthtracker.com" in p.read_text(errors="ignore").lower()]
    assert not bad, "the old domain is still referenced on: " + ", ".join(bad)


def test_the_allowlist_is_not_stale():
    """If one of the deliberate survivals disappears, this test says so rather than quietly protecting nothing."""
    for rel, why in ALLOWED.items():
        p = ROOT / rel
        assert p.exists(), f"{rel} is allowlisted but gone"
        assert "healthtracker" in p.read_text(errors="ignore").lower(), \
            f"{rel} no longer contains the old name, so its allowlist entry can go ({why})"
