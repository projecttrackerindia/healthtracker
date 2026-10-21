"""The family's side: the card that shows a technician coming to the door.
Run: python -m pytest -q tests/test_family_tracking.py"""
import os
import re
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_famtrack.db"

ROOT = Path(__file__).resolve().parents[1]
WEB = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
LAYER = WEB[WEB.index("/*live-p36*/"):]


def test_the_layer_is_applied():
    assert 'id="live36-css"' in WEB
    assert re.search(r"const V='dk-r(3[6-9]|[4-9]\d)'", (ROOT / "web" / "sw.js").read_text(encoding="utf-8"))


def test_it_reads_state_through_the_exported_handle():
    """A live layer runs in a different scope from the main script: bare `S` is undefined there, silently.
    This caught the card out once already."""
    body = LAYER[: LAYER.index("SX.boot();")]
    assert "SX.S" in body
    assert not re.search(r"[^.\w]S\.liveOrders", body), "reading the main script's S directly fails silently"


def test_the_card_is_ordered_to_the_top_of_the_page():
    """#page lays its cards out on a grid, so being first in the DOM is not enough to be first on screen."""
    css = WEB[WEB.index('<style id="live36-css">'):]
    css = css[: css.index("</style>")]
    assert "order:-1" in css and "grid-row:1" in css


def test_no_map_without_a_maps_key():
    """An empty map container paints as a grey box, which reads as something that failed to load."""
    assert "SX.cfg.maps.provider === 'google'" in LAYER
    assert "SX.cfg.maps.key" in LAYER


def test_distance_not_an_invented_eta():
    """We have a position and an address. We do not have a routing call, so we say how far, not how long."""
    assert "km(" in LAYER and "away" in LAYER
    assert "minutes away" not in LAYER


def test_every_state_has_something_true_to_say():
    for phrase in ("is on the way", "has arrived", "is assigned", "Last seen",
                   "Not sharing their location right now"):
        assert phrase in LAYER, f"no honest line for: {phrase}"


def test_it_repaints_in_place_rather_than_re_rendering():
    """Re-rendering the page would rebuild the Google map on every tick — the fault that made the places
    list shake in round 34."""
    assert "replaceWith" in LAYER
    assert "SX.gmapPan" in LAYER


def test_polling_is_slower_than_the_technician_pings():
    assert "setInterval(poll, 10000)" in LAYER, "the technician pings every 15s; polling faster buys nothing"


def test_the_card_only_shows_on_pages_that_should_have_it():
    assert "const SHOW_ON = ['dash', 'orders']" in LAYER


# ---------------------------------------------------------------- the status the family is shown
def test_the_shown_step_never_lags_the_real_status():
    """_status derived the step from the timeline alone, so a status set without a timeline entry — an admin
    fixing something, a migration, a partner integration — showed the family a step behind reality."""
    from types import SimpleNamespace

    from api.models import now
    from api.routes import _status

    # created=now(), or the staging demo clock walks the order to the last step on its own
    o = SimpleNamespace(kind="lab", status="en_route", timeline=[], created=now())
    steps, i = _status(o)
    assert steps[i][0] == "en_route", f"family would have seen {steps[i][0]}"

    # and the timeline still wins when it is ahead of a stale status column
    o2 = SimpleNamespace(kind="lab", status="assigned", created=now(),
                         timeline=[{"s": "assigned"}, {"s": "en_route"}, {"s": "arrived"}])
    steps2, i2 = _status(o2)
    assert steps2[i2][0] == "arrived"
