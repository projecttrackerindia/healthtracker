import numpy as np, re, json
from dec import *
ab,meta,base,names=female()
FP=meta['parts']
def fget(nm):
    i=[k for k,n in enumerate(names) if n==nm and FP[k].get('l')==2]
    return np.vstack([fpart(ab,meta,base,k)[0] for k in i])
sk,sktri=fpart(ab,meta,base,0)
S=atlas('skeleton'); M=atlas('muscles')
def aget(nm):
    k=[i for i,(n,g) in enumerate(S['parts']) if n==nm]; return S['pos'][np.isin(S['pid'],k)]
def top(P,f=.06):  y=P[:,1]; return P[y>y.max()-f*(y.max()-y.min())]
def bot(P,f=.06):  y=P[:,1]; return P[y<y.min()+f*(y.max()-y.min())]
def hipc(F):
    t=top(F,.1); t=t[np.abs(t[:,0])<=np.median(np.abs(t[:,0]))]; return t.mean(0)
J={}  # name -> (atlas, female)
for s,a,f in [('r','.r','Right '),('l','.l','Left ')]:
    aF,fF=aget('Femur'+a),fget(f+'femur'); aT,fT=aget('Tibia'+a),fget(f+'tibia')
    J['hip'+s]=(hipc(aF),hipc(fF))
    J['knee'+s]=((bot(aF).mean(0)+top(aT).mean(0))/2,(bot(fF).mean(0)+top(fT).mean(0))/2)
    J['ankle'+s]=(bot(aT).mean(0),bot(fT).mean(0))
vmap={'L5':'lumbar vertebra 5','L3':'lumbar vertebra 3','L1':'lumbar vertebra 1','T12':'thoracic vertebra 12','T9':'thoracic vertebra 9','T6':'thoracic vertebra 6','T3':'thoracic vertebra 3','T1':'thoracic vertebra 1','C5':'mammalian cervical vertebra 5','C3':'mammalian cervical vertebra 3'}
for k,v in vmap.items():
    a=aget('Vertebra '+k); f=fget(v)
    J[k]=((a.min(0)+a.max(0))/2,(f.min(0)+f.max(0))/2)
J['pelv']=((J['hipr'][0]+J['hipl'][0])/2,(J['hipr'][1]+J['hipl'][1])/2)
# head top
J['head']=(np.array([0,S['pos'][:,1].max(),J['C3'][0][2]]),np.array([0,sk[:,1].max(),J['C3'][1][2]]))
# ---- arms: atlas joints from bones; female from skin using atlas proportions
names_m=[n for n,g in M['parts']]
for s,a,sg in [('r','.r',-1),('l','.l',1)]:
    aH=aget('Humerus'+a); aR=aget('Radius'+a); aU=aget('Ulna'+a)
    sh=top(aH,.08).mean(0); el=(bot(aH).mean(0)); wr=(bot(aR).mean(0)+bot(aU).mean(0))/2
    hk=[i for i,n in enumerate(names_m) if n.endswith(a) and re.search(r'of hand|interossei muscles of hand|Palmar|pollicis brevis|digiti minimi of hand|Lumbrical muscles of hand',n)]
    hand=M['pos'][np.isin(M['pid'],hk)]; tip=hand[hand[:,1].argmin()]
    # female shoulder: scale atlas shoulder offset from T1 by torso ratio
    ar=J['T1'][0]; fr=J['T1'][1]
    sc=np.linalg.norm(J['T1'][1]-J['L5'][1])/np.linalg.norm(J['T1'][0]-J['L5'][0])
    # arm skin points on this side
    side=sk[sk[:,0]*sg>0]
    fsh=fr+(sh-ar)*sc
    # widen shoulder x to female skin: ratio of skin half-width at shoulder level vs atlas deltoid outer
    dk=[i for i,n in enumerate(names_m) if n.endswith(a) and 'deltoid' in n.lower()]
    dl=M['pos'][np.isin(M['pid'],dk)]
    tipF=side[side[:,1]<fsh[1]][np.argmax(np.abs(side[side[:,1]<fsh[1]][:,0]))]
    # fingertip: farthest skin point from shoulder among outer points below shoulder & |x| > 1.2
    cand=side[(np.abs(side[:,0])>1.0)]
    tipF=cand[np.argmax(np.linalg.norm(cand-fsh,axis=1))]
    L=np.linalg.norm(tip-sh); Lf=np.linalg.norm(tipF-fsh); d=(tipF-fsh)/Lf
    fel=fsh+d*Lf*np.linalg.norm(el-sh)/L; fwr=fsh+d*Lf*(np.linalg.norm(el-sh)+np.linalg.norm(wr-el))/L
    J['sh'+s]=(sh,fsh); J['el'+s]=(el,fel); J['wr'+s]=(wr,fwr); J['tip'+s]=(tip,tipF)
    toe=lambda P:P[P[:,2].argmax()]
for s,sg in [('r',-1),('l',1)]:
    aa=M['pos'][(M['pos'][:,1]<0.06)&(M['pos'][:,0]*sg>0)]; ff=sk[(sk[:,1]<-2.85)&(sk[:,0]*sg>0)]
    J['toe'+s]=(aa[aa[:,2].argmax()],ff[ff[:,2].argmax()])
for k,(a,f) in J.items(): print(k,a.round(3),f.round(3))
np.save('J.npy',{k:(a,f) for k,(a,f) in J.items()},allow_pickle=True)
