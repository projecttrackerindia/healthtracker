"""Option A (27 Nov 2026): every mark is the lab's own; pregnancy and children get "Doctor to review" instead of a green tick
for sugar, haemoglobin and thyroid (and alkaline phosphatase and creatinine for children); no limits of the app's own."""
from pathlib import Path

H = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text()
B = (Path(__file__).resolve().parents[1] / "web" / "body.html").read_text()


def _fn(name, src=H):
    i = src.index("function %s(" % name)
    return src[i:src.index("\nfunction ", i + 10)]


def test_four_marks_only_from_the_lab():
    s = _fn("statusOf")
    for w in ("Lab marked critical", "Doctor to review", "In range (lab)", "'Lab marked '+fl"):
        assert w in s, w
    assert "DOCT[" not in s and "Talk to your doctor this week" not in H and "A little high" not in H


def test_who_gets_doctor_to_review():
    a = _fn("adultX")
    assert "if(pg)return sug||hb||thy" in a and "if(isKid(p))return sug||hb||thy||c==='alp'||c==='creat'" in a and "return false}" in a


def test_note_and_no_green_band_for_review():
    n = _fn("adultNote")
    assert "Labs print adult ranges" in n and "Labs often print adult ranges" in n and "Please show this report to your doctor" in n
    assert "const bar=st.k==='review'?'':rangeBar(f)" in H and "const d=null," in _fn("rangeBar")
    assert "${adultNote(p,rows)}<div class=\"list rrl\"" in H and "${adultNote(p,rows)}${n?" in H


def test_no_app_verdicts_left():
    assert "Your cover may pay for" not in H and "Check what your cover includes" in H
    assert "Doing well. " not in H and "'Goal under '" not in B and "see doctor" not in B
    assert "f.review?'review':'ok'" in B and "review:qualFlag(f)==='normal'&&adultX(f,p)" in H
