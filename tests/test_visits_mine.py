"""r146: Visits · Mine follows the approved design ("Visits")."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UH = (ROOT / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_family_due_card_has_one_action_each_and_respects_who_may_write():
    d = _fn("vzDueCards")
    assert "Book vaccination" in d and "Mark as given" in d and "${w?`<div class=\"a\">" in d
    k = _fn("vzDueKids")
    assert "p.self" in k and "can(q,'all')" in k  # only the account holder sees the family's due list, and only for children they may see


def test_note_a_visit_uses_the_record_the_server_already_reminds_on():
    n = _fn("noteVisit")
    assert "kind:'visitnote'" in n and "follow:day" in n and "booked:true" in n and "writer(p)" in n
    assert "day<today()" in n
    rem = (ROOT / "api" / "reminders.py").read_text(encoding="utf-8")
    assert 'x.kind == "visitnote" and d.get("follow") == day' in rem and 'n.get("follow") != tmr' in rem


def test_until_hospitals_are_live_nothing_leads_to_a_dead_end():
    assert "const vzOff=()=>!!(SVC&&SVC.visits===false);" in UH
    assert "vzOff()?`noteVisit(" in _fn("vzReasons") and "vzOff()?`noteVisit(" in _fn("vzDueCards")
    s = _fn("vzSoon")
    assert "Note a visit" in s and "You still get reminders." in s and "Tell me when live" not in s  # no promise the server cannot keep
    assert "writer(p)&&!(vzOff()&&!hist)" in _fn("visitsBlock")


def test_noted_visit_is_shown_once():
    assert "n.follow&&!n.booked&&n.follow>=today()" in UH and "noted by you" in _fn("vzNoted")
    assert "dueFam(p,1)" in _fn("visitsBlock")


def test_headline_counts_family_visits_to_book():
    assert "' to book','for '" in UH
