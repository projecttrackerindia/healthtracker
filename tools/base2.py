# Build orig2.html: orig.html with the pregnancy module (3D mother/baby, fetus worker, knowledge base, tabs) taken from
# DoKKo_Anatomy_Lab_Demo_2.html (the newer pregnancy build), plus its adaptive render-quality helper.
import re
U='/root/.claude/uploads/a8bd75e4-9e39-5596-8630-53b2347ba3bf/c32aa93d-DoKKo_Anatomy_Lab_Demo_2.html'
D=open(U).read(); s=open('orig.html').read()
SEC=lambda t,n:t.index('// ===================== '+n)
# 1. worker source
a=s.index('<script id="fxsrc" type="text/plain">')+len('<script id="fxsrc" type="text/plain">'); b=s.index('</script>',a)
da=D.index('<script id="fxsrc" type="text/plain">')+len('<script id="fxsrc" type="text/plain">'); db=D.index('</script>',da)
s=s[:a]+D[da:db]+s[b:]
# 2. main-thread pregnancy sections: knowledge base … end of 3D viewer
i0=SEC(s,'pregnancy knowledge base'); i1=SEC(s,'generated audio')
j0=SEC(D,'pregnancy knowledge base'); j1=SEC(D,'generated audio')
s=s[:i0]+D[j0:j1]+s[i1:]
# 3. PERF helper (adaptive pixel ratio) in front of the clinical knowledge section
p0=SEC(D,'adaptive render quality'); p1=D.index('const $=s=>document.querySelector(s)',p0)
perf=D[p0:p1]
k=s.index('// ===================== clinical knowledge')
s=s[:k]+perf+s[k:]
# 4. stage markup: activity caption element
old='<div id="pld" class="pld">Building 3D mother &amp; baby…</div><div class="pbuild" id="pbuild" hidden></div>'
assert s.count(old)==1
s=s.replace(old,'<div id="pld" class="pld">Building 3D mother &amp; baby…</div><div class="pact" id="pact" hidden></div><div class="pbuild" id="pbuild" hidden></div>')
# 5. CSS: rules whose selectors are new in Demo2 (activity caption, behaviours, biology panels, build spinner)
def css(t):
    cs=t.index('<style>');ce=t.index('</style>',cs); return cs+7,ce,t[cs+7:ce]
def rules(t):
    out=[];depth=0;cur=''
    for ch in t:
        cur+=ch
        if ch=='{':depth+=1
        elif ch=='}':
            depth-=1
            if depth==0: out.append(cur.strip());cur=''
    return out
_,_,cd=css(D); cs0,ce0,co=css(s)
sel=lambda r:r.split('{',1)[0].strip()
have=set(sel(r) for r in rules(co))
add=[r for r in rules(cd) if sel(r) not in have and not sel(r).startswith('/*')]
stop=next(i for i,r in enumerate(add) if sel(r).startswith('.ksrch'))
add=add[:stop]
# rose recolour of the build spinner, keep Demo2 geometry
pb=[r for r in rules(cd) if sel(r)=='.pbuild'][0].replace('rgba(6,18,42,.78)','rgba(40,10,24,.78)').replace('#e3efff','#ffe3ec')
add=[r.replace('rgba(6,18,42,.75)','rgba(40,10,24,.75)').replace('#a8c8ff','#ffc9d8').replace('#e9f2ff','#fff0f5').replace('rgba(227,239,255,.35)','rgba(255,227,236,.35)').replace('border-top-color:#e3efff','border-top-color:#ffe3ec').replace('rgba(10,20,40,.6)','rgba(40,8,20,.6)') for r in add]
s=s[:ce0]+'\n/* ---- pregnancy v2 (Demo 2) additions ---- */\n'+'\n'.join(add+[pb])+'\n'+s[ce0:]
open('orig2.html','w').write(s)
print('ok',len(s),'css added',len(add))
