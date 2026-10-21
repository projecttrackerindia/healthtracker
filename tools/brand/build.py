import sys,os,json;sys.path.insert(0,'.')
from mark import VIEW_BARE, glyph
from word import run
V={'user':('#2F5BFF','Urban Health','for people & families'),'partner':('#0B8A7C','Partners','doctors · hospitals · pharmacies · labs · insurers'),'admin':('#1C1E26','Admin','internal console')}
OUT='out';os.makedirs(OUT+'/svg',exist_ok=True);os.makedirs(OUT+'/png',exist_ok=True)
def tile(bg,fg='#fff',size=None):
    sz=f' width="{size}" height="{size}"' if size else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"{sz}><rect width="64" height="64" rx="16" fill="{bg}"/>{glyph(fg)}</svg>'
def maskable(bg,fg='#fff'):  # Android adaptive icon: full bleed, glyph inside the 80% safe zone
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="{bg}"/><g transform="translate(32 32) scale(.72) translate(-32 -32)">{glyph(fg)}</g></svg>'
def bare(fg):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEW_BARE}">{glyph(fg)}</svg>'
WD,WW=run([('Urban ','Regular'),('Health','Bold')],44)
def lockup(col,label=None,reverse=False):
    tile_bg,tile_fg,txt=(('#fff',col,'#fff') if reverse else (col,'#fff',col))
    x0=64+16;w=x0+WW
    lab=''
    if label:
        ld,lw=run([(label.lower(),'Medium')],22,0.04)
        lab=f'<rect x="{w+14}" y="20" width="1.6" height="26" fill="{txt}" opacity=".35"/><path transform="translate({w+30} 41)" d="{ld}" fill="{txt}"/>'
        w=w+30+lw
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w+2:.1f} 64"><rect width="64" height="64" rx="16" fill="{tile_bg}"/>{glyph(tile_fg)}<path transform="translate({x0} 46)" d="{WD}" fill="{txt}"/>{lab}</svg>'
def stacked(col):
    s=WW/ (64*2.6)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WW:.1f} 210"><g transform="translate({WW/2-48} 0) scale(1.5)"><rect width="64" height="64" rx="16" fill="{col}"/>{glyph("#fff")}</g><path transform="translate(0 168)" d="{WD}" fill="{col}"/></svg>'
files={}
def put(name,svg): open(f'{OUT}/svg/{name}.svg','w').write(svg);files[name]=svg
for k,(c,label,_) in V.items():
    put(f'{k}-icon',tile(c));put(f'{k}-icon-maskable',maskable(c));put(f'{k}-mark',bare(c))
    lb=None if k=='user' else label
    put(f'{k}-logo',lockup(c,lb));put(f'{k}-logo-white',lockup(c,lb,True))
put('user-logo-stacked',stacked(V['user'][0]))
put('mono-black-logo',lockup('#000000'));put('mono-white-logo',lockup('#000000',None,True).replace('fill="#000000"','fill="#000"'))
put('mono-black-mark',bare('#000'));put('mono-white-mark',bare('#fff'))
json.dump({k:v for k,v in files.items()},open('files.json','w'))
print(len(files),'svgs')
