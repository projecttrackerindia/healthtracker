"""Screen sweep: open every main screen of /app on a phone and a laptop, scroll each one to the end, and fail if any
screen cannot reach its bottom or the page throws a script error.

Runs against a local server started with OTP_DEMO=1 (see .github/workflows/ui-sweep.yml):

    python tools/ui_sweep.py http://localhost:8077

It exists because unit tests never open a screen: on 14 Nov 2026 a cut-off CSS rule made every long page unscrollable
on phones and 1,000+ tests still passed.
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from playwright.async_api import async_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8077").rstrip("/")
OUT = sys.argv[2] if len(sys.argv) > 2 else "sweep"
TABS = ["summary", "records", "meds", "cover", "visits"]
OPENERS = ("openSettings openAddresses openContacts openDoctors openMedId openLanguage openNotifSettings openBookings openSecurity "
           "openPrivacy openAccessLog openCycle openSharing openProfile openOrders openLabs openBook openBag openInbox openAidList "
           "openNominee openConsents openData openSimple openPregnancy openHealthCard openScans openVital openEmergencySetup "
           "openSchemes openVax").split()
SIZES = [(390, 844, True), (1366, 768, False)]

TARGET = """() => {
  // whatever is under the finger in the middle of the screen, and the nearest thing above it that scrolls
  const x = innerWidth / 2, y = innerHeight * 0.6;
  let el = document.elementFromPoint(x, y), kind = 'fits';
  while (el && el !== document.documentElement) {
    const cs = getComputedStyle(el);
    const over = el.scrollHeight > el.clientHeight + 4;
    if (over && /auto|scroll/.test(cs.overflowY)) { kind = el.closest('.sheetx') ? 'sheet' : el.closest('#layer') ? 'page' : 'main'; break; }
    // a fixed panel ends the search: if its content is taller than the screen it must be the scroller (and a clipped
    // one is exactly the bug this sweep exists for); if it fits, nothing underneath can be reached anyway
    if (cs.position === 'fixed') { if (over) { kind = 'page'; break; } el = null; break; }
    el = el.parentElement;
  }
  if (!el || el === document.documentElement) { el = document.scrollingElement; if (kind === 'fits') el = {scrollTop: 0, scrollHeight: 0, clientHeight: 0}; }
  window.__sweepEl = el;
  return {kind, x: Math.round(x), y: Math.round(y)};
}"""
STATE = "() => { const el = window.__sweepEl; return [el.scrollTop, el.scrollHeight - el.clientHeight]; }"


async def signed_in(ctx) -> None:
    """A fresh account through the real sign-up API (OTP_DEMO returns the code), with AI reading declined."""
    u = uuid.uuid4().hex[:8]
    h = {"x-tht": "1", "content-type": "application/json"}
    r = await ctx.request.post(BASE + "/api/v1/auth/signup/start", headers=h, data={
        "name": "Sweep Tester", "email": f"sweep{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    j = await r.json()
    r = await ctx.request.post(BASE + "/api/v1/auth/signup/verify", headers=h, data={"flow": j["flow"], "code": j["demo"]})
    assert r.ok, await r.text()
    await ctx.request.put(BASE + "/api/v2/permissions", headers=h, data={"items": {"ai_reports": False, "reminders": False, "nearby_care": False, "emergency_location": False}, "via": "app"})
    # what onboarding saves: the person's own profile and one emergency contact; the language is chosen on the device
    r = await ctx.request.post(BASE + "/api/v2/people", headers=h, data={"name": "Sweep Tester", "profile": {"dob": "1990-04-12", "sex": "female", "blood": "O+"}})
    assert r.ok, await r.text()
    pid = (await r.json())["id"]
    await ctx.request.post(BASE + f"/api/v2/people/{pid}/records", headers=h, data={"kind": "contact", "data": {"name": "Ravi", "phone": "9840011122", "relation": "Brother"}})
    await ctx.add_init_script("try{localStorage.setItem('uh-lang','en');localStorage.setItem('uh-lang-chosen','1')}catch(_){}")


async def sweep(b, w, h, mob, problems: list) -> None:
    ctx = await b.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob)
    await signed_in(ctx)
    pg = await ctx.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)[:160]))
    for typ, name in [("tab", t) for t in TABS] + [("fn", f) for f in OPENERS]:
        try:
            if typ == "tab":
                await pg.goto(f"{BASE}/app/{name}", wait_until="load")
            else:
                await pg.goto(f"{BASE}/app", wait_until="load")
                await pg.wait_for_timeout(700)
                if not await pg.evaluate(f"typeof {name}==='function'&&({name}(),true)"):
                    continue
                try:   # screens that fetch first open a moment later
                    await pg.wait_for_selector("#layer .page, .sheetx .sh", timeout=5000)
                except Exception:
                    pass
            await pg.wait_for_timeout(1400)
            t = await pg.evaluate(TARGET)
            await pg.mouse.move(t["x"], max(60, t["y"]))
            for _ in range(14):
                await pg.mouse.wheel(0, 500)
                await pg.wait_for_timeout(80)
            await pg.wait_for_timeout(350)
            top, need = await pg.evaluate(STATE)
            if need > 2 and top < need - 3:
                problems.append(f"{w}px {name}: stuck at {top} of {need}px ({t['kind']})")
                await pg.screenshot(path=f"{OUT}-{w}-{name}.png")
        except Exception as e:   # a screen that cannot open at all is reported, not hidden
            problems.append(f"{w}px {name}: {type(e).__name__}: {str(e)[:120]}")
    problems += [f"{w}px script error: {e}" for e in dict.fromkeys(errors)]
    await ctx.close()


async def main() -> int:
    problems: list[str] = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, h, mob in SIZES:
            await sweep(b, w, h, mob, problems)
        await b.close()
    for x in problems:
        print("✗", x)
    print(f"{len(problems)} problem(s) across {len(SIZES)} sizes" if problems else f"✓ every screen scrolls to its end at {', '.join(str(s[0]) for s in SIZES)} px, no script errors")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
