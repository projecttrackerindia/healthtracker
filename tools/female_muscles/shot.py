import sys
from playwright.sync_api import sync_playwright
jobs=[a.split('=',1) for a in sys.argv[1:]]
with sync_playwright() as p:
    br=p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--ignore-gpu-blocklist"])
    for out,q in jobs:
        pg=br.new_page(viewport={"width":900,"height":1100}); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e))); pg.on("console",lambda m:errs.append(m.text) if m.type=='error' else None)
        pg.goto("http://localhost:8901/h.html?"+q); pg.wait_for_function("window.__done",timeout=120000); pg.wait_for_timeout(300)
        pg.screenshot(path=out); print(out,errs[:2]); pg.close()
