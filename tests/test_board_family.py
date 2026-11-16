"""Family boards u1-u7: the small backend pieces the new screens rely on."""
import pytest
from fastapi import HTTPException

from api.auth import device_label
from api.people import KIND_LEVEL, _check_record


def test_baby_feed_and_nappy_records_are_allowed():
    assert KIND_LEVEL["feed"] == "summary" and KIND_LEVEL["nappy"] == "summary"
    _check_record("feed", {"at": 1}, "2026-11-17")
    _check_record("feed", {"side": "left"}, "2026-11-17")
    _check_record("nappy", {"t": "wet"}, "2026-11-17")


def test_bad_feed_and_nappy_values_are_refused():
    with pytest.raises(HTTPException):
        _check_record("feed", {"side": "both sides"}, "2026-11-17")
    with pytest.raises(HTTPException):
        _check_record("nappy", {"t": "blue"}, "2026-11-17")


def test_device_label_for_new_sign_in_alert():
    assert device_label("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)") == "iPhone"
    assert device_label("Mozilla/5.0 (Linux; Android 15; Pixel 9)") == "Android phone"
    assert device_label("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "Windows computer"
    assert device_label("") == "a new device"
