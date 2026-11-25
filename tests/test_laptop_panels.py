"""r149: the laptop right column follows the designs for Visits and Medicine."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_visits_rail_has_the_month_and_how_a_visit_works():
    rail = _fn("railHTML")
    assert "S.tab==='visits'&&!S.sub&&can(p,'all')" in rail and "${vzCal(p)}" in rail and "How a visit works" in rail
    cal = _fn("vzCal")
    assert "vNotes(q.id)" in cal and "vaxOf(q)" in cal and "can(q,'all')" in cal  # only people this account may see


def test_medicine_rail_offers_the_prescription_to_order():
    rail = _fn("railHTML")
    assert "On this prescription" in rail and "inTab('bk',openPharmacy)" in rail and "svcOkQuiet('medicine')" in rail


def test_next_vaccine_sets_show_beside_the_due_card_on_wider_screens():
    assert "vzDueCards(p)+vzThen(p)" in UH and "@media (min-width:700px){.vzth{display:block" in UH
