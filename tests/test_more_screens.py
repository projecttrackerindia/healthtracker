"""r154: the remaining family screens follow their boards (Family, Claims, Buy, Government, Mine, Orders, Emergency setup, Privacy)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UH = (ROOT / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_full_pages_have_title_and_done_on_one_row():
    p = _fn("page")
    assert 'class="pbar pbx"' in p and 'class="ptl"' in p and ">Done</button>" in p
    assert "PREV?'pdone':'pback pdone'" in p  # a top-level page's Done goes back the same way Back did


def test_avatar_opens_the_family_page():
    f = _fn("ddFamily")
    assert "page('Family'" in f and "Add family member" in f and "Each person’s records stay private to them" in f
    assert "dd('#who'" not in f


def test_insurance_tabs_have_their_own_headlines():
    t = _fn("gbTab")
    assert "Know what to look for" in t and "already have" in t and "'Claim-ready: '" in t
    assert "Schemes we check" in UH and "Never pay an agent." in UH and "Tell me when quotes are ready" in UH


def test_privacy_grid_reflects_real_sharing_levels():
    p = _fn("openPrivacy")
    assert "Who can see what" in p and "on(r,c[0])" in p and "openSharing()" in p
    assert "Tap a person to change what they see." in p  # the grid opens the real editor; it does not pretend a circle saves on tap
    for keep in ("exportData()", "openProfile()", "openNominee()", "openChanges()", "deleteAccount()"):
        assert keep in p  # every right stays one tap away


def test_order_card_offers_a_refund_only_when_paid():
    c = _fn("ordCard")
    assert "Ask for a refund" in c and "paid?" in c
