"""r149: every child's Home uses the dark stage from the baby design, with no floating label over the body."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_stage_is_for_every_child_not_only_babies():
    i = UH.index("const kidStage=")
    ks = UH[i:i + 300]
    assert "isKid(p)" in ks and "kidBand(ageOf(p))==='baby'" not in ks


def test_child_home_has_one_next_step_and_no_duplicate_tiles():
    kh = _fn("kidsHome")
    assert "kdNext(p)+kdSets(p)+gbKid(p,1)+kidList(p,!!kdNext(p))" in kh
    assert "return staged?km:" in _fn("gbKid")


def test_growth_note_is_on_the_height_chip_not_floating_over_the_body():
    assert "if(isKid(p)&&!kidFlat(p)&&!kidStage(p)){" in UH
    hud = _fn("kdHud")
    assert "kidGrowWord(p,hc)" in hud and "hc&&hc.day" in hud  # no date, no verdict (an undated height read as 'below the usual range')
    assert "ageOf(p)<2?'Length':'Height'" in hud
