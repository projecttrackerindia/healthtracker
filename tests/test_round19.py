"""Round 19: Withings/Oura clouds and the native Bluetooth bridge. Run: python -m pytest -q tests/test_round19.py"""
import os
import shutil
import subprocess
import uuid
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round19.db"
for k in ("WITHINGS_CLIENT_ID", "WITHINGS_CLIENT_SECRET", "OURA_CLIENT_ID", "OURA_CLIENT_SECRET"):
    os.environ.pop(k, None)

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import wearables  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def household(c):
    key = "k" + uuid.uuid4().hex[:28]
    r = c.post("/api/v1/hello", headers={**H, "x-dokko-key": key}, json={})
    assert r.status_code == 200, r.text
    return key


# ---------------------------------------------------------------- normalisers
def test_withings_measures_become_readings():
    meas = {"measuregrps": [
        {"grpid": 1, "date": 1700000000, "measures": [{"type": 10, "value": 1284, "unit": -1}, {"type": 9, "value": 82, "unit": 0}, {"type": 11, "value": 71, "unit": 0}]},
        {"grpid": 2, "date": 1700003600, "measures": [{"type": 1, "value": 7245, "unit": -2}]},
        {"grpid": 3, "date": 1700007200, "measures": [{"type": 54, "value": 97, "unit": 0}]},
        {"grpid": 4, "date": 1700010800, "measures": [{"type": 71, "value": 366, "unit": -1}]},   # body temperature: not in the contract, ignored
    ]}
    act = {"activities": [{"date": "2023-11-14", "steps": 8123}, {"date": "2023-11-15", "steps": 0}]}
    slp = {"series": [{"date": "2023-11-14", "data": {"total_sleep_time": 25200}}]}
    ecg = [{"signalid": 9, "timestamp": 1700000000, "heart_rate": 68, "afib": 0, "fs": 300, "samples": [1, 2, 3]}]
    out = wearables.normalise_withings(meas, act, slp, ecg)
    assert out["bloodPressure"] == [{"t": 1700000000000, "sys": 128, "dia": 82, "id": "wi-bp-1"}]
    assert out["heartRate"] == [{"t": 1700000000000, "bpm": 71, "id": "wi-hr-1"}]
    assert out["weight"] == [{"t": 1700003600000, "kg": 72.5, "id": "wi-w-2"}]  # 7245 × 10^-2 → 72.45 → 72.5
    assert out["spo2"] == [{"t": 1700007200000, "pct": 97, "id": "wi-spo2-3"}]
    assert out["steps"] == [{"date": "2023-11-14", "count": 8123}]
    assert out["sleep"] == [{"date": "2023-11-14", "hours": 7.0}]
    assert out["ecg"][0]["classification"] == "sinus_rhythm" and out["ecg"][0]["fs"] == 300 and out["ecg"][0]["avgHr"] == 68
    assert out["glucose"] == []


def test_oura_sleep_and_heart_rate_thinned():
    act = {"data": [{"day": "2024-03-01", "steps": 10432}]}
    slp = {"data": [{"day": "2024-03-01", "total_sleep_duration": 27000, "lowest_heart_rate": 52}, {"day": "2024-03-01", "total_sleep_duration": 1800}]}
    hr = {"data": [{"bpm": 60 + i, "source": "rest", "timestamp": f"2024-03-01T0{i // 12}:{(i % 12) * 5:02d}:00+00:00"} for i in range(24)] + [{"bpm": 150, "source": "workout", "timestamp": "2024-03-01T05:00:00+00:00"}]}
    spo2 = {"data": [{"day": "2024-03-01", "spo2_percentage": {"average": 96.4}}]}
    out = wearables.normalise_oura(act, slp, hr, spo2)
    assert out["steps"] == [{"date": "2024-03-01", "count": 10432}]
    assert out["sleep"] == [{"date": "2024-03-01", "hours": 8.0}]       # 27000 + 1800 s
    resting = [x for x in out["heartRate"] if x.get("resting")]
    assert resting and resting[0]["bpm"] == 52
    samples = [x for x in out["heartRate"] if not x.get("resting")]
    assert 3 <= len(samples) <= 5 and all(x["bpm"] < 150 for x in samples)   # 2 hours of 5-minute samples → one per half hour; workout dropped
    assert out["spo2"] == [{"t": out["spo2"][0]["t"], "pct": 96, "id": "ou-spo2-2024-03-01"}]


# ---------------------------------------------------------------- routes
def test_status_lists_both_providers_as_off_without_keys():
    c = client()
    key = household(c)
    j = c.get("/api/v1/wear/status", headers={**H, "x-dokko-key": key}).json()
    assert [p["id"] for p in j["providers"]] == ["withings", "oura"]
    assert all(p["enabled"] is False for p in j["providers"]) and j["links"] == []
    r = c.post("/api/v1/wear/withings/start?member=d1", headers={**H, "x-dokko-key": key})
    assert r.status_code == 503 and "Withings" in r.json()["detail"]
    assert c.post("/api/v1/wear/garmin/start", headers={**H, "x-dokko-key": key}).status_code == 404
    assert c.post("/api/v1/wear/oura/sync", headers={**H, "x-dokko-key": key}, json={"member": "d1"}).status_code == 404


def test_start_builds_the_consent_url_and_callback_rejects_bad_state(monkeypatch):
    monkeypatch.setenv("OURA_CLIENT_ID", "cid")
    monkeypatch.setenv("OURA_CLIENT_SECRET", "sec")
    c = client()
    key = household(c)
    r = c.post("/api/v1/wear/oura/start?member=d1", headers={**H, "x-dokko-key": key})
    assert r.status_code == 200
    url = r.json()["url"]
    assert url.startswith("https://cloud.ouraring.com/oauth/authorize?") and "client_id=cid" in url and "wear%2Foura%2Fcallback" in url
    r = c.get("/api/v1/wear/oura/callback?code=x&state=forged", headers=H, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("#wear=oura:cancelled")


def test_demo_key_cannot_link():
    c = client()
    r = c.post("/api/v1/wear/withings/start?member=d1", headers={**H, "x-dokko-key": "demo-abcdefghijklmnop"})
    assert r.status_code == 403


# ---------------------------------------------------------------- the page and the Bluetooth bridge
def test_page_carries_layer_19_and_sw_bumped():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p19*/" in html and "SX.bleShim=makeBluetooth" in html
    assert "withings:'Withings',oura:'Oura'" in html
    assert "SX.act.bledev=(...a)=>(navigator.bluetooth&&navigator.bluetooth.requestDevice)?ble0(...a):SX.act.hcsync()" in html
    assert "dk-r19" in (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    assert subprocess.run(["python3", str(ROOT / "tools" / "compress.py"), "--check"], capture_output=True).returncode == 0


def test_bluetooth_bridge_speaks_web_bluetooth():
    """A fake native plugin: the shim must turn Web-Bluetooth calls into plugin calls and deliver notifications as DataViews."""
    if not shutil.which("node"):
        import pytest
        pytest.skip("node not installed")
    r = subprocess.run(["node", str(ROOT / "tests" / "ble_shim.test.js")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok 6" in r.stdout
