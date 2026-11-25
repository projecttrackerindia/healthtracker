"""r147: no cut-off labels. Action buttons never shrink below their text, and the phone check fails on clipped text."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UH = (ROOT / "web" / "uh.html").read_text(encoding="utf-8")
PC = (ROOT / "tests_e2e" / "phone_check.py").read_text(encoding="utf-8")


def test_action_rows_wrap_instead_of_cutting_a_label():
    for rule in (".vzd .a .pri,.vzs .a .pri{flex:1 0 auto;", ".gbna button.pri{flex:1 0 auto;", ".mfnd button.pri{flex:1 0 auto;"):
        assert rule in UH
    assert ".gbna{flex-wrap:wrap}" in UH and ".mfnd>div{flex-wrap:wrap}" in UH


def test_phone_check_fails_on_cut_off_text():
    assert "CLIPPED = r\"\"\"" in PC and "text wider than its box" in PC and "cut by its container" in PC and "off the screen edge" in PC
    assert 'bad.extend("cut-off text, " + c for c in await pg.evaluate(CLIPPED))' in PC
    assert "e.scrollWidth>e.clientWidth+1" in PC  # Safari's engine reports it this way


def test_family_feed_line_wraps():
    i = UH.index("function famFeed(")
    assert "text-overflow:ellipsis\">${esc(x.t)}" not in UH[i:i + 4000]
