"""r148: Insurance follows the approved designs ("Insurance", "Insurance, claims")."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def test_headline_says_the_amount_and_claims_readiness():
    assert "'covered for ₹'+Number(COVTOT).toLocaleString('en-IN')" in UH
    assert "H('Claim-ready: '+num(CLREADY.done+' of '+CLREADY.n),'papers in place')" in UH
    assert "'INSURANCE · CLAIMS'" in UH and "'INSURANCE · FAMILY'" in UH


def test_policy_card_names_the_insurer_without_cutting_it():
    assert "<span class=\"bce\"><span>${esc(String(c.name||'').toUpperCase())}</span><span>${c.last4?'•••• '+esc(c.last4)" in UH
    assert ".bce>span:first-child{white-space:normal!important;overflow:visible!important;text-overflow:clip!important" in UH
    assert ";height:196px;" not in UH and "min-height:196px;" in UH


def test_show_card_row_and_delivery_hint():
    assert "<b>Show card at hospital desk</b>" in UH
    assert "See what ${p.self?'your':'the'} cover pays for delivery." in UH and "can(p,'summary')" in UH


def test_claim_papers_say_who_provides_them():
    assert "['preauth','Pre-authorisation form','','The hospital’s TPA desk fills it']" in UH
    assert "'Ask your doctor at the visit'" in UH


def test_eyebrow_puts_the_tab_first_and_wraps():
    assert "eyebrowOf(p)+' · '+esc((firstName(p)||nameOf(p)).toUpperCase())" in UH
    assert "#top .ttl .eyebrow,#top .gbg{white-space:normal!important" in UH
