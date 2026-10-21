"""Round 34 patch: places you can use — pick a lab, read it, book it; and the page stops rebuilding under your finger."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p34*/"
s = W.read_text(encoding="utf-8")
if "/*live-p33*/" not in s:
    sys.exit("apply p33 first")
if MARK in s:
    sys.exit("already applied")


def one(old: str, new: str, what: str) -> None:
    global s
    if s.count(old) != 1:
        sys.exit(f"{what}: anchor found {s.count(old)}×")
    s = s.replace(old, new)


# the whole row opens the place sheet; the map keeps its instance instead of being rebuilt on every tap
one("SX.act.mapsel=([id])=>{plSel=decodeURIComponent(id);render();const el=document.querySelector('.lv6-pl.on');if(el)el.scrollIntoView({block:'nearest',behavior:'smooth'})};",
    "SX.act.mapsel=([id])=>{plSel=decodeURIComponent(id);render();const el=document.querySelector('.lv6-pl.on');if(el)el.scrollIntoView({block:'nearest',behavior:'smooth'})};\n"
    "SX.placesData=()=>PLACES;SX.setPlSel=v=>{plSel=v};", "mapsel")
# a Google map that is already on screen pans instead of being thrown away
one("SX.gmapHTML=(center,items,opt={})=>{const id='gm'+(++seq);PENDING[id]={center,items,opt};setTimeout(()=>mount(id),0);return `<div class=\"lv6-map lv13-gmap\" id=\"${id}\" style=\"height:${opt.h||300}px\"><div class=\"lv13-gmap-in\"></div>${opt.act?'':''}</div>`};",
    "SX.gmapHTML=(center,items,opt={})=>{const id='gm'+(++seq);PENDING[id]={center,items,opt};setTimeout(()=>mount(id),0);return `<div class=\"lv6-map lv13-gmap\" id=\"${id}\" style=\"height:${opt.h||300}px\"><div class=\"lv13-gmap-in\"></div>${opt.act?'':''}</div>`};\n"
    "SX.gmapPan=p=>{try{const m=LASTMAP;if(m&&p&&p.lat)m.panTo({lat:p.lat,lng:p.lng})}catch(e){}};", "gmap pan")
one("const map=new google.maps.Map(el.querySelector('.lv13-gmap-in'),{center:{lat:center.lat,lng:center.lng},zoom:opt.zoom||13,disableDefaultUI:true,zoomControl:true,gestureHandling:'greedy',clickableIcons:false}",
    "const map=LASTMAP=new google.maps.Map(el.querySelector('.lv13-gmap-in'),{center:{lat:center.lat,lng:center.lng},zoom:opt.zoom||13,disableDefaultUI:true,zoomControl:true,gestureHandling:'greedy',clickableIcons:false}", "gmap instance")
one("let seq=0;const PENDING={};", "let seq=0,LASTMAP=null;const PENDING={};", "gmap state")
# the quote sheet lives in the main script; give the layer a way to append to it and to read what came back
one('const labCTA=()=>`<div class="card sx-cta">',
    'SX.labQuotes=()=>LABS;\n'
    'SX.labSheetHook=f=>{const o=labSheet;labSheet=function(){o.apply(this,arguments);try{f()}catch(e){}}};\n'
    'const labCTA=()=>`<div class="card sx-cta">', "lab sheet hook")

HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live34-css">' + (HERE / "live34.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live34.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
