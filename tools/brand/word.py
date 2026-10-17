# Outline text to SVG path data (no font needed by viewers). Inter Display is SIL OFL 1.1: outlines may be used in a logo.
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
F={}
def font(w):
    if w not in F: F[w]=TTFont(f'/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf')
    return F[w]
def run(parts,size=100,track=-0.02):
    """parts: [(text,weight)] -> (path_d, width, ascent) in px at given font size; baseline at y=0"""
    d=[];x=0
    for text,w in parts:
        f=font(w);gs=f.getGlyphSet();cmap=f.getBestCmap();upm=f['head'].unitsPerEm;sc=size/upm
        hm=f['hmtx']
        for ch in text:
            g=cmap[ord(ch)];pen=SVGPathPen(gs)
            tp=TransformPen(pen,(sc,0,0,-sc,x,0));gs[g].draw(tp);d.append(pen.getCommands())
            x+=hm[g][0]*sc+track*size
    return ' '.join(d),x-track*size
