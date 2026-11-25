"""r151: Settings follows the approved design ("Settings")."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_settings_leads_with_notifications_and_the_medical_id():
    s = _fn("openSettings")
    assert "Notifications are off." in s and "enablePush()" in s and "ps.notif?''" in s
    assert "class=\"card smid\"" in s and "medIdCard(me)" in s
    assert "@media (min-width:1100px){.setlp .smid{display:none}}" in UH  # the laptop already shows it on the right


def test_rows_say_where_each_stands():
    s = _fn("openSettings")
    assert "two is safer" in s and "Privacy and your rights" in s and "openPrivacy()" in s and "id=\"shsum\"" in s
    for kept in ("Sign-in and security", "Permissions", "Simple mode for elders", "My doctors"):
        assert kept in s  # nothing that existed is lost
