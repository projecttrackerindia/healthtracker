"""r152: the shared frame and Home follow the approved designs (checked side by side with the boards)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UH = (ROOT / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_tab_bar_has_icons_labels_and_sos_beside_it_on_a_phone():
    i = UH.index("/* Shared frame (design)")
    blk = UH[i:i + 4000]
    assert "#b5 .t5>svg:not(.mn){display:block!important" in blk and "#sos5{position:relative!important" in blk and "#E0352B" in blk
    assert UH.index("/* Shared frame (design)") > UH.index("#b5 .t5{flex:0 0 auto!important")  # wins over the old phone rules


def test_every_tab_has_the_logo_and_a_small_line_above_the_headline():
    assert "d.insertAdjacentHTML('afterbegin','<p class=\"gbg\">'+esc(gbLine0(p0" in UH
    g = _fn("gbLine0")
    assert "'Pregnancy · '+nm" in g and "weekday:'short'" in g and "gbUp(eyebrowOf(p))" in g


def test_pink_stays_on_the_pregnancy_home_only():
    assert "S.person===me.id&&S.tab==='summary'))" in UH and "body.preg #bg{background:#F2F2EF!important}" in UH


def test_home_is_stage_next_step_results_family_and_medical_id():
    h = _fn("gbHome")
    assert "gbNext(p)+gbTiles(p)+gbFam(p)+gbMid(p)" in h and "gbMini(" not in h and "gbPlan(" not in h
    assert "Doing well. " in _fn("gbHead") and "to recheck this week" in _fn("gbHead")
    assert "body.gbhome #sheet>*:not(#gbx){display:none!important}" in UH


def test_family_list_never_names_a_pregnancy():
    f = _fn("gbFam")
    assert "preg(" not in f and "Week" not in f


def test_tell_me_when_live_uses_the_server_waiting_list():
    assert "kind:'hospital'" in _fn("vzNotify")
    bk = (ROOT / "api" / "booking.py").read_text(encoding="utf-8")
    assert '("lab", "pharmacy", "hospital")' in bk and '"hospital": "Hospital visits with live tokens are now available in your area."' in bk
