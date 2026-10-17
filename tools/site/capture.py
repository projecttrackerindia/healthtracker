import asyncio
from playwright.async_api import async_playwright
SET_PREG="(()=>{SX.setActive('m2');const m=SX.me();const l=new Date(Date.now()-30*7*864e5).toISOString().slice(0,10);SX.S.preg=SX.S.preg||{};SX.S.preg[m.id]={on:true,lmp:l,t:Date.now()};SX.save(true)})()"
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
        await pg.goto('http://localhost:8099/app'); await ready(pg); await pg.evaluate("document.documentElement.dataset.theme='light'"); await pg.wait_for_timeout(2500)
        await pg.screenshot(path='landing_src/desk_dash.png')
        await pg.evaluate("go('heart')"); await pg.wait_for_timeout(12000); await pg.screenshot(path='landing_src/desk_heart.png')
        await pg.evaluate("SX.S.consent.ai_analysis=true;go('vault')"); await pg.wait_for_timeout(800); await pg.click('[data-sx="ai:v1"]'); await pg.wait_for_timeout(2500); await pg.screenshot(path='landing_src/desk_ai.png')
        await pg.evaluate("SX.closeModal();SX.act.labs(['hba1c+lipid+tsh'])"); await pg.wait_for_timeout(2500); await pg.screenshot(path='landing_src/desk_labs.png')
        await pg.evaluate("SX.closeModal();SX.S.cart=[{id:'para500',m:'m1',q:2},{id:'ator10',m:'m1',q:1}];SX.save(true);SX.act.cart()"); await pg.wait_for_timeout(2500); await pg.screenshot(path='landing_src/desk_cart.png')
        await pg.evaluate("SX.closeModal();"+SET_PREG); await pg.reload(); await ready(pg); await pg.evaluate("document.documentElement.dataset.theme='light';go('preg')")
        for i in range(60):
            if await pg.evaluate("typeof PV!=='undefined'&&PV.ready===true"): break
            await pg.wait_for_timeout(1000)
        await pg.evaluate("setPView('baby');setW(30)")
        for i in range(40):
            if await pg.evaluate("document.querySelector('#pbuild').hidden"): break
            await pg.wait_for_timeout(500)
        await pg.wait_for_timeout(3000); await pg.screenshot(path='landing_src/desk_preg.png')
        await pg.evaluate("setPView('mother');setW(28)"); await pg.wait_for_timeout(6000); await pg.screenshot(path='landing_src/desk_mother.png')
        await ctx.close()
        # phone dark 3x
        ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=3,color_scheme='dark',is_mobile=True,has_touch=True); pg=await ctx.new_page();pg.set_default_timeout(180000)
        await pg.goto('http://localhost:8099/app'); await ready(pg); await pg.evaluate("document.documentElement.dataset.theme='dark'"); await pg.wait_for_timeout(2500)
        await pg.screenshot(path='landing_src/phone_dash.png')
        await pg.evaluate("go('sos')"); await pg.wait_for_timeout(1500); await pg.screenshot(path='landing_src/phone_sos.png')
        await b.close()
asyncio.run(main())
