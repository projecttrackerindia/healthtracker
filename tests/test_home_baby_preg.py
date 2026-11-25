"""r140: the baby Home and the pregnancy Home follow the approved designs ("Home, baby", "Home, pregnancy")."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UH = (ROOT / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    j = UH.index("\nfunction ", i + 10)
    return UH[i:j]


def test_baby_home_is_stage_next_step_sets_first_aid():
    body = _fn("kidsHome")
    baby = body[body.index("if(band==='baby')"):body.index("const v=vaxOf(p)")]
    assert "kdNext(p)+first30(p)+kdSets(p)" in baby
    assert "First aid for babies" in baby and "openAidList()" in baby
    # the old pale cards are gone from the baby Home, not left reachable
    assert "vaxDueCard(p)" not in baby and "gCard(" not in baby and "vaxRows(p)" not in baby


def test_baby_stage_is_dark_and_uses_the_childs_own_3d_body():
    assert re.search(r"body\.kidst #herobg\{background:radial-gradient\([^}]*#0A1420", UH)
    assert "document.body.classList.toggle('kidst',on)" in UH
    assert "showModel();pgHud();kdHud();h3dSet(P())" in UH
    # chips sit beside the body on a phone: the body moves right, the chips keep the left
    assert "body.kidst #gl{transform:translate(58px" in UH


def test_vaccine_pin_is_found_on_the_skin_and_follows_the_body():
    pin = _fn("kdPin")
    assert "kdThigh(cur)" in pin and "applyMatrix4(root.matrixWorld).project(cam)" in pin
    assert "placeLabels();kdPin()" in UH
    th = _fn("kdThigh")
    assert "skinGeo.attributes.position.array" in th


def test_baby_chips_let_a_parent_add_weight_and_length():
    hud = _fn("kdHud")
    assert "'Weight'" in hud and "'Length'" in hud and "+ Add" in hud
    assert "overdue" in hud and "openVax(" in hud and "openGrowthPage(" in hud
    # someone who cannot write does not get an Add chip
    assert ":w?`<button class=\"kdc\"" in hud


def test_next_step_only_offers_mark_as_given_to_a_writer():
    nx = _fn("kdNext")
    assert "NEXT STEP" in nx and "Book a visit" in nx
    assert "${w?`<button onclick=\"vaxGive(" in nx


def test_baby_headline_names_the_vaccines_to_catch_up_on():
    alt = _fn("gbAlt")
    assert "kidStage(p)" in alt and "to catch up on" in alt and "is up to date" in alt


def test_pregnancy_home_has_progress_under_headline_and_timeline():
    alt = _fn("gbAlt")
    assert 'class="pgin"' in alt and "of 40" in alt
    ph = _fn("pregHome")
    assert 'class="card pgtl' in ph and "From week 37" in ph and "Now · week " in ph
    assert "Coming up" not in ph and 'class="card pgup"' not in ph
    assert "Count once today" in ph


def test_pregnancy_stage_says_what_is_happening_this_week():
    hud = _fn("pgHud")
    assert 'class="phc"' in hud and "This week: " in hud and "openPregMore()" in hud
    assert "'an ':'a '" in hud  # "about a coconut", not "about coconut"


def test_version_stamp_matches_service_worker():
    sw = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    v = re.search(r"const APPV='(dk-r\d+)'", UH).group(1)
    assert "const V='%s'" % v in sw and int(v[4:]) >= 140
