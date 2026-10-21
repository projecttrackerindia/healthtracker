"""Round 29: Google-backed places and geocoding, the self-filling phrase table, SOS channels, and the phone fixes in the page.

Run: python -m pytest -q tests/test_round29.py
"""
import json
import os
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round29.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import i18n, messaging, places, sos, whatsapp  # noqa: E402
from api.db import SessionLocal  # noqa: E402
from api.models import Phrase  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("GOOGLE_MAPS_KEY", "GOOGLE_MAPS_SERVER_KEY", "GEMINI_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "MSG91_AUTH_KEY", "MSG91_SOS_FLOW_ID", "WA_TOKEN", "WA_PHONE_ID", "WA_TEMPLATE_SOS"):
        monkeypatch.delenv(k, raising=False)
    places._CACHE.clear()
    i18n._CACHE.update(t=0, body=b"", src="", v=0)
    monkeypatch.setenv("I18N_AUTO", "0")          # the background thread stays out of the tests
    yield
    places._CACHE.clear()
    i18n._CACHE.update(t=0, body=b"", src="", v=0)


def client():
    c = TestClient(server.app)
    c.__enter__()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    return c


def db():
    s = SessionLocal()
    s.query(Phrase).delete()
    s.commit()
    return s


# ---------------------------------------------------------------- places and geocoding
GEO = {"status": "OK", "results": [{"formatted_address": "Hitech City Rd, Madhapur, Hyderabad, Telangana 500081, India",
                                    "geometry": {"location": {"lat": 17.4452, "lng": 78.3908}},
                                    "address_components": [{"long_name": "Madhapur", "types": ["sublocality_level_1", "sublocality"]},
                                                           {"long_name": "Hyderabad", "types": ["locality"]},
                                                           {"long_name": "Hyderabad", "types": ["administrative_area_level_2"]},
                                                           {"long_name": "Telangana", "types": ["administrative_area_level_1"]},
                                                           {"long_name": "500081", "types": ["postal_code"]},
                                                           {"long_name": "India", "types": ["country"]}]}]}


def test_reverse_geocode_prefers_google_and_keeps_the_fields_the_app_stores(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_SERVER_KEY", "k")
    calls = []

    def fake(url, params, timeout=10):
        calls.append((url, params))
        return GEO

    monkeypatch.setattr(places, "_gget", fake)
    monkeypatch.setattr(places, "_get", lambda *a, **k: pytest.fail("OSM must not be called when Google answers"))
    c = client()
    j = c.get("/api/v1/geo/where?lat=17.4452&lng=78.3908", headers=H).json()
    assert j["ok"] and j["place"] == "Madhapur" and j["city"] == "Hyderabad" and j["state"] == "Telangana"
    assert j["stateCode"] == "TS" and j["pin"] == "500081" and "Madhapur" in j["label"]
    assert places.provider() == "google" and "geocode/json" in calls[0][0]
    c.get("/api/v1/geo/where?lat=17.4452&lng=78.3908", headers=H)      # the second ask is served from the cell cache
    assert len(calls) == 1


def test_geocoding_falls_back_to_openstreetmap_when_google_is_not_configured_or_fails(monkeypatch):
    seen = []
    monkeypatch.setattr(places, "_get", lambda url, *a, **k: seen.append(url) or {"address": {"suburb": "Kondapur", "city": "Hyderabad", "state": "Telangana", "postcode": "500084"}})
    c = client()
    j = c.get("/api/v1/geo/where?lat=17.46&lng=78.36", headers=H).json()
    assert j["place"] == "Kondapur" and j["stateCode"] == "TS" and places.provider() == "osm"
    # and with a key that errors, the same fallback runs
    places._CACHE.clear()
    monkeypatch.setenv("GOOGLE_MAPS_SERVER_KEY", "k")
    monkeypatch.setattr(places, "_gget", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    j = c.get("/api/v1/geo/where?lat=17.46&lng=78.36", headers=H).json()
    assert j["place"] == "Kondapur" and len(seen) == 2


def test_nearby_places_come_from_google_with_the_fields_the_cards_show(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_SERVER_KEY", "k")
    body = {}

    def fake(url, b, fields, timeout=12):
        body.update(b)
        return {"places": [{"id": "abc", "displayName": {"text": "Apollo Hospitals"}, "location": {"latitude": 17.45, "longitude": 78.39},
                            "formattedAddress": "Jubilee Hills, Hyderabad", "nationalPhoneNumber": "040 2355 1066", "rating": 4.3, "userRatingCount": 900,
                            "currentOpeningHours": {"openNow": True}, "regularOpeningHours": {"weekdayDescriptions": ["Monday: Open 24 hours"]}},
                           {"displayName": {"text": "No location"}}]}

    monkeypatch.setattr(places, "_gpost", fake)
    monkeypatch.setattr(places, "_get", lambda *a, **k: pytest.fail("Overpass must not be called"))
    c = client()
    j = c.get("/api/v1/places?kind=hospital&lat=17.44&lng=78.35&radius=6000", headers=H).json()
    assert j["ok"] and j["src"] == "google" and len(j["places"]) == 1
    p = j["places"][0]
    assert p["name"] == "Apollo Hospitals" and p["phone"].endswith("1066") and p["rating"] == 4.3 and p["open"] is True and p["km"] > 0
    assert body["includedTypes"] == ["hospital"] and body["locationRestriction"]["circle"]["radius"] == 6000.0


def test_nearby_places_fall_back_to_overpass_and_say_which_source_answered(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_SERVER_KEY", "k")
    monkeypatch.setattr(places, "_gpost", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("quota")))
    monkeypatch.setattr(places, "_get", lambda *a, **k: {"elements": [{"type": "node", "id": 7, "lat": 17.45, "lon": 78.39, "tags": {"name": "Govt Hospital", "emergency": "yes"}}]})
    c = client()
    j = c.get("/api/v1/places?kind=hospital&lat=17.44&lng=78.35", headers=H).json()
    assert j["ok"] and j["src"] == "osm" and j["places"][0]["name"] == "Govt Hospital" and j["places"][0]["emergency"] is True


# ---------------------------------------------------------------- the phrase table fills itself
def test_a_phone_reports_untranslated_strings_and_the_table_grows(monkeypatch):
    s = db()
    c = client()
    r = c.post("/api/v1/i18n/missing", headers=H, json={"items": ["Zephyr clinic opens at seven", "Zephyr clinic opens at seven", "  Quartz reading added  ", "₹2,999", "BP", "HbA1c", "<b>{x}</b>", "https://x.com", "a"]})
    j = r.json()
    assert j["added"] == 2 and j["pending"] == 2 and j["translator"] is False      # only the two real sentences
    assert {p.en for p in s.query(Phrase).all()} == {"Zephyr clinic opens at seven", "Quartz reading added"}
    # the model answers; the next load of the table carries both, with a version the app can compare
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(i18n, "gemini", lambda batch: {b: ["हिन्दी " + b, "తెలుగు " + b] for b in batch})
    assert i18n.translate_pending(s) == 2
    body = json.loads(c.get("/api/v1/i18n", headers=H).content)
    assert body["Zephyr clinic opens at seven"][0].startswith("हिन्दी") and body["Quartz reading added"][1].startswith("తెలుగు")
    assert body["__v"] and c.get("/api/v1/i18n", headers=H).headers["x-i18n-source"].endswith("+db2")
    # a phrase the model keeps refusing is tried three times, then left alone
    s.add(Phrase(en="Something odd"))
    s.commit()
    monkeypatch.setattr(i18n, "gemini", lambda batch: {})
    i18n.translate_pending(s)
    monkeypatch.setattr(i18n, "gemini", lambda batch: {"nope": ["x", "y"]})
    for _ in range(4):
        i18n.translate_pending(s)
    assert s.get(Phrase, "Something odd").tries <= 3
    s.close()


def test_usable_keeps_sentences_and_drops_codes_markup_and_numbers():
    assert i18n.usable("  Blood   pressure high ") == "Blood pressure high"
    for junk in ("BP", "HbA1c", "₹2,999", "—", "{name} is low", "<b>hi</b>", "support@x.com", "https://a.b", "x" * 201, "7"):
        assert i18n.usable(junk) == "", junk


# ---------------------------------------------------------------- SOS: every channel the server can drive by itself
def test_sos_channels_say_what_leaves_without_a_tap(monkeypatch):
    c = client()
    j = c.get("/api/v1/sos/channels", headers=H).json()
    assert j == {"email": j["email"], "sms": False, "whatsapp": False, "push": j["push"]}
    monkeypatch.setenv("MSG91_AUTH_KEY", "k")
    monkeypatch.setenv("MSG91_SOS_FLOW_ID", "flow1")
    monkeypatch.setenv("WA_TOKEN", "t")
    monkeypatch.setenv("WA_PHONE_ID", "1")
    j = c.get("/api/v1/sos/channels", headers=H).json()
    assert j["sms"] is True and j["whatsapp"] is True and messaging.alert_sms_ready() is True


def test_alert_sms_uses_the_msg91_template_when_twilio_is_absent(monkeypatch):
    sent = {}
    monkeypatch.setattr(messaging, "send_flow_sms", lambda to, flow, var: sent.update(to=to, flow=flow, **var) or True)
    assert messaging.send_text_sms("+919876543210", "EMERGENCY", flow_vars={"name": "Meera", "link": "https://x/sos/t"}) is False
    monkeypatch.setenv("MSG91_AUTH_KEY", "k")
    monkeypatch.setenv("MSG91_SOS_FLOW_ID", "flow1")
    assert messaging.send_text_sms("+919876543210", "EMERGENCY", flow_vars={"name": "Meera", "link": "https://x/sos/t"}) is True
    assert sent["flow"] == "flow1" and sent["name"] == "Meera" and sent["link"].endswith("/sos/t")
    assert messaging.send_text_sms("+919876543210", "plain") is False      # no flow variables → no template to use


def test_sos_fan_out_adds_whatsapp_when_that_channel_is_live(monkeypatch):
    monkeypatch.setenv("WA_TOKEN", "t")
    monkeypatch.setenv("WA_PHONE_ID", "1")
    posts = []
    monkeypatch.setattr(whatsapp, "_post", lambda payload: posts.append(payload) or {})
    monkeypatch.setattr(sos.messaging, "email_ready", lambda: False)
    monkeypatch.setattr(sos.messaging, "send_text_sms", lambda *a, **k: False)
    monkeypatch.setattr(sos, "notify", lambda *a, **k: None)

    class A:
        token, name, household_id, member_id = "tok", "Meera", "h1", "m1"
        lat = lng = acc = None
        created = updated = 1_760_000_000
        trail: list = []
        data = {"contacts": [{"n": "Ravi", "ph": "+919876543210"}], "summary": "two medicines", "blood": "O+"}

    out = sos.fan_out(None, A(), "https://app.example")
    assert [x["channel"] for x in out] == ["whatsapp", "push"] and out[0]["ok"] is True
    assert posts and posts[0]["to"] == "919876543210"
    # with an approved template the message carries the name and the live link as variables
    posts.clear()
    monkeypatch.setenv("WA_TEMPLATE_SOS", "sos_alert")
    sos.fan_out(None, A(), "https://app.example")
    params = posts[0]["template"]["components"][0]["parameters"]
    assert posts[0]["template"]["name"] == "sos_alert" and params[0]["text"] == "Meera" and params[1]["text"].endswith("/sos/tok")


# ---------------------------------------------------------------- the page the phone loads
def test_page_carries_layer_29_with_every_fix_from_the_phone():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p29*/" in html
    # a mobile app does not pinch-zoom
    assert "maximum-scale=1, user-scalable=no" in html
    # SOS: the press is the alert — no countdown, a siren until "I'm safe"
    assert "lv21cancel" not in html and "SX.siren" in html and "sosmute" in html
    assert "try{SX.siren&&SX.siren.start()}catch(e){}" in html and "SX.act.sossafe=async()=>{if(!A)return;A.active=false;try{SX.siren&&SX.siren.stop()}" in html
    # one location, picked on a map, used everywhere
    assert "SX.mapPick=" in html and "SX.loc={" in html and "SX.locCard=" in html and html.count("SX.act.locset=") == 3
    # Heart Lab leaves Home and only joins Care when the heart is the subject
    assert "SX.heartOn=" in html and "const home=SX.G.find(g=>g.k==='home');if(home)home.tabs=home.tabs.filter(t=>t!=='heart')" in html
    # the body's head clears the search bar on a portrait phone
    assert "C.fov=ph?33:30" in html and "setViewOffset" in html
    # the tab bar stays inside the screen, money stays on one line, the vault gets arrows
    assert "max-width:calc(100vw - 24px)!important" in html and ".lv29-money" in html and "lv29-wnav" in html
    # every string on screen is translated, and the table is never served stale
    assert "SX.i18nDom=" in html and "cache:'no-store'" in html and "/i18n/missing" in html
    # the assistant's own mark, and the iPhone install card instead of an Android download
    assert "SX.assistMark=" in html and "lv29-mark" in html and "data-sx=\"a2hs\"" in html
    assert "${isIOS?'':a.available?" in html


def test_service_worker_ships_the_new_build():
    sw = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    import re
    m = re.search(r"const V='dk-r(\d+)'", sw)
    assert m and int(m.group(1)) >= 29
