"""The card number sits in a TEXT column. Raw encrypted bytes came back from Postgres as '\\x76…' text and could not be
read, so the desk screen said the number wasn't saved. It is now stored as base64, and the older forms still read."""
from api.family import encrypt
from api.schemes import _open, _seal


def test_new_numbers_round_trip_as_text():
    v = _seal({"n": "58678671"})
    assert isinstance(v, str) and v.startswith("b64:")
    assert _open(v)["n"] == "58678671"


def test_rows_saved_before_the_fix_still_read():
    raw = encrypt({"n": "58678671"})
    assert _open(raw)["n"] == "58678671"                       # bytes (SQLite)
    assert _open("\\x" + raw.hex())["n"] == "58678671"         # what Postgres handed back for bytes in TEXT


def test_empty_or_garbage_is_none():
    assert _open("") is None and _open(None) is None and _open("b64:!!!") is None


def test_policy_start_from_the_card_is_kept():
    from api.schemes import CardIn, _fill
    from api.models import SchemeCard
    c = SchemeCard(household_id="h", scheme="private")
    _fill(c, CardIn(scheme="private", number="58678671", insurer="Care Health", validFrom="2025-09-22"))
    assert (c.terms or {}).get("valid_from") == "2025-09-22"
    _fill(c, CardIn(scheme="private", number="58678671", insurer="Care Health", validFrom="22/09/2025"))
    assert c.terms["valid_from"] == "2025-09-22"      # a bad date never overwrites a good one


def test_dependent_relation_is_kept_and_unknown_dropped():
    from api.people import clean_profile
    assert clean_profile({"relation": "Daughter"})["relation"] == "Daughter"
    assert clean_profile({"relation": "Boss"})["relation"] == ""
