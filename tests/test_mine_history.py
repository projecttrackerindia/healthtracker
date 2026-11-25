"""r149: Medicine · Mine, Visits · History and Visits · Book follow the approved designs."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_mine_lists_days_left_and_offers_one_reorder():
    m = _fn("medMine")
    assert "medLeft(m)" in m and "days left" in m.replace("' day'+(d===1?'':'s')+' left'", "days left") and "RUNNING LOW" in m
    assert "openPharmacy(['${low.m.id}'])" in m and "svcOkQuiet('medicine')" in m and "low&&w" in m  # only someone who may order, only when ordering is on
    assert "MLOWNO['${low.m.id}']=1" in m  # 'Not now' hides it
    assert "if(meds.length&&S.sub===1)h=medMine(p,meds);" in UH


def test_days_left_comes_from_stock_and_dose_times():
    d = _fn("medLeft")
    assert "+m.stock>0" in d and "m.stockDay" in d and "(m.times||[]).length" in d


def test_history_lists_past_visits_from_prescriptions():
    h = _fn("vzPastHtml")
    assert "Add notes" in h and "Book again" in h and "writer(p)" in h
    assert "r.doc==='prescription'" in _fn("vzPast")
    assert "' past visit'" in UH and "in '+(p.self?'your':'the')+' reports'" in UH


def test_book_tab_notes_a_visit_while_hospitals_are_not_live():
    assert "inTab('bk',vzOff()?vzBookNote:openBook)" in UH
    b = _fn("vzBookNote")
    assert "kind:'visitnote'" in b and "follow:day" in b and "booked:true" in b and "Save this visit" in b
    assert "grid-template-columns:minmax(0,1fr) minmax(0,1fr)" in UH  # date and time never spill out of the card
