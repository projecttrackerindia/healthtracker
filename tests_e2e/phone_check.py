"""Phone check: the real app on an iPhone 15 (WebKit, Safari's engine) and a Pixel 7 (Chrome).

Walks the screens people use most and fails on what a person would notice:
  * a page narrower or wider than the screen, or not at the left edge (the 13 Nov "squeezed Settings" bug)
  * anything wider than the screen (sideways scrolling, Safari zooming out)
  * a JavaScript error
Screenshots of every step land in tests_e2e/out/ so a red run can be looked at, not guessed at.

    python tests_e2e/phone_check.py            # starts its own server on a scratch database
    BASE=http://localhost:8000 python tests_e2e/phone_check.py   # or check a server you already run
"""
from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "out"
H = {"x-tht": "1"}
FAIL: list[str] = []


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_server() -> tuple[str, subprocess.Popen | None]:
    if os.getenv("BASE"):
        return os.environ["BASE"].rstrip("/"), None
    port = free_port()
    db = Path(tempfile.mkdtemp()) / "phone.db"
    env = {**os.environ, "APP_ENV": "development", "OTP_DEMO": "1", "SECRET_KEY": "phone-check", "IN_PROCESS_LOOPS": "0",
           "DATABASE_URL": f"sqlite:///{db}"}
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(90):
        try:
            urllib.request.urlopen(base + "/api/health", timeout=2)
            return base, p
        except Exception:
            time.sleep(1)
    p.kill()
    raise SystemExit("server did not start")


GEOMETRY = """(()=>{const w=innerWidth,de=document.documentElement,p=document.querySelector('#layer .page');
 const r=p?p.getBoundingClientRect():null;
 return {w,scrollW:de.scrollWidth,page:r?[Math.round(r.x),Math.round(r.width)]:null,cls:p?p.className:'',
   radius:p?getComputedStyle(p).borderTopRightRadius:'',title:p?(p.dataset.t||''):'',
   scale:window.visualViewport?visualViewport.scale:1}})()"""


async def check(pg, dev: str, step: str, want_page: bool = True) -> None:
    await pg.wait_for_timeout(700)   # let the slide finish
    # Headless WebKit runs animations slower than a phone; finish them so we measure where things end up.
    await pg.evaluate("document.getAnimations().forEach(a=>{try{a.finish()}catch(_){}})")
    await pg.wait_for_timeout(100)
    g = await pg.evaluate(GEOMETRY)
    await pg.screenshot(path=str(OUT / f"{dev}-{step}.png"))
    bad = []
    if g["scrollW"] > g["w"] + 1:
        bad.append(f"content is {g['scrollW']}px wide on a {g['w']}px screen")
    if abs(g["scale"] - 1) > 0.01:
        bad.append(f"view is zoomed to {g['scale']}")
    if want_page:
        if not g["page"]:
            bad.append("no page open")
        elif g["page"][0] != 0 or abs(g["page"][1] - g["w"]) > 1:
            bad.append(f"page '{g['title']}' is at x={g['page'][0]}, {g['page'][1]}px wide on a {g['w']}px screen ({g['cls']}, corner {g['radius']})")
    elif g["page"]:
        bad.append(f"a page is still open: {g['title']}")
    print(f"  {'✗' if bad else '✓'} {dev} · {step}" + (": " + "; ".join(bad) if bad else ""))
    FAIL.extend(f"{dev} · {step}: {b}" for b in bad)


async def tap(pg, js: str) -> None:
    await pg.evaluate(js)


ROW = "[...document.querySelectorAll('#layer .page .li, #layer .page .card, #layer .page button')].find(b=>b.textContent.includes(%r)).click()"


async def walk(p, base: str, engine: str, device: str, dev: str) -> None:
    b = await getattr(p, engine).launch()
    c = await b.new_context(**p.devices[device])
    pg = await c.new_page()
    errs: list[str] = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(base + "/app")
    await pg.wait_for_timeout(1500)
    email = f"{dev}-{int(time.time())}@example.com"
    r = await pg.request.post(base + "/api/v1/auth/signup/start", headers=H, data={
        "name": "Daddala Prasannakrishna", "email": email, "phone": "98765" + str(int(time.time()))[-5:],
        "password": "Chennai#Rain2026!", "terms": True})
    j = await r.json()
    await pg.request.post(base + "/api/v1/auth/signup/verify", headers=H, data={"flow": j["flow"], "code": j["demo"]})
    await pg.request.post(base + "/api/v2/people", headers=H, data={"name": "Daddala Prasannakrishna",
                          "profile": {"sex": "male", "dob": "1997-03-15", "blood": "O+", "height": 157, "weight": 65}})
    me = await (await pg.request.get(base + "/api/v2/me", headers=H)).json()
    pid = me["people"][0]["id"]
    await pg.request.post(f"{base}/api/v2/people/{pid}/records", headers=H,
                          data={"kind": "contact", "data": {"name": "Jyothsna Vadlamudi", "phone": "9123456780", "relation": "Wife"}})
    await pg.evaluate("localStorage.setItem('uh-lang-chosen','1')")
    await pg.goto(base + "/app")
    await pg.wait_for_timeout(4000)
    for _ in range(5):
        if await pg.query_selector("#permpg"):   # first-run permissions page: accept as shown, like a person would
            await pg.evaluate("[...document.querySelectorAll('#layer .page .btn.pri')].find(b=>b.textContent.includes('Continue')).click()")
            await pg.wait_for_timeout(900)
            continue
        bt = await pg.query_selector("text=Not now") or await pg.query_selector("text=Skip")
        if bt:
            await bt.click()
            await pg.wait_for_timeout(600)
    await check(pg, dev, "01-today", want_page=False)

    # Settings through the avatar menu, the way people open it
    await tap(pg, "document.querySelector('#who').click()")
    await pg.wait_for_timeout(700)
    await tap(pg, "[...document.querySelectorAll('.dd .ddr')].find(b=>b.textContent.includes('Profile')).click()")
    await check(pg, dev, "02-settings")
    for name, step in (("Medical ID", "03-medical-id"), ("Emergency contacts", "05-contacts"), ("Language", "07-language")):
        await tap(pg, ROW % name)
        await check(pg, dev, step)
        await tap(pg, "document.querySelector('#layer .pback').click()")
        await check(pg, dev, step[:2] + "b-back-to-settings")
    # going back without the 'still' shortcut: the path that picked up the menu's styles
    await tap(pg, ROW % "Medical ID")
    await pg.wait_for_timeout(700)
    await tap(pg, "NAVSYS=0;navBack()")
    await check(pg, dev, "09-back-plain")
    await tap(pg, "document.querySelector('#layer .pback').click()")
    await check(pg, dev, "10-back-to-today", want_page=False)

    for e in errs:
        print(f"  ✗ {dev} · JavaScript error: {e[:200]}")
        FAIL.append(f"{dev} · JavaScript error: {e[:200]}")
    await b.close()


async def main() -> int:
    OUT.mkdir(exist_ok=True)
    base, proc = start_server()
    try:
        async with async_playwright() as p:
            await walk(p, base, "webkit", "iPhone 15", "iphone15")
            await walk(p, base, "chromium", "Pixel 7", "pixel7")
    finally:
        if proc:
            proc.terminate()
    if FAIL:
        print(f"\nPhone check FAILED ({len(FAIL)}):")
        for f in FAIL:
            print("  -", f)
        return 1
    print("\nPhone check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
