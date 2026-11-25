"""r145: Medicine · Order follows the approved design ("Medicine, order")."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_order_can_start_from_a_prescription_on_file():
    o = _fn("openPharmacy")
    assert "RXO.fromRx=!meds.length&&!!rx" in o and "on:i<3,more:i>=3" in o
    assert "more from this prescription" in o and "confirms the price before packing" in o
    assert "writer(p)" in o and "svcOk('medicine')" in o  # still only for someone who may order, and only when the service is on


def test_price_is_seen_before_the_order_is_placed():
    o = _fn("openPharmacy")
    assert "Price shown before you confirm" in o and ">See price</button>" in o
    n = _fn("rxNear")
    assert "$('#rxgo').textContent='See price'" in n and "$('#rxgo').textContent='Place order'" in n


def test_a_typed_medicine_stays_in_the_list():
    o = _fn("openPharmacy")
    assert "RXO.keep=RXO.items;openPharmacy(preIds);" in o and "if(RXO.keep){RXO.items=RXO.keep;RXO.keep=null}" in o


def test_order_headline():
    assert "'Order from '+(p.self?'your':'the')" in UH and "'MEDICINE · ORDER':S.sub===1?'MEDICINE · MINE':'MEDICINE'" in UH
