"""r150: Medicine · Orders and Lab · Bookings follow the approved designs, without promising what the server does not do."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_each_tab_shows_only_its_own_orders():
    b = _fn("openBookings")
    assert "const medOnly=S.tab==='meds'&&S.sub==='ord';" in b and "if(medOnly)os=os.filter(o=>o.kind!=='lab');" in b
    assert "S.sub==='ord'||medOnly?[]:APPTS" in b  # hospital visits stay on Visits


def test_order_card_shows_every_step_and_a_late_state():
    c = _fn("ordCard")
    assert "Delayed" in c and "Talk to support" in c and "reportProblem(" in c
    assert "will call you back" in c and "has been told" not in c  # only what the server actually does: the admin console flags stuck orders
    l = _fn("ordLate")
    assert "3*86400" in l and "o.kind==='lab'" in l


def test_headlines():
    assert "' late.','Our team can see it.'" in UH and "' booked'" in UH
    assert "'MEDICINE · ORDERS'" in UH and "'LAB · BOOKINGS'" in UH
