"""The Android apps: Digital Asset Links proves the site and the apps share an owner, and the APKs download."""
from fastapi.testclient import TestClient

import server


def test_assetlinks_lists_both_apps():
    c = TestClient(server.app)
    r = c.get("/.well-known/assetlinks.json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    pkgs = {e["target"]["package_name"]: e for e in r.json()}
    assert set(pkgs) == {"in.urbanhealth.app", "in.urbanhealth.partner"}
    for e in pkgs.values():
        assert e["relation"] == ["delegate_permission/common.handle_all_urls"]
        assert all(len(f.split(":")) == 32 for f in e["target"]["sha256_cert_fingerprints"])


def test_apks_download_and_unknown_names_do_not():
    c = TestClient(server.app)
    for name in ("urbanhealth.apk", "urbanhealth-partner.apk"):
        r = c.get(f"/download/{name}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/vnd.android.package-archive"
        assert "attachment" in r.headers["content-disposition"] and r.content[:2] == b"PK"
    assert c.get("/download/../server.py").status_code == 404
    assert c.get("/download/other.apk").status_code == 404
