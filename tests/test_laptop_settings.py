"""Laptop Settings and Privacy follow their boards: they open inside the app frame (header and tab bar stay),
in three columns, and the tab bar closes them."""
from pathlib import Path

H = (Path(__file__).resolve().parent.parent / "web" / "uh.html").read_text()


def test_settings_and_privacy_open_in_the_frame():
    assert "const PFRAME=['Settings','Privacy and your rights'," in H
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


def test_notifications_needs_you_panel():
    i = H.index("function needsList(")
    body = H[i:H.index("function medIdWide(", i)]
    for t in ("Overdue", "Window closes week", "Running low", "Routine", "Later", "Done",
              "How this list is ordered", "You only see what each person shares with you"):
        assert t in body, t
    assert "${wide?`</div><div>${needsPanel()}</div></div>`:''}" in H


def test_medical_id_on_laptop_is_the_dark_card():
    assert "if(innerWidth>=980)return page('Medical ID',medIdWide(me));" in H
    i = H.index("function medIdWide(")
    body = H[i:H.index("function openData()", i)]
    for t in ("/qr.svg", "Add to my lock screen", "Print the card", "Called first", "Edit details"):
        assert t in body, t
    assert "@media print{" in H


def test_emergency_setup_has_the_medical_id_column():
    assert "Your Medical ID and contacts" in H and "${esRows(me)}" in H
    assert "'Notifications','Emergency setup'" in H
    assert ".page.pfr .pin{max-width:1400px!important;padding:0 24px!important;columns:auto!important}" in H
