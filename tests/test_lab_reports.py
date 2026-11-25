"""r142: Lab · My reports follows the approved design ("Lab")."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_read_for_you_says_it_is_not_a_diagnosis_and_offers_one_step():
    rd = _fn("labRead")
    assert "READ FOR YOU" in rd and "Not a diagnosis." in rd and "openAI()" in rd
    assert "gbBookTest()" in rd and "bad.length&&writer(p)" in rd  # booking only when something needs a recheck
    assert "can(p,'summary')" in rd


def test_on_your_body_shows_the_persons_own_latest_result():
    ob = _fn("labOnBody")
    assert "filter(f=>!f.baby)" in ob and "openBody()" in ob and "can(p,'summary')" in ob


def test_reports_list_has_year_header_add_button_and_show_more():
    ls = _fn("labList")
    assert "Add report" in ls and "openUplink()" in ls and "i===0&&w" in ls  # only a writer can add
    assert "LABALL=true;renderSheet()" in ls and "more report" in ls
    row = _fn("labRow")
    assert "labMine(r)" in row and "openReport(" in row and "Looks like a copy" in row
    assert "!isFactRow(f)&&!BABY_RX.test(f.test||'')" in UH[UH.index("const labMine="):UH.index("const labMine=") + 300]


def test_old_lab_hero_and_timeline_are_not_used_for_a_short_list():
    body = _fn("recordsBody")
    assert "labList(p,all)" in body and "tlHtml(all)" not in body
    assert "el.className='gblab'" not in UH and "#gbx.gblab" not in UH


def test_laptop_rail_carries_the_cards_once():
    body = _fn("recordsBody")
    assert "rail?'':labRead(p)+labOnBody(p)" in body
    rail = _fn("railHTML")
    assert "${labRead(p)}${labOnBody(p)}" in rail and "Book a blood test" in rail


def test_book_a_test_headline_counts_chosen_tests():
    tab = _fn("gbTab")
    assert "S.sub==='bk'&&writer(p)" in tab and "chosen,','collected at your door'" in tab
    assert "records:S.sub==='bk'?'LAB · HOME COLLECTION':'LAB'" in UH
    assert "if(S.tab==='records'&&S.sub==='bk')renderTop()" in _fn("labToggle")
    page = _fn("labPage")
    assert "'report in '+t.tat+' h'" in page and "' · fasting needed'" in page


def test_booking_bar_clears_the_tab_bar_on_a_phone():
    assert "@media (max-width:979px){#embed .lbar,#embed .mkbar,#embed .ckbar{bottom:calc(100px + env(safe-area-inset-bottom))!important}" in UH
