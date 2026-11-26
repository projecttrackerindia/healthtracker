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


def test_report_opens_as_a_panel_beside_the_lab_list():
    assert "if(innerWidth>=980){if(S.tab!=='records'){S.tab='records';S.sub=0;renderAll()}PGSIDE=1;return page(recTitle(r),repSide(p,r))}" in H
    i = H.index("function repSide(")
    body = H[i:H.index("function openReport(", i)]
    for t in ("in range", "READ FOR YOU", "See these values on your body", "Share with a doctor", "Show "):
        assert t in body, t
    assert "function repBar(" in H and "normal ${lo} to ${hi}" in H


def test_visits_book_and_history_rails():
    assert "<div class=\"rhd2\">Past visits</div>" in H and "<div class=\"rhd2\">Before your next visit</div>" in H
    assert "<div class=\"rhd2\">Due and upcoming</div>" in H and "${vzReasons(p)}${vzSoon(p)}${AC('')}" in H


def test_order_tracking_sits_in_the_frame_on_laptop():
    assert "#layer:has(.trk)>.scrim" in H and "body:has(#layer .trk) .srail{visibility:hidden}" in H


def test_sos_on_laptop_click_opens_hold_screen_and_keeps_the_cancel_window():
    assert "if(innerWidth>=980)sosHoldScreen();else{b.classList.add('tipon')" in H
    i = H.index("function sosHoldScreen(")
    body = H[i:H.index("function lockCard(", i)]
    assert "Hold for 2 seconds" in body and "5 seconds to cancel" in body and "sosConfirm()" in body
    assert "where one is live" in body and "dial it from your phone" in body
    assert "if(innerWidth>=980)sosWide();sosPaint();" in H


def test_prescription_and_pharmacy_open_as_panels_on_laptop():
    assert "PGSIDE=innerWidth>=980?'Choose a pharmacy':0;" in H
    assert "PGSIDE=innerWidth>=980?'Your order':0;" in H
    assert "Check what we read before it reminds you" in H and "Nothing reminds you until you confirm" in H
    assert "if(!(innerWidth>=980&&PGSIDE)&&EMB&&EMB.live" in H


def test_family_today_panel_and_lab_side_steps():
    assert "'Emergency setup','Family'];" in H and "${WF?`</div><div>${famTodayPanel()}</div></div>`:''}" in H
    i = H.index("function famTodayPanel(")
    body = H[i:H.index("function ddFamily(", i)]
    for t in ("Everyone, in", "medicines taken", "Nothing due today", "What I share with family", "Add a parent to look after"):
        assert t in body, t
    assert "PGSIDE=innerWidth>=980?'Choose a lab':0;" in H and "PGSIDE=innerWidth>=980?'Review and pay':0;" in H


def test_signup_steps_follow_the_boards_order_and_frame():
    assert "step=step??(!me?0:PERMS&&!PERMS.asked?2:!(me.medicalId.contacts||[]).length?3:4);" in H
    assert "Who should we call <span class=\"hpl\">first</span>?" in H and "You decide each one, <span class=\"hpl\">separately</span>" in H
    assert "$('#on3').onclick=async()=>{await permsSave('signup');onboard(3)}}" in H
    assert "${step+1} of 5" in H and "Create your account</b><span>1 of 5" in H


def test_first_run_and_ask_panel_on_laptop():
    i = H.index("function firstRunScreen(")
    body = H[i:H.index("async function finishOnboarding(", i)]
    assert "Start with" in body and "Coming soon" in body and "Skip for now" in body
    assert "modal glass${W?' aiw':''}" in H and "Tap and speak, in any of these languages" in H


def test_body_viewer_laptop_panel_follows_the_board():
    B = (Path(__file__).resolve().parent.parent / "web" / "body.html").read_text()
    assert "if(innerWidth>=980&&!KID)return sheet(bodyWide(L));" in B
    i = B.index("function bodyWide(")
    body = B[i:B.index("/* Body map summary", i)]
    for t in ("in range", "to watch", "Needs a look", "In range", "Book a recheck", "Not a diagnosis"):
        assert t in body, t
    assert "exFitBox(b,.62)" in B
    O = (Path(__file__).resolve().parent.parent / "web" / "organs2.js").read_text()
    assert "!c.querySelector('.bwt')" in O


def test_laptop_sign_in_has_steps_and_languages():
    assert "New accounts take about two minutes" in H and "class=\"alang\"" in H
    assert "#layer .page.auth .pin.aflow{background:transparent!important}" in H


def test_page_behind_a_framed_page_is_hidden():
    assert "body:has(#layer .page.pfr) .gbl{opacity:0!important;visibility:hidden!important}" in H
