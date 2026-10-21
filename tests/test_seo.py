"""The site has to be findable, and findable exactly once.

The app answers on two addresses: urbanhealth.in and the Cloud Run URL it is actually deployed to. Both serve
identical HTML. If a crawler reaches the Cloud Run one, Google ends up holding two copies of the same site and
picks a winner on its own — usually the one it found first, which is the ugly one. So everything here is really
one rule checked from several angles: only the canonical host is allowed into an index.

The structured-data test is a different kind of guard. Invented review counts and prices are the quickest way to
earn a manual action, and they are tempting to add because they make a search result look busier. This asserts
they are absent.

Run: python -m pytest -q tests/test_seo.py
"""
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_seo.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

CANON = "urbanhealth.in"
ROOT = Path(server.__file__).resolve().parent


@pytest.fixture
def live(monkeypatch):
    """The app as it answers in production, on the canonical host."""
    monkeypatch.setattr(server, "CANONICAL", CANON)
    monkeypatch.setenv("APP_ENV", "production")
    with TestClient(server.app, base_url=f"https://{CANON}") as c:
        yield c


@pytest.fixture
def other(monkeypatch):
    """The same app answering on the Cloud Run address."""
    monkeypatch.setattr(server, "CANONICAL", CANON)
    monkeypatch.setenv("APP_ENV", "production")
    with TestClient(server.app, base_url="https://tht-88456779070.asia-south1.run.app") as c:
        yield c


# ---------------------------------------------------------------- robots.txt

def test_robots_on_the_real_address_points_at_the_sitemap(live):
    r = live.get("/robots.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert f"Sitemap: https://{CANON}/sitemap.xml" in r.text


def test_robots_keeps_crawlers_out_of_every_signed_in_surface(live):
    body = live.get("/robots.txt").text
    for path in ("/app", "/partner", "/admin", "/counter", "/api/"):
        assert f"Disallow: {path}" in body, path


def test_robots_blocks_the_paths_that_serve_the_landing_html_again(live):
    """/signin, /signup, /reset and /join/<token> all return the landing page — duplicate content."""
    body = live.get("/robots.txt").text
    for path in ("/signin", "/signup", "/reset", "/join/"):
        assert f"Disallow: {path}" in body, path


def test_the_cloud_run_address_is_closed_to_crawlers_completely(other):
    body = other.get("/robots.txt").text
    assert body.strip() == "User-agent: *\nDisallow: /"
    assert "Sitemap" not in body


def test_a_non_production_environment_is_closed_too(monkeypatch):
    monkeypatch.setattr(server, "CANONICAL", CANON)
    monkeypatch.setenv("APP_ENV", "staging")
    with TestClient(server.app, base_url=f"https://{CANON}") as c:
        assert "Disallow: /" in c.get("/robots.txt").text
        assert "Sitemap" not in c.get("/robots.txt").text


# ---------------------------------------------------------------- X-Robots-Tag

def test_the_cloud_run_address_sends_noindex_on_the_page_itself(other):
    """robots.txt only stops a crawl. A page already in the index needs the header to fall out of it."""
    assert "noindex" in other.get("/").headers.get("X-Robots-Tag", "")


def test_the_real_address_does_not_send_noindex(live):
    assert "noindex" not in live.get("/").headers.get("X-Robots-Tag", "")


# ---------------------------------------------------------------- sitemap.xml

def test_the_sitemap_is_well_formed_and_lists_the_public_pages(live):
    r = live.get("/sitemap.xml")
    assert r.status_code == 200
    root = ET.fromstring(r.text)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in root.findall(".//s:loc", ns)]
    assert locs == [f"https://{CANON}/", f"https://{CANON}/privacy", f"https://{CANON}/terms"]


def test_every_page_in_the_sitemap_actually_answers(live):
    root = ET.fromstring(live.get("/sitemap.xml").text)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in [e.text for e in root.findall(".//s:loc", ns)]:
        path = loc.replace(f"https://{CANON}", "") or "/"
        assert live.get(path).status_code == 200, path


def test_lastmod_is_a_real_date_from_the_file_not_the_clock(live):
    """A lastmod that moves on every restart teaches Google to ignore the field."""
    body = live.get("/sitemap.xml").text
    dates = re.findall(r"<lastmod>([^<]+)</lastmod>", body)
    assert dates, "no lastmod at all"
    for d in dates:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", d), d
    assert live.get("/sitemap.xml").text == body     # stable across calls


def test_the_sitemap_never_advertises_a_blocked_path(live):
    locs = re.findall(r"<loc>([^<]+)</loc>", live.get("/sitemap.xml").text)
    for loc in locs:
        path = loc.replace(f"https://{CANON}", "") or "/"
        assert not any(path.startswith(b) for b in server.CRAWL_BLOCKED if b != "/"), path


# ---------------------------------------------------------------- the pages themselves

@pytest.mark.parametrize("path,expected", [
    ("/", f"https://{CANON}/"),
    ("/privacy", f"https://{CANON}/privacy"),
    ("/terms", f"https://{CANON}/terms"),
])
def test_each_public_page_names_its_own_canonical(live, path, expected):
    html = live.get(path).text
    assert f'<link rel="canonical" href="{expected}">' in html


def test_the_duplicate_paths_point_back_at_the_landing_page(live):
    """/signin serves the landing HTML, so its canonical has to say so."""
    for path in ("/signin", "/signup", "/reset"):
        assert f'<link rel="canonical" href="https://{CANON}/">' in live.get(path).text, path


def test_the_share_image_is_absolute_and_present(live):
    html = live.get("/").text
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    assert m, "no og:image"
    assert m.group(1).startswith("https://"), "a relative og:image does not render on most platforms"
    assert (ROOT / "site" / "img" / "og.png").exists()


def test_the_share_image_is_the_size_the_platforms_want(live):
    html = live.get("/").text
    assert '<meta property="og:image:width" content="1200">' in html
    assert '<meta property="og:image:height" content="630">' in html


# ---------------------------------------------------------------- structured data

def _ld(html):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert m, "no JSON-LD on the landing page"
    return json.loads(m.group(1))


def test_the_structured_data_parses(live):
    g = _ld(live.get("/").text)
    assert g["@context"] == "https://schema.org"
    assert {n["@type"] for n in g["@graph"]} == {"Organization", "WebSite", "SoftwareApplication"}


def test_the_structured_data_claims_no_ratings_and_no_price(live):
    """There are no reviews and no published price yet. Inventing either is what earns a manual action."""
    blob = json.dumps(_ld(live.get("/").text))
    for forbidden in ("aggregateRating", "ratingValue", "reviewCount", "offers", "price"):
        assert forbidden not in blob, forbidden


def test_the_structured_data_uses_the_canonical_address_throughout(live):
    blob = json.dumps(_ld(live.get("/").text))
    assert "run.app" not in blob
    assert blob.count(f"https://{CANON}") >= 4


# ---------------------------------------------------------------- security.txt

def test_security_txt_is_absent_until_there_is_a_mailbox_behind_it(live, monkeypatch):
    """A contact address that bounces is worse than no file: the finder usually gives up instead of retrying."""
    monkeypatch.delenv("SECURITY_EMAIL", raising=False)
    monkeypatch.delenv("SUPPORT_EMAIL", raising=False)
    assert live.get("/.well-known/security.txt").status_code == 404


def test_security_txt_is_valid_when_configured(live, monkeypatch):
    monkeypatch.setenv("SECURITY_EMAIL", "security@urbanhealth.in")
    r = live.get("/.well-known/security.txt")
    assert r.status_code == 200
    assert "Contact: mailto:security@urbanhealth.in" in r.text
    assert f"Canonical: https://{CANON}/.well-known/security.txt" in r.text
    expires = re.search(r"Expires: (\S+)", r.text).group(1)
    from datetime import datetime as _dt, timezone as _tz
    assert _dt.fromisoformat(expires.replace("Z", "+00:00")) > _dt.now(_tz.utc), "an expired security.txt is invalid"


def test_security_txt_falls_back_to_the_support_address(live, monkeypatch):
    monkeypatch.delenv("SECURITY_EMAIL", raising=False)
    monkeypatch.setenv("SUPPORT_EMAIL", "support@urbanhealth.in")
    assert "mailto:support@urbanhealth.in" in live.get("/.well-known/security.txt").text
