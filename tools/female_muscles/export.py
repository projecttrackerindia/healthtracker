import numpy as np, json, re, sys
from dec import *
M=atlas('muscles'); names=[n for n,g in M['parts']]
skip=re.compile(r'fascia|septum|bursa|retinacul|aponeurosis|tract|ligament|linea alba|tendinous arch|sheath',re.I)
keep=np.array([not skip.search(n) for n in names])
tend=np.array([bool(re.search(r'tendon|tendinous|calcaneal',n,re.I)) for n in names])
def dump(pos,fn):
    pid=M['pid']; tri=M['idx'].reshape(-1,3)
    ok=keep[pid[tri]].all(1); tri=tri[ok]
    col=np.where(tend[pid][:,None],[0.86,0.82,0.74],[0.62,0.20,0.17]).astype(np.float32)
    # vary per part slightly
    h=(np.array([hash(n)%1000 for n in names])/1000.)[pid]
    col=col*(0.88+0.2*h[:,None])
    hdr=np.array([len(pos),len(tri)*3],np.uint32)
    open(fn,'wb').write(hdr.tobytes()+pos.astype(np.float32).tobytes()+col.astype(np.float32).tobytes()+tri.astype(np.uint32).tobytes())
dump(np.load('Mf.npy'),'mf.bin')
dump(M['pos'],'mm.bin')
ab,meta,base,nm=female()
# female: skin + skeleton(l2) + organs(l3) in one file with layer tag
P=[];C=[];T=[];off=0
for k,p in enumerate(meta['parts']):
    l=p.get('l')
    if l not in (0,2,3): continue
    v,t=fpart(ab,meta,base,k)
    c={0:[.93,.86,.82],2:[.92,.89,.82],3:[.80,.45,.42]}[l]
    P.append(v);C.append(np.tile(c+[l],(len(v),1)));T.append(t.astype(np.uint32)+off);off+=len(v)
P=np.vstack(P);C=np.vstack(C).astype(np.float32);T=np.vstack(T)
open('fb.bin','wb').write(np.array([len(P),T.size],np.uint32).tobytes()+P.astype(np.float32).tobytes()+C.tobytes()+T.tobytes())
print(len(P))
