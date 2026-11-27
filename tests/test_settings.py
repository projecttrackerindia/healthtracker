"""r151: Settings follows the approved design ("Settings")."""
from pathlib import Path

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text(encoding="utf-8")


def _fn(name):
    i = UH.index("function %s(" % name)
    return UH[i:UH.index("\nfunction ", i + 10)]


def test_settings_leads_with_notifications_and_the_medical_id():
    """27 Nov: Settings became the You menu; it still leads with the notifications banner and the Medical ID."""
    assert "function openSettings(){openYou()}" in UH
    s = UH[UH.index("function openYou("):UH.index("function famSub(")]
    assert "Notifications are off." in s and "enablePush()" in s and "ps.notif?''" in s
    assert "${yuMid(me)}" in s and "function yuMid(" in UH


def test_rows_say_where_each_stands():
    s = UH[UH.index("function yuLists("):UH.index("function yuTodo(")]
    assert "Add one more" in s and "My data and rights" in s and "openPrivacy()" in s and 'id="shsum"' in s
    for kept in ("Sign-in and security", "Notifications and permissions", "Simple mode for elders", "My doctors", "Emergency contacts", "First aid", "Language"):
        assert kept in s  # nothing that existed is lost
