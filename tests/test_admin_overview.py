"""Admin Overview follows its board (launch readiness, services locked until a partner is live), and the server
keeps medicine, tests and visits closed to families until a licensed partner is live."""
from pathlib import Path

A = (Path(__file__).resolve().parent.parent / "admin" / "index.html").read_text()
C = (Path(__file__).resolve().parent.parent / "api" / "compliance.py").read_text()


def test_overview_board_parts():
    i = A.index("VIEWS.today=async()=>{")
    body = A[i:A.index("let TH_K='';", i)]
    for t in ("Launch is", "ready</span>", "Before families can order", "Services families see", "Locked",
              "Unlocks when 1 ", "A service cannot be switched on without a live partner", "NEEDS YOU", "Live board",
              "Clinical review", "Messages", "Catalogue", "Practice mode"):
        assert t in body, t


def test_server_refuses_a_service_without_a_live_partner():
    assert 'if b.on and not _live(db, key):' in C and "raise HTTPException(409" in C
    assert 'return {k: bool(_live(db, k)) for k in SERVICES}' in C
    assert 'v["on"] and bool(_live(db, k))' in C
