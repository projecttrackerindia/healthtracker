"""Builds the hospital bag page (site/home/bag.html, with .br and .gz) and its policies page (site/home/policies.html)
from the sources in this folder. Run: python3 tools/bagpage/build.py"""
import os,re,gzip,pathlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];os.chdir(HERE)
css=open("style.css").read();body=open("body.html").read();main=open("main.js").read();art=open("art.js").read();mod=open("three.js").read()
logo=open("logo.html").read().replace('href="#home"','href="/"');footer=open("footer.html").read()
CK='<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l4 4 10-10"/></svg>'
body=body.replace("/*LOGO*/",logo).replace("/*FOOTER*/",footer).replace("/*CK*/",CK)
main=main.replace("/*ART*/",art)
land=open(ROOT/"site/home/index.html").read()
icon=re.search(r'<link rel="icon"[^>]*>',land).group(0)
head='''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hospital Bag · Urban Health</title>
<meta name="description" content="A hospital bag for you and your baby, with Mee Mee, SuperBottoms and Pee Safe essentials, shaped around your delivery and delivered before week 36. Take the complete bag or build your own.">
<meta name="theme-color" content="#FFFFFF">
<link rel="canonical" href="https://urbanhealth.in/hospital-bag">
<meta property="og:type" content="website"><meta property="og:site_name" content="Urban Health"><meta property="og:url" content="https://urbanhealth.in/hospital-bag">
<meta property="og:title" content="Hospital Bag · Urban Health"><meta property="og:description" content="Packed around you, at your door before week 36.">
<meta property="og:image" content="https://urbanhealth.in/s/img/og.png">
'''+icon+'''
<link rel="preload" href="/s/fonts/geist.woff2" as="font" type="font/woff2" crossorigin><style>@font-face{font-family:Geist;src:url(/s/fonts/geist.woff2) format('woff2');font-weight:100 900;font-display:swap}</style>
<script type="importmap">{"imports":{"three":"/s/home/js/three-0.160.0/three.module.min.js"}}</script>
<link rel="modulepreload" href="/s/home/js/three-0.160.0/three.module.min.js">
<style>
'''+css+'''</style>
</head>
'''
out=head+body+"<script>\n"+main+"\n</script>\n<script type=\"module\">\n"+mod+"\n</script>\n</body>\n</html>\n"
p=ROOT/"site/home/bag.html";p.write_text(out)
d=out.encode();pathlib.Path(str(p)+".gz").write_bytes(gzip.compress(d,9))
import brotli;pathlib.Path(str(p)+".br").write_bytes(brotli.compress(d,quality=11))
print("built",len(out))

# ---- the policies page ----

V=str(HERE)+"/";P=str(HERE/"pol")+"/"
css=open(V+"style.css").read().split("\n")
base="\n".join(css[:50])   # tokens, base elements, buttons and the header (same as the bag page)
assert css[49].startswith(".gin .lk.on::after"),css[49]
foot=[l for l in css if l.startswith("footer{") or l.startswith("footer .wrap")]
assert len(foot)==2
body=open(P+"body.html").read()
logo=open(V+"logo.html").read().replace('href="#home"','href="/"')
body=body.replace("/*LOGO*/",logo).replace("/*FOOTER*/",open(V+"footer.html").read())
land=open(ROOT/"site/home/index.html").read()
icon=re.search(r'<link rel="icon"[^>]*>',land).group(0)
head='''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Returns, refunds and delivery · Urban Health</title>
<meta name="description" content="Urban Health hospital bag policies: 7-day returns and exchanges, free cancellation until packed, refunds within 5 to 7 working days, free delivery across India.">
<meta name="theme-color" content="#FFFFFF">
<link rel="canonical" href="https://urbanhealth.in/hospital-bag/policies">
<meta property="og:type" content="website"><meta property="og:site_name" content="Urban Health"><meta property="og:url" content="https://urbanhealth.in/hospital-bag/policies">
<meta property="og:title" content="Returns, refunds and delivery · Urban Health"><meta property="og:description" content="Simple terms, written plainly.">
'''+icon+'''
<link rel="preload" href="/s/fonts/geist.woff2" as="font" type="font/woff2" crossorigin><style>@font-face{font-family:Geist;src:url(/s/fonts/geist.woff2) format('woff2');font-weight:100 900;font-display:swap}</style>
<style>
'''+base+"\n"+"\n".join(foot)+"\n"+open(P+"pol.css").read()+'''</style>
</head>
'''
out=head+body
(ROOT/"site/home/policies.html").write_text(out)
print("built",len(out))
