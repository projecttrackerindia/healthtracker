"""What SOS actually sends, and what it only offers.

Reported from a real alert: "it didn't send any messages." It was working as built — email and the family's
app alert go on their own, SMS and WhatsApp cannot, because a web page on a phone may not send a message on
somebody's behalf. These tests pin which channels leave by themselves, so the chips in the app can never
again claim more than the server did.

Run: python -m pytest -q tests/test_sos_reach.py
"""
import os
import uuid
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_sosreach.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import messaging, sos, whatsapp  # noqa: E402
from api.db import Base, engine  # noqa: E402

H = {"x-tht": "1"}
Base.metadata.create_all(engine)


def family():
    c = TestClient(server.app)
    c.__enter__()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", headers=H, json={"name": "Meera", "members": 2})
    return c


def press(c):
    return c.post("/api/v1/sos/start", json={
        "member": "m1", "name": "Meera", "blood": "O+", "phone": "9876500011",
        "summary": "Allergic to penicillin",
        "loc": {"lat": 13.0716, "lng": 80.2420, "acc": 12},
        "contacts": [{"n": "Jyothsna", "ph": "9876500022", "em": "j@example.com"}]})


def channels_say(monkey, **kw):
    for name, val in kw.items():
        if name == "whatsapp":
            monkey.setattr(whatsapp, "ready", lambda v=val: v)
        elif name == "sms":
            monkey.setattr(messaging, "alert_sms_ready", lambda v=val: v)
        elif name == "email":
            monkey.setattr(messaging, "email_ready", lambda v=val: v)


def test_the_app_is_told_exactly_which_channels_the_server_drives(monkeypatch):
    """The chips are rendered from this. If it over-claims, the app lies in an emergency."""
    channels_say(monkeypatch, sms=False, whatsapp=False, email=True)
    ch = family().get("/api/v1/sos/channels").json()
    assert ch["email"] is True and ch["sms"] is False and ch["whatsapp"] is False
    assert set(ch) == {"email", "sms", "whatsapp", "push"}


def test_without_a_registered_sender_nothing_is_reported_as_texted(monkeypatch):
    """The exact shape of the live report: email went, SMS and WhatsApp did not."""
    channels_say(monkeypatch, sms=False, whatsapp=False, email=True)
    sent = []
    monkeypatch.setattr(messaging, "send_mail", lambda *a, **k: sent.append("email") or True)
    monkeypatch.setattr(messaging, "send_text_sms", lambda *a, **k: False)

    r = press(family())
    assert r.status_code == 200, r.text
    chans = {x["channel"] for x in r.json()["sent"] if x.get("ok")}
    assert "email" in chans and "push" in chans
    assert "sms" not in chans and "whatsapp" not in chans


def test_with_a_registered_sender_they_go_on_their_own(monkeypatch):
    """Nothing in the app changes when the accounts exist — the same fan-out simply reaches further."""
    channels_say(monkeypatch, sms=True, whatsapp=True, email=True)
    monkeypatch.setattr(messaging, "send_mail", lambda *a, **k: True)
    monkeypatch.setattr(messaging, "send_text_sms", lambda *a, **k: True)
    monkeypatch.setattr(whatsapp, "send_sos", lambda *a, **k: True)

    r = press(family())
    chans = {x["channel"] for x in r.json()["sent"] if x.get("ok")}
    assert {"email", "sms", "whatsapp", "push"} <= chans


def test_one_channel_failing_does_not_stop_the_others(monkeypatch):
    """An emergency is the worst moment for an exception to swallow the rest of the fan-out."""
    channels_say(monkeypatch, sms=True, whatsapp=True, email=True)
    monkeypatch.setattr(messaging, "send_mail", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("smtp down")))
    monkeypatch.setattr(messaging, "send_text_sms", lambda *a, **k: True)
    monkeypatch.setattr(whatsapp, "send_sos", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("meta 500")))

    r = press(family())
    out = r.json()["sent"]
    assert any(x["channel"] == "sms" and x["ok"] for x in out)
    assert any(x["channel"] == "push" and x["ok"] for x in out)
    assert any(x["channel"] == "email" and not x["ok"] for x in out)


def test_the_message_carries_the_things_a_contact_needs(monkeypatch):
    channels_say(monkeypatch, sms=False, whatsapp=False, email=False)
    msg = press(family()).json()["message"]
    assert "Meera" in msg and "13.07" in msg and "/sos/" in msg


# ---------------------------------------------------------------- the app's side of the same honesty
def test_the_page_carries_the_sos_fix():
    page = Path("web/index.html").read_text(encoding="utf-8")
    assert "/*live-p39*/" in page and "lv39-go" in page
    assert "dk-r" in Path("web/sw.js").read_text(encoding="utf-8")   # bumped by each later layer


def test_the_send_buttons_are_big_enough_to_hit_while_shaking():
    css = Path("tools/live/live39.css").read_text(encoding="utf-8")
    assert "min-height:52px" in css


def test_the_block_disappears_by_itself_once_the_server_can_send():
    """Otherwise the day the accounts are configured, the app still asks for a tap that is no longer needed."""
    js = Path("tools/live/live39.js").read_text(encoding="utf-8")
    assert "serverSends" in js and "CH.sms && CH.whatsapp" in js


def test_we_stop_promising_a_buzz_on_a_phone_that_cannot_buzz():
    """navigator.vibrate does not exist on iOS Safari, so that half of the sentence was never true there."""
    js = Path("tools/live/live39.js").read_text(encoding="utf-8")
    assert "CAN_BUZZ" in js and "A siren sounds until you tap" in js


def test_the_siren_can_be_woken_after_the_phone_suspends_it():
    """It kept its AudioContext in a closure, so nothing could reach in and resume it — which is why it
    sounded once and then never again."""
    js = Path("tools/live/live39.js").read_text(encoding="utf-8")
    assert "visibilitychange" in js and "ctx.resume()" in js
    assert "if (muted || !osc) return;" in js      # a muted siren stays muted
