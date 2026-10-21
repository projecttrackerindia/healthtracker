import asyncio
import base64
from playwright.async_api import async_playwright
SET_PREG="(()=>{SX.setActive('m2');const m=SX.me();const l=new Date(Date.now()-30*7*864e5).toISOString().slice(0,10);SX.S.preg=SX.S.preg||{};SX.S.preg[m.id]={on:true,lmp:l,t:Date.now()};SX.save(true)})()"
async def shoot(pg, path, w, h, dsf):
    """Capture without waiting for a stable frame.

    page.screenshot() blocks until the renderer settles, and the anatomy canvas never settles, so every
    dashboard shot timed out. CDP captures immediately. It ignores the context's device_scale_factor, so the
    scale belongs in the clip or the file comes back at 1x."""
    await pg.add_style_tag(content="#lv16demo{display:none!important}")   # the demo bar sits over the organ chips
    cdp = await pg.context.new_cdp_session(pg)
    shot = await cdp.send("Page.captureScreenshot", {
        "format": "png", "captureBeyondViewport": False,
        "clip": {"x": 0, "y": 0, "width": w, "height": h, "scale": dsf}})
    open(path, 'wb').write(base64.b64decode(shot["data"]))


async def ready(pg):
    for i in range(150):
        if await pg.evaluate("typeof A!=='undefined'&&A.ready===true"): break
        await pg.wait_for_timeout(1000)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
        # desktop light, 2x
        ctx=await b.new_context(viewport={'width':1440,'height':900},device_scale_factor=2,color_scheme='light'); pg=await ctx.new_page();pg.set_default_timeout(180000)
        await pg.add_init_script("window.__raf=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=cb=>setTimeout(()=>window.__raf(cb),400)")
        await pg.goto('http://localhost:8099/app?demo=1'); await ready(pg); await pg.evaluate("document.documentElement.dataset.theme='light'"); await pg.wait_for_timeout(2500)
        await shoot(pg, 'landing_src/desk_dash.png', 1440, 900, 2)
        await pg.evaluate("go('heart')"); await pg.wait_for_timeout(12000); await shoot(pg, 'landing_src/desk_heart.png', 1440, 900, 2)
        await pg.evaluate("SX.S.consent.ai_analysis=true;go('vault')"); await pg.wait_for_timeout(800); await pg.click('[data-sx="ai:v1"]'); await pg.wait_for_timeout(2500); await shoot(pg, 'landing_src/desk_ai.png', 1440, 900, 2)
        await pg.evaluate("SX.closeModal();SX.act.labs(['hba1c+lipid+tsh'])"); await pg.wait_for_timeout(2500); await shoot(pg, 'landing_src/desk_labs.png', 1440, 900, 2)
        await pg.evaluate("SX.closeModal();SX.S.cart=[{id:'para500',m:'m1',q:2},{id:'ator10',m:'m1',q:1}];SX.save(true);SX.act.cart()"); await pg.wait_for_timeout(2500); await shoot(pg, 'landing_src/desk_cart.png', 1440, 900, 2)
        await pg.evaluate("SX.closeModal();"+SET_PREG); await pg.reload(); await ready(pg); await pg.evaluate("document.documentElement.dataset.theme='light';go('preg')")
        for i in range(60):
            if await pg.evaluate("typeof PV!=='undefined'&&PV.ready===true"): break
            await pg.wait_for_timeout(1000)
        await pg.evaluate("setPView('baby');setW(30)")
        for i in range(40):
            if await pg.evaluate("document.querySelector('#pbuild').hidden"): break
            await pg.wait_for_timeout(500)
        await pg.wait_for_timeout(3000); await shoot(pg, 'landing_src/desk_preg.png', 1440, 900, 2)
        await pg.evaluate("setPView('mother');setW(28)"); await pg.wait_for_timeout(6000); await shoot(pg, 'landing_src/desk_mother.png', 1440, 900, 2)
        await ctx.close()
        # phone dark 3x
        ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=3,color_scheme='dark',is_mobile=True,has_touch=True); pg=await ctx.new_page();pg.set_default_timeout(180000)
        await pg.goto('http://localhost:8099/app?demo=1'); await ready(pg); await pg.evaluate("document.documentElement.dataset.theme='dark'"); await pg.wait_for_timeout(2500)
        await shoot(pg, 'landing_src/phone_dash.png', 390, 844, 3)
        await pg.evaluate("go('sos')"); await pg.wait_for_timeout(1500); await shoot(pg, 'landing_src/phone_sos.png', 390, 844, 3)
        await b.close()
asyncio.run(main())
