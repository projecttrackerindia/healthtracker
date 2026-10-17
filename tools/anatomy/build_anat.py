# Build the DoKKo anatomy blob from Z-Anatomy exports (CC BY-SA 4.0, derived from BodyParts3D).
import json, re, gzip, base64, struct, hashlib, sys
import numpy as np, fast_simplification as fs, trimesh
from scipy.spatial import cKDTree
from oldmodel import load

BUDGET = {'bone':460000,'joint':60000,'muscle':720000,'cardio':430000,'nerve':520000,'visc':170000,'lymph':60000}
FAC=1.0
if len(sys.argv)>1: FAC=float(sys.argv[1]); BUDGET={k:int(v*FAC) for k,v in BUDGET.items()}
SUF=sys.argv[2] if len(sys.argv)>2 else ''
XF = [(3.4817,0.0001),(3.5856,-3.0438),(3.4429,0.0013)]   # per-axis fit to the existing model frame
EXCL = re.compile(r'^(pleura|spinal dura|mucosa of stomach|mucosa of nasal cavity)$|segment of liver|^\(|fascia|intermuscular septum|subcutaneous|bursa|omentum|mesocolon|meso-appendix', re.I)

def nice(n):
    side=''
    if n.endswith('.r'): side='Right '; n=n[:-2]
    elif n.endswith('.l'): side='Left '; n=n[:-2]
    n=re.sub(r'[()*]','',n).strip()
    n=re.sub(r'\s+',' ',n)
    if side: n=side+n[0].lower()+n[1:] if not re.match(r'^[A-Z]{2}',n) else side+n
    return n
H=lambda s:int(hashlib.md5(s.encode()).hexdigest()[:6],16)/0xffffff
def lerp(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def hx(t): return (t[0]<<16)|(t[1]<<8)|t[2]
def col_layer(sysk, n, mc):
    s=n.lower(); grey = mc is None or (abs(mc[0]-.8)<.02 and abs(mc[1]-.8)<.02)
    if sysk=='bone':
        if re.search(r'incisor|canine|molar|premolar|tooth',s): return 2,0xf3eee4
        if 'cartilage' in s: return 2,0xcfdce2
        return 2,hx(lerp((214,198,164),(226,212,180),H(n)))
    if sysk=='joint':
        if re.search(r'pulposus',s): return 2,0xe6dcae
        if re.search(r'fibrosus|disc|menisc|labrum|cartilage',s): return 2,0xdfe2df
        return 2,hx(lerp((228,230,228),(240,240,236),H(n)))
    if sysk=='muscle':
        if re.search(r'fascia|aponeuros|septum|retinacul|tendon|sheath|bursa|galea|tract|ligament',s): return 1,hx(lerp((226,214,200),(236,226,214),H(n)))
        return 1,None
    if sysk=='cardio':
        if re.search(r'leaflet|cusp|valve|chordae',s): return 3,0xead2c6
        if re.search(r'atrium|ventricle|papillary|auricle|trabecul|interventricular|interatrial|heart|myocard|pericard',s) and 'branch' not in s and 'artery' not in s and 'vein' not in s: return 3,hx(lerp((170,36,44),(190,52,56),H(n)))
        if re.search(r'lymph|thoracic duct|cisterna',s): return 4,0x7fb58a
        if mc and mc[2]>mc[0]+.2 or re.search(r'\bvein|venous|sinus|vena\b',s): return 4,hx(lerp((52,96,176),(70,112,196),H(n)))
        return 4,hx(lerp((186,46,42),(204,62,52),H(n)))
    if sysk=='nerve':
        if re.search(r'eyeball|\blens\b|cornea|retina|iris|sclera|vitreous|ciliary body|cochlea|tympan|vestibul|semicircular|malleus|incus|stapes|lacrimal|conjunctiv|auricle|external acoustic|labyrinth|segment of eyeball|suspensory ligament of eyeball|eyelid|tarsus',s): return 3,0xeadcd2
        if re.search(r'sulcus|fissure',s): return 5,0xb98884
        if re.search(r'white matter|corpus callosum|capsule|fornix|commissure|tract|lemniscus|radiation|fascicul|funicul',s): return 5,0xf0e4d6
        if re.search(r'falx|tentorium|dura|arachnoid|pia mater|mening',s) and 'nerve' not in s and 'branch' not in s: return 5,0xd8c4a6
        if re.search(r'nucleus|thalam|putamen|caudate|pallid|amygdal|hippocamp|claustrum|substantia|horn|grey|gray|olive|red nucleus|colliculus|mammillary|hypothal|pituitary|pineal|tegment|pons|medulla|midbrain|peduncle|vermis|flocculus|cerebell|lobule|tonsil of cerebellum',s) and 'nerve' not in s and 'branch' not in s and 'artery' not in s: return 5,hx(lerp((214,170,160),(228,186,176),H(n)))
        if re.search(r'gyrus|lobe|pole|cuneus|uncus|insula|cortex|operculum|lingula',s) and 'nerve' not in s: return 5,hx(lerp((228,196,188),(238,208,200),H(n)))
        if re.search(r'spinal cord|conus|filum|cauda',s): return 5,0xeedcc0
        return 5,hx(lerp((222,186,70),(236,204,96),H(n)))   # peripheral & cranial nerves, ganglia, roots, plexuses
    if sysk=='lymph':
        if 'spleen' in s: return 3,0x8a3a4a
        if 'thymus' in s: return 3,0xd8b8a0
        return 3,hx(lerp((120,176,128),(140,190,140),H(n)))
    if sysk=='visc':
        for rx,c in [(r'liver',0x8e3b2c),(r'lobe of .*lung|lung',0xd99aa2),(r'bronch|trachea',0xe0cfc0),(r'kidney',0x9c4a36),(r'renal pelvis|ureter|bladder|urethra',0xd6b25a),
                     (r'stomach|duoden|jejun|ileum|colon|appendix|caecum|cecum|rectum|oesoph|esoph|pharyn',0xd98f78),(r'taenia|omentum|mesocolon|meso',0xe8cf9a),
                     (r'gallbladder|bile|hepatic duct|cystic duct',0x5f8a3c),(r'pancrea',0xe0b07a),(r'thyroid|parathyroid|suprarenal|adrenal|hypophysis|pineal',0xd9a54a),
                     (r'parotid|submandibular|sublingual|gland',0xe2b48c),(r'tongue|palate|uvula|gingiva|epiglottis',0xd27a78),
                     (r'testis|epididymis|ductus deferens|seminal|prostate|penis|ejaculatory',0xd9a3a0)]:
            if re.search(rx,s): return 3,c
        if not grey: return 3,hx(tuple(int(min(1,x)*255) for x in mc))
        return 3,0xd9a08a
def group(sysk,l,s):
    if l==1: return 2 if re.search(r'aponeuros|retinacul|tendon|sheath|galea|tract|ligament',s) else 0
    if l==2: return 2
    if l==4: return 12 if re.search(r'\bvein|venous|sinus|vena\b',s) else 11
    if l==5: return 13
    if sysk=='cardio': return 4
    if sysk=='lymph': return 10
    if sysk=='nerve': return None
    for g,rx in [(9,r'thyroid|parathyroid|suprarenal|hypophysis|pineal'),(7,r'kidney|renal pelvis|ureter|bladder|urethra'),(8,r'testis|epididymis|ductus deferens|seminal|prostate|penis|ejaculatory'),
                 (6,r'lung|bronch|trachea|epiglottis|laryn'),(5,r'.')]:
        if re.search(rx,s): return g
def safe_smooth(tm,it):
    b0=tm.bounds.copy(); v0=tm.vertices.copy()
    try: trimesh.smoothing.filter_laplacian(tm,lamb=0.35,iterations=it,implicit_time_integration=False,volume_constraint=False)
    except Exception: tm.vertices=v0; return tm
    ext=(b0[1]-b0[0]).max()
    if np.abs(tm.bounds-b0).max()>0.04*ext or not np.isfinite(tm.vertices).all(): tm.vertices=v0
    return tm
def kind(sysk,l,s):
    if sysk=='bone': return 5 if re.search(r'incisor|canine|molar|premolar|tooth',s) else 2 if 'cartilage' in s else 1
    if sysk=='joint': return 2 if re.search(r'pulposus|cartilage|menisc|labrum|triradiate',s) else 3
    if sysk=='muscle': return 3 if re.search(r'aponeuros|retinacul|tendon|sheath|galea|tract|ligament|septum',s) else 4
    return 0
def xform(v): return np.stack([XF[0][0]*v[:,0]+XF[0][1], XF[1][0]*v[:,2]+XF[1][1], XF[2][0]*(-v[:,1])+XF[2][1]],1)
def extras():
    out=[]
    # auricles from Z-Anatomy's auricular-region surface patches, thickened into cartilage
    E=json.load(open('/home/claude/zexp/ear.json'))
    for sd,nm in [('.r','Right'),('.l','Left')]:
        V=[];F=[];o=0
        for k,e in E.items():
            if k.endswith(sd) and e['f'] and not e['mods']:
                V.append(np.array(e['v']));F.append(np.array(e['f'])+o);o+=len(e['v'])
        m=trimesh.Trimesh(np.vstack(V),np.vstack(F),process=True);m.merge_vertices(digits_vertex=4)
        m.remove_unreferenced_vertices()
        v2,f2=trimesh.remesh.subdivide(m.vertices,m.faces);m=trimesh.Trimesh(v2,f2,process=True);m.merge_vertices();m=safe_smooth(m,2)
        n=m.vertex_normals;c=m.vertices.mean(0);lat=np.array([1.0 if sd=='.l' else -1.0,0,0])
        if np.mean(n@lat)<0: n=-n
        t=0.0026; back=m.vertices-n*t
        e=m.edges_sorted;u,cn=np.unique(e,axis=0,return_counts=True);bd=u[cn==1];nv=len(m.vertices)
        rim=np.vstack([np.c_[bd[:,0],bd[:,1],bd[:,1]+nv],np.c_[bd[:,0],bd[:,1]+nv,bd[:,0]+nv]])
        sh=trimesh.Trimesh(np.vstack([m.vertices,back]),np.vstack([m.faces,m.faces[:,::-1]+nv,rim]),process=True)
        out.append(dict(name=nm+' auricle (external ear cartilage)',l=2,c=0xe8d9cc,g=2,k=2,pos=xform(sh.vertices),idx=sh.faces.astype(np.uint16).reshape(-1),sys='bone'))
    G=json.load(open('/home/claude/zexp/heart_gen.json'))
    HC={'Left ventricle':(3,hx((176,46,48)),4),'Anterior leaflet of left atrioventricular valve':(3,0xead2c6,4),'Posterior leaflet of left atrioventricular valve':(3,0xead2c6,4),
        'Anterolateral papillary muscle of left ventricle':(3,hx((170,56,58)),4),'Posteromedial papillary muscle of left ventricle':(3,hx((170,56,58)),4),'Chordae tendineae of mitral valve':(3,0xf0ece2,4),
        'Septomarginal trabecula':(3,hx((176,62,60)),4),'Conduction system of heart':(3,0xf2d24f,4),'Arch of aorta':(4,hx((196,52,48)),11)}
    for nm,(l,c,g) in HC.items():
        if nm not in G: continue
        v=np.array(G[nm]['v']);f=np.array(G[nm]['f'])
        if len(v)>65000:
            v2,f2=fs.simplify(v.astype(np.float32),f.astype(np.int32),target_reduction=1-60000/len(v)); v,f=v2.astype(np.float64),f2
        if FAC<1 and len(v)>int(60000*FAC)+500:
            v2,f2=fs.simplify(v.astype(np.float32),f.astype(np.int32),target_reduction=1-int(60000*FAC)/len(v)); v,f=v2.astype(np.float64),f2
        out.append(dict(name=nice(nm),l=l,c=c,g=g,k=0,pos=xform(v),idx=f.astype(np.uint16).reshape(-1),sys='cardio'))
    for c in json.load(open('/home/claude/zexp/cartilage.json')):
        v=np.array(c['v']);f=np.array(c['f'])
        out.append(dict(name=c['n'],l=2,c=0xc9d8df,g=2,k=2,pos=xform(v),idx=f.astype(np.uint16).reshape(-1),sys='joint'))
    return out
def build():
    parts=[]; total=0
    for sysk,budget in BUDGET.items():
        meta=json.load(open(f'/home/claude/zexp/{sysk}.json')); z=np.load(f'/home/claude/zexp/{sysk}.npz')
        keep=[i for i,m in enumerate(meta) if not EXCL.search(m['n']) and not (sysk=='cardio' and m['n'] in ('Left ventricle','Posterior leaflet of left atrioventricular valve','Inferior papillary muscle of left ventricle'))]
        src=sum(meta[i]['v'] for i in keep); ratio=min(1.0,budget/src)
        got=0
        for i in keep:
            m=meta[i]; v=z[f'v{i}'].astype(np.float64); f=z[f'f{i}'].astype(np.int64)
            # weld duplicate verts (curves/split normals) before simplifying
            q=np.round(v*2e5).astype(np.int64)
            uq,idx_first,inverse=np.unique(q,axis=0,return_index=True,return_inverse=True)
            v=v[idx_first]; f=inverse.reshape(-1)[f]
            f=f[(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,0]!=f[:,2])]
            if len(f)==0: continue
            if sysk=='bone' and len(v)>60:
                el=np.linalg.norm(v[f[:,0]]-v[f[:,1]],axis=1).mean()
                if el>0.0032 and len(v)<20000:
                    try:
                        tm=trimesh.Trimesh(v,f,process=True); tm.remove_unreferenced_vertices()
                        v2,f2=trimesh.remesh.subdivide(tm.vertices,tm.faces); tm=trimesh.Trimesh(v2,f2,process=True); v2,f2=tm.vertices,tm.faces
                        tm=safe_smooth(trimesh.Trimesh(v2,f2,process=False),2); v,f=np.asarray(tm.vertices),np.asarray(tm.faces)
                    except Exception as e:
                        tm=trimesh.Trimesh(v,f,process=True); v2,f2=trimesh.remesh.subdivide(tm.vertices,tm.faces); tm=safe_smooth(trimesh.Trimesh(v2,f2,process=True),2); v,f=np.asarray(tm.vertices),np.asarray(tm.faces)
            r=ratio
            cap=max(2500,int(60000*FAC))
            if len(v)*r>cap: r=cap/len(v)
            if len(v)>150 and r<0.98:
                try:
                    v2,f2=fs.simplify(v.astype(np.float32),f.astype(np.int32),target_reduction=1-r)
                    if len(f2)>8: v,f=v2.astype(np.float64),f2
                except Exception as e: print('simplify fail',m['n'],e)
            # remove unreferenced
            used=np.unique(f); remap=-np.ones(len(v),np.int64); remap[used]=np.arange(len(used)); v=v[used]; f=remap[f]
            if len(v)>65535: print('too big',m['n'],len(v)); continue
            P=xform(v)
            l,c=col_layer(sysk,m['n'],m['c'])
            g=group(sysk,l,m['n'].lower())
            parts.append(dict(name=nice(m['n']),l=l,c=c,g=g,k=kind(sysk,l,m['n'].lower()),pos=P,idx=f.astype(np.uint16).reshape(-1),sys=('sense' if sysk=='nerve' and l==3 else sysk))); got+=len(v)
        total+=got; print(sysk,'parts',len(keep),'src',src,'->',got,flush=True)
    parts+=extras()
    print('TOTAL verts',total)
    return parts
def bake_ao(allp):
    for l in sorted(set(p['l'] for p in allp)):
        ps=[p for p in allp if p['l']==l]
        P=np.vstack([p['pos'] for p in ps]); tree=cKDTree(P)
        N=[]
        for p in ps:
            tm=trimesh.Trimesh(p['pos'],p['idx'].reshape(-1,3).astype(np.int64),process=False); n=np.asarray(tm.vertex_normals)
            if len(n) and np.mean(np.einsum('ij,ij->i',n,p['pos']-p['pos'].mean(0)))<0: n=-n
            N.append(n)
        N=np.nan_to_num(np.vstack(N)); N[np.linalg.norm(N,axis=1)<.5]=[0,0,1.]; occ=np.zeros(len(P))
        a=np.cross(N,np.where(np.abs(N[:,:1])<.9,np.array([[1.,0,0]]),np.array([[0,1.,0]]))); a/=np.linalg.norm(a,axis=1,keepdims=True)+1e-9; b=np.cross(N,a)
        dirs=[N]+[ (N+0.9*s1*a+0.9*s2*b)/np.linalg.norm(N+0.9*s1*a+0.9*s2*b,axis=1,keepdims=True) for s1,s2 in [(1,0),(-1,0),(0,1),(0,-1)]]
        for r,w in [(0.012,.4),(0.035,.38),(0.08,.22)]:
            for D in dirs:
                d,_=tree.query(P+D*r,workers=-1)
                el=1.0 if D is dirs[0] else 0.72
                occ+=w/len(dirs)*np.clip(1-d/(0.9*r*el),0,1)
        occ=np.clip(occ*1.6,0,1)
        ao=1-occ; ao=np.clip(ao/np.percentile(ao,70),0.18,1.0); o=0
        for p in ps: p['ao']=(ao[o:o+len(p['pos'])]*255).astype(np.uint8); o+=len(p['pos'])
        print('ao layer',l,len(P),round(float(ao.mean()),3),flush=True)
def fdir(P):
    c=P-P.mean(0); w,v=np.linalg.eigh(c.T@c); d=v[:,-1]; return [int(round(x*127)) for x in d]
def pack(parts,old_skin=None):
    bake_ao(list(parts)+(old_skin or []))
    allp=list(parts)+(old_skin or [])
    metas=[];chunks=[];off=0
    for p in allp:
        P=p['pos'];mn=P.min(0);mx=P.max(0);ext=np.maximum(mx-mn,1e-6)
        qv=np.clip(np.round((P-mn)/ext*65535),0,65535).astype(np.uint16)
        b=qv.tobytes()+p['idx'].astype(np.uint16).tobytes()
        if 'ao' in p: b+=p['ao'].tobytes()+(b'\0' if len(P)%2 else b'')
        d={'l':p['l'],'v':len(P),'i':len(p['idx']),'b':[round(float(x),5) for x in list(mn)+list(mn+ext)],'o':off}
        if p.get('c') is not None: d['c']=p['c']
        if 'ao' in p: d['a']=1
        if p.get('k'): d['k']=p['k']
        if p.get('k') in (3,4): d['d']=fdir(P)
        if p.get('g') is not None: d['g']=p['g']
        if p.get('sys') and p['sys']!='skin': d['y']=p['sys']
        metas.append(d);chunks.append(b);off+=len(b)
    js=json.dumps({'parts':metas,'anchors':[[0.0,2.6638,0.3207],[0.0709,2.1209,0.4225],[0.6512,1.3717,0.0299],[0.0,0.7161,0.3968],[0.2904,-1.4307,0.0779]]},separators=(',',':'))
    if (4+len(js))%2: js+=' '
    blob=struct.pack('<I',len(js))+js.encode()+b''.join(chunks)
    names=[p['name'] for p in allp]
    return base64.b64encode(gzip.compress(blob,9)).decode(),json.dumps(names,ensure_ascii=False),[p.get('sys','skin') for p in allp]
if __name__=='__main__':
    parts=build()
    _,old=load('mdlm','nmm')
    skin=[dict(name=o['name'],l=0,c=None,g=o['g'],pos=o['pos'],idx=o['idx'],sys='skin') for o in old if o['l']==0]
    b64,names,sysl=pack(parts,skin)
    open(f'/home/claude/build/mdz{SUF}.b64','w').write(b64); open(f'/home/claude/build/nmz{SUF}.json','w').write(names); json.dump(sysl,open(f'/home/claude/build/sysz{SUF}.json','w'))
    print('blob MB',len(b64)/1e6,'parts',len(sysl))
