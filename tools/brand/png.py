import asyncio,json,re
from playwright.async_api import async_playwright
F=json.load(open('files.json'))
JOBS=[]
for v in ('user','partner','admin'):
    for s in (1024,512,192,180,32): JOBS.append((f'{v}-icon',s,s,f'{v}-icon-{s}'))
    JOBS.append((f'{v}-icon-maskable',512,512,f'{v}-icon-maskable-512'))
    for n in (f'{v}-logo',f'{v}-logo-white'): JOBS.append((n,None,160,n))
JOBS+= [('user-logo-stacked',None,420,'user-logo-stacked'),('mono-black-logo',None,160,'mono-black-logo'),('mono-white-logo',None,160,'mono-white-logo')]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch();pg=await b.new_page(device_scale_factor=1)
        for n,w,h,out in JOBS:
            svg=F[n];vb=[float(x) for x in re.search(r'viewBox="([^"]+)"',svg).group(1).split()]
            if w is None: w=round(h*vb[2]/vb[3])
            svg=re.sub(r'<svg ',f'<svg width="{w}" height="{h}" ',svg,1).replace(' width="None" height="None"','')
            await pg.set_viewport_size({'width':w,'height':h})
            await pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
            await pg.screenshot(path=f'out/png/{out}.png',omit_background=True,clip={'x':0,'y':0,'width':w,'height':h})
        await b.close()
asyncio.run(main())
