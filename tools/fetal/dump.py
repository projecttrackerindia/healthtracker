"""Decode the app's own pregnancy models (meshopt-compressed GLBs) in a headless browser and save what
tools/fetal/build.py needs: each week's baby mesh, and the mother model's baby, placenta, cord and sac.

    python -m http.server 8100 --directory web &      # any static server for web/
    python tools/fetal/dump.py                          # writes /tmp/wk/wNN.json
    python tools/fetal/build.py > /tmp/wk/manifest.json # writes web/a/pbr-wNN.<hash>.json
Then put the manifest into RIGS (web/baby.html) and PGR (web/uh.html), and pre-compress the new files.
"""
import json, os, re
from playwright.sync_api import sync_playwright
WEB = os.path.join(os.path.dirname(__file__), '..', '..', 'web'); OUT = '/tmp/wk'; os.makedirs(OUT, exist_ok=True)
PAGE = """<!doctype html><body><script src="/a/three.9274bbce.js"></script><script src="/a/gltfloader.5c15967b.js"></script><script src="/a/meshopt.0de67743.js"></script><script>
window.dump=async(w,B,M)=>{await MeshoptDecoder.ready;const L=new THREE.GLTFLoader();L.setMeshoptDecoder(MeshoptDecoder);const ld=u=>new Promise((r,j)=>L.load('/a/'+u,r,undefined,j));
 const geo=(m)=>{const G=m.geometry,n=G.attributes.position.count,v=new THREE.Vector3(),P=[];for(let i=0;i<n;i++){v.fromBufferAttribute(G.attributes.position,i).applyMatrix4(m.matrixWorld);P.push(v.x,v.y,v.z)}return{P,I:Array.from(G.index.array)}};
 const g=await ld(B);g.scene.updateMatrixWorld(true);let bm;g.scene.traverse(o=>{if(o.isMesh)bm=o});const out={baby:geo(bm)};
 const m=await ld(M);m.scene.updateMatrixWorld(true);for(const nm of ['Baby','Placenta','Umbilical_Cord','Amniotic_Sac_Back']){const o=m.scene.getObjectByName(nm);if(!o)continue;let me;o.traverse(x=>{if(x.isMesh)me=x});if(me)out[nm]=geo(me)}return out};</script>"""
if __name__ == '__main__':
    open(os.path.join(WEB, '_fetal_dump.html'), 'w').write(PAGE)
    D = json.loads(re.search(r'const D=(\{.*?\});', open(os.path.join(WEB, 'baby.html')).read()).group(1))
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader']); pg = b.new_page(); pg.goto('http://localhost:8100/_fetal_dump.html')
            for w in sorted(int(k) for k in D['B']):
                json.dump(pg.evaluate('([w,b,m])=>dump(w,b,m)', [w, D['B'][str(w)], D['M'][str(w)]]), open(f'{OUT}/w{w:02d}.json', 'w')); print(w)
            b.close()
    finally:
        os.remove(os.path.join(WEB, '_fetal_dump.html'))
