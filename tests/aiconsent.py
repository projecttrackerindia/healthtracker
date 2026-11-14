"""Test helper: what a real person does before any AI reads their records — sign in and say yes to "AI reads my reports"."""
import uuid

H = {"x-tht": "1"}


def ai_yes(c, signed_in: bool = False):
    if not signed_in:
        u = uuid.uuid4().hex[:8]
        r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Test Person", "email": f"ai{u}@example.com",
                                                                  "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
        assert c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]}).status_code == 200
    assert c.put("/api/v2/permissions", headers=H, json={"items": {"ai_reports": True}, "via": "app"}).status_code == 200
    return c
