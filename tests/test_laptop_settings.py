"""Laptop Settings and Privacy follow their boards: they open inside the app frame (header and tab bar stay),
in three columns, and the tab bar closes them."""
from pathlib import Path

H = (Path(__file__).resolve().parent.parent / "web" / "uh.html").read_text()


def test_settings_and_privacy_open_in_the_frame():
    assert "const PFRAME=['Settings','Privacy and your rights']" in H
    assert "PFRAME.includes(title)?' pfr'" in H
    assert ".page.pfr>.pbar{display:none!important}" in H


def test_tab_bar_closes_a_framed_page():
    assert "if($('#layer .page.pfr')){closeL();if(k===t)return renderAll()}" in H


def test_settings_board_groups():
    i = H.index("function settingsWide(")
    body = H[i:H.index("\n/* Laptop Settings (approved mockup", i)]
    for t in ("Sharing", "This app", "Emergency", "Permissions on this device", "Privacy and your rights",
              "My doctors", "Sign out", "Blood donor", "On my lock screen", "to finish"):
        assert t in body, t
    assert "if(innerWidth>=980)return page('Settings',settingsWide(" in H


def test_privacy_board_columns():
    i = H.index("function privacyWide(")
    body = H[i:H.index("function openData()", i)]
    for t in ("Your records are", "Who can see what", "Recent access", "Permissions", "Consent history",
              "Your rights", "Questions or complaints", "Digital Personal Data Protection Act"):
        assert t in body, t
    assert "permToggle('${k}',${!ok})" in body
