"""r144: Medicine · Today offers the medicines already read from a prescription (design "Medicine")."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_only_offered_to_someone_who_can_set_medicines_and_has_none_yet():
    f = _fn("medFound")
    assert "!writer(p)||!can(p,'all')" in f and "r.kind==='med'" in f and "r.doc==='prescription'" in f


def test_nothing_is_switched_on_without_the_persons_confirmation():
    h = _fn("medFoundHtml")
    assert "You confirm every dose first." in h and "Suggested" in h
    assert "medRxGo('${r.id}')" in h and "openReport('${r.id}')" in h
    assert "API(" not in h  # showing the card never creates a medicine
    assert "openRxImport(r)" in _fn("medRxGo")


def test_day_is_split_into_morning_afternoon_night_from_the_prescription():
    h = _fn("medFoundHtml")
    assert "rxPlan(m).times" in h and "Morning" in h and "Afternoon" in h and "Night" in h and "Nothing here" in h


def test_headline_counts_the_medicines_found():
    assert "' found','in '+(p.self?'your'" in UH
