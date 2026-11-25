"""25 Nov: SOS must sit in one place on every screen, beside the tab bar, as in the design."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def test_tab_bar_never_folds_away_on_scroll():
    i = UH.index("function fold(on){")
    assert UH[i:i + 40].startswith("function fold(on){if(on)return;")


def test_sos_is_beside_the_tab_bar_not_at_the_top():
    i = UH.index("/* Shared frame (design)")
    blk = UH[i:i + 4000]
    assert "#sos5{position:relative!important;top:auto!important" in blk
    assert i > UH.index("#sos5{position:fixed!important;top:max(19px")  # the old 'SOS at the top' rule is overridden
