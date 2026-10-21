"""Round 32: one place for location, a heart that looks like a heart, a chat-first assistant,
and places you can actually book. Run: python -m pytest -q tests/test_round32.py"""
import os
import re
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round32.db"

ROOT = Path(__file__).resolve().parents[1]
WEB = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------- the layers are applied
def test_layers_applied():
    for n in (32, 33, 34):
        assert f"/*live-p{n}*/" in WEB, f"layer {n} missing"


def test_service_worker_bumped():
    sw = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    m = re.search(r"const V='dk-r(\d+)'", sw)
    assert m, "sw version marker missing"
    assert int(m.group(1)) >= 34, "service worker not bumped for this round"


# ---------------------------------------------------------------- A. one global location
def test_one_door_for_location():
    """Every module asks through SX.needLoc, so permission is requested once and reused."""
    assert "SX.needLoc=" in WEB
    assert "SX.locSheet=" in WEB
    # the old per-page geo call is wrapped, not replaced, so existing callers keep working
    assert "const geo0=SX.geo" in WEB


def test_module_choices_with_sos_locked():
    """All modules on by default; the person may deselect any of them except SOS."""
    for k in ("'sos'", "'labs'", "'meds'", "'care'", "'alerts'", "'live'"):
        assert k in WEB, f"module {k} missing from the consent sheet"
    assert "req:true" in WEB, "SOS is not marked mandatory"
    assert "p.mod.sos=true" in WEB, "SOS can be switched off"
    assert "SX.chg.locmod" in WEB, "no per-module toggle"


def test_live_tracking_present():
    assert "SX.sosWatch=" in WEB
    assert "watchPosition" in WEB


def test_location_is_visible_and_changeable():
    assert "SX.locChip" in WEB, "no status chip in the header"
    assert "SX.locCard" in WEB, "no location card for Today/Book"
    assert "lv32" in WEB


# ---------------------------------------------------------------- B. the heart
def test_heart_studio_lighting():
    assert "studioEnv" in WEB, "no image-based lighting"
    assert "ACESFilmicToneMapping" in WEB
    assert "PMREMGenerator" in WEB


def test_heart_surface_relief():
    """Flat materials read as a balloon; the relief map is what makes it tissue."""
    assert "noiseMaps" in WEB
    assert "normalMap" in WEB
    assert "roughnessMap" in WEB


def test_heart_sheen_handles_both_three_builds():
    """This three build carries sheen as a Colour; newer ones as a number. Both must be safe."""
    assert "myo.sheen.isColor" in WEB


def test_heart_gfx_is_reachable_from_layers():
    assert "SX.heartGfx" in WEB
    assert "gfx:()=>({THREE,R,S,cam,G,myo,valM,artM,veinM})" in WEB


# ---------------------------------------------------------------- C. the assistant is chat-first
def test_assistant_chat_first():
    assert "lv33-chat" in WEB, "no chat-first mode"
    assert "lv33bar" in WEB, "the mark does not shrink into a bar"
    assert "SX.act.agnew" in WEB, "no New chat action"


# ---------------------------------------------------------------- D. places you can use
def test_place_sheet_exists():
    assert "SX.placeSheet=" in WEB
    assert "SX.act.plopen" in WEB
    assert "SX.act.plbook" in WEB


def test_row_actions_do_not_collapse():
    css = WEB[WEB.index('<style id="live34-css">'):]
    css = css[: css.index("</style>")]
    assert "white-space:nowrap" in css, "buttons may wrap into vertical letters"
    assert ".lv34-row2" in css


def test_selecting_a_place_does_not_rerender():
    """The full render() rebuilt the Google map under the finger — that was the shake."""
    body = WEB[WEB.index("/*live-p34*/"):]
    sel = body[body.index("SX.act.mapsel=") :]
    sel = sel[: sel.index("\n}")] if "\n}" in sel else sel[:600]
    assert "render()" not in sel, "mapsel still triggers a full render"
    assert "classList.toggle" in sel
    assert "SX.gmapPan" in sel


def test_map_instance_is_kept():
    assert "LASTMAP" in WEB
    assert "SX.gmapPan=" in WEB


def test_nothing_repaints_while_scrolling():
    assert "SX.busyScroll" in WEB
    assert "lv34-scroll" in WEB


def test_booking_path_for_non_partner_labs():
    """/labs/quotes only knows partner stores; where there are none the sheet used to end blank."""
    assert "SX.labSheetHook" in WEB, "the quote sheet cannot be extended"
    assert "SX.labQuotes" in WEB
    assert "fbLabs" in WEB, "no fallback list of nearby labs"
    assert "lv34-fb" in WEB


def test_planned_tests_are_saved():
    assert "labPlan" in WEB
    assert "SX.act.lpdone" in WEB
    assert "SX.act.lpcall" in WEB


def test_layer_reads_main_scope_through_exports_only():
    """Layers run in a different scope: reaching for PLACES/plSel directly silently returns nothing."""
    body = WEB[WEB.index("/*live-p34*/"):]
    assert "typeof PLACES!=='undefined'" not in body, "layer reads PLACES directly"
    assert "SX.placesData" in body
    assert "SX.setPlSel" in body


# ---------------------------------------------------------------- prices stay honest
def test_no_invented_price_floor():
    """We never quote a 'from ₹X' we made up; the lab confirms the real amount."""
    assert "typical*0.75" not in WEB
    assert "the lab confirms the final amount" in WEB
