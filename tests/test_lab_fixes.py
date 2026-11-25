"""r141: Lab fixes found while building Lab to the design."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def test_book_a_home_test_opens_the_lab_booking_tab():
    # sub 1 is "Mine" under Medicine; Lab's booking tab is the embedded 'bk' list
    assert "S.tab='records';S.sub=1" not in UH
    assert "function gbBookTest(){S.tab='records';" in UH and "inTab('bk',openLabs)}" in UH
    assert 'onclick="gbBookTest()">Book a home test' in UH


def test_report_card_counts_only_the_persons_own_results():
    i = UH.index("function recCard(")
    head = UH[i:i + 400]
    assert "!isFactRow(f)" in head and "!BABY_RX.test(f.test||'')" in head


def test_lab_headline_counts_reports_and_eyebrow_is_short():
    assert "' report'+(n===1?'':'s'),n===1?'is in range':'are all in range'" in UH
    assert "'LAB · HOME COLLECTION':S.sub==='ord'?'LAB · BOOKINGS':'LAB'" in UH and "records:'YOUR REPORTS'" not in UH
