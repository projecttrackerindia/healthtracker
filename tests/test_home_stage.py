"""Home for an adult (25 Nov 2026 design): the whole body on one dark stage, the person's results beside it.

The rules a person would notice if they broke: a card must never sit on the body, lines must not cross,
the result that needs a look must never be the one left out, and a baby's measurements are not the mother's.
"""
import re
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text()
STAGE = UH[UH.index("function gbStage(p)"):UH.index("function gbStageLines()")]


def test_every_organ_anchor_is_inside_the_picture():
    block = UH[UH.index("const GBANCH="):UH.index("const GBORGN=")]
    pairs = re.findall(r"\[(\.\d+|\d(?:\.\d+)?),(\.\d+|\d(?:\.\d+)?)\]", block)
    assert len(pairs) >= 14
    assert all(0 < float(x) < 1 and 0 < float(y) < 1 for x, y in pairs)


def test_every_anchored_organ_has_a_name():
    block = UH[UH.index("const GBANCH="):UH.index("const GBORGN=")]
    names = UH[UH.index("const GBORGN="):UH.index("function gbStage(p)")]
    for organ in set(re.findall(r"(\w+):\[", block)):
        assert f"{organ}:'" in names, organ


def test_what_needs_a_look_leads_the_dial():
    # v2 (Nov 2026): one dial entry per organ; organs with a result to watch come first, led by the next-step result
    assert "bi(a)-bi(b)||A[a.o][1]-A[b.o][1]" in STAGE
    assert ".slice(0,innerWidth>=980?7:5)" in STAGE


def test_the_babys_measurements_never_reach_the_mothers_stage():
    assert "findings(p.id).filter(f=>!f.baby)" in STAGE


def test_home_uses_the_stage_and_one_next_step():
    home = UH[UH.index("function gbHome(p)"):UH.index("function gbLine()")]
    assert "gbStage(p)" in home and "gbNext(p)" in home


def test_nothing_is_drawn_over_the_body():
    # v2: no value cards or lines on the stage; the organ glows and its result shows in one row under the dial
    assert "gbsc" not in STAGE and "gbsk" not in STAGE
    assert 'class="gbdl"' in STAGE and 'id="gbse"' in STAGE and 'id="gbgl"' in STAGE
    css = UH[UH.index(".gbst.v2{"):UH.index(".gbsr{")]
    assert "pointer-events:none" in css      # the glow never takes a tap meant for the body button
