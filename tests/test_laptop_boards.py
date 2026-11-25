"""r155: each tab's laptop right column follows its board; no profile card, no generic 'Coming up'."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_rail_per_tab():
    r = _fn("railHTML")
    assert "labRead(p)}${labOnBodyBig(p)}" in r
    assert "Order these from a nearby pharmacy" in r and "Prescription on file" in r
    assert "claimsView(el)" in r and "More cover, from a licensed partner" in r
    assert "${vzReasons(p)}${vzCal(p)}" in r
    assert 'class="rcard rwho"' not in r  # the profile card the boards do not have


def test_pregnancy_laptop_header_heads_the_right_column():
    assert "const pgHH=innerWidth>=980" in UH and "let h=pgHH+pregBar(p,pg,w)" in UH
    assert "document.body.classList.contains('preg')&&S.tab==='summary'?176:240" in UH


def test_lab_next_test_sits_under_the_reports_on_a_laptop():
    assert 'class="card lbnx2"' in _fn("recordsBody")
