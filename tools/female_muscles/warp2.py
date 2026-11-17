import numpy as np
from dec import *
J=np.load('J.npy',allow_pickle=True).item()
ab,meta,base,names=female(); sk,sktri=fpart(ab,meta,base,0)
M=atlas('muscles'); P=M['pos'].astype(np.float64)
B=[]
for s in 'rl':
    B+= [('hip'+s,'knee'+s),('knee'+s,'ankle'+s),('ankle'+s,'toe'+s),('pelv','hip'+s),('T3','sh'+s),('sh'+s,'el'+s),('el'+s,'wr'+s),('wr'+s,'tip'+s)]
B+= [('pelv','L5'),('L5','L3'),('L3','L1'),('L1','T12'),('T12','T9'),('T9','T6'),('T6','T3'),('T3','T1'),('T1','C5'),('C5','C3'),('C3','head')]
SPINE={('pelv','L5'),('L5','L3'),('L3','L1'),('L1','T12'),('T12','T9'),('T9','T6'),('T6','T3'),('T3','T1')}
def segd(X,a,b):
    d=b-a; t=np.clip(((X-a)@d)/(d@d),0,1); return np.linalg.norm(X-(a+t[:,None]*d),axis=1),t
def rot(a,b):
    a=a/np.linalg.norm(a); b=b/np.linalg.norm(b); v=np.cross(a,b); c=a@b
    if np.linalg.norm(v)<1e-9: return np.eye(3)
    K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]); return np.eye(3)+K+K@K/(1+c)
def frame(e):
    e=e/np.linalg.norm(e); ref=np.array([1.,0,0]) if abs(e[0])<.8 else np.array([0,0,1.])
    u=ref-e*(ref@e); u/=np.linalg.norm(u); return e,u,np.cross(e,u)
NB=6
DA=np.stack([segd(P,J[a][0],J[b][0])[0] for a,b in B],1)
DF=np.stack([segd(sk,J[a][1],J[b][1])[0] for a,b in B],1)
ownA=DA.argmin(1); ownF=DF.argmin(1)
import re
names=[n for n,g in M['parts']]
ARM=re.compile(r'deltoid|biceps brachii|triceps|brachialis|coracobrachialis|pronator|flexor carpi|palmaris|flexor digitorum (superficialis|profundus)|superficialis|flexor pollicis|extensor carpi|extensor digitorum\.|^extensor digitorum\.|extensor digiti minimi|extensor indicis|extensor pollicis|abductor pollicis|adductor pollicis|opponens pollicis|of hand|palmar interossei|brachioradialis|anconeus|supinator|teres|infraspinatus|supraspinatus|subscapularis',re.I)
GIRD=re.compile(r'pectoralis major|latissimus|teres (major|minor)|infraspinatus|supraspinatus|subscapularis',re.I)
LEG=re.compile(r'gluteus|femoris|vastus|sartorius|adductor (magnus|longus|brevis|minimus)|gracilis|pectineus|semimembranosus|semitendinosus|tensor fasciae|piriformis|gemellus|obturator|tibialis|fibularis|gastrocnemius|soleus|plantaris|popliteus|hallucis|of foot|extensor digitorum (longus|brevis)|flexor digitorum (longus|brevis)|quadratus plantae|calcaneal|plantar interossei|iliacus|psoas',re.I)
def grp(n):
    if n.startswith('Extensor digitorum.'): return 'arm'
    if GIRD.search(n): return 'gird'
    if ARM.search(n) and not LEG.search(n): return 'arm'
    if LEG.search(n): return 'leg'
    return 'trunk'
G=np.array([grp(n) for n in names]); side=np.array([ 'r' if n.endswith('.r') or n.endswith('.r)') else 'l' if n.endswith('.l') else '' for n in names])
def allowed(g,sd,a,b):
    bs=a[-1] if a[-1] in 'rl' and a not in ('T12','L1') else (b[-1] if b[-1] in 'rl' and b not in('T12','L1') else '')
    if a in('T3',) and b.startswith('sh'): kind='clav'
    elif a.startswith(('sh','el','wr')): kind='arm'
    elif a.startswith(('hip','knee','ankle')): kind='leg'
    elif a=='pelv' and b.startswith('hip'): kind='pelv'
    else: kind='spine'
    if g=='arm': return kind in('arm','clav') and bs==sd
    if g=='gird': return kind in('spine','clav') or (kind=='arm' and bs==sd and a.startswith('sh'))
    if g=='leg': return (kind in('leg','pelv') and (bs==sd or sd=='')) or (kind=='spine' and a=='pelv')
    return kind in('spine','clav','pelv')
MASK=np.zeros((len(names),len(B)),bool)
for i,n in enumerate(names):
    for bi,(a,b) in enumerate(B): MASK[i,bi]=allowed(G[i],side[i],a,b)
print('groups',{g:(G==g).sum() for g in set(G)})
Mv=MASK[M['pid']]
W=np.where(Mv,1/(DA+0.006)**6,0)
gv=G[M['pid']]=='gird'
for bi,(a,b) in enumerate(B):
    if a.startswith('sh'):
        _,t=segd(P,J[a][0],J[b][0]); W[gv,bi]*=np.clip(1-t[gv]/0.2,0,1)**2; W/=W.sum(1,keepdims=True)+1e-30
out=np.zeros_like(P)
info=[]
from scipy.interpolate import PchipInterpolator
SP=['pelv','L5','L3','L1','T12','T9','T6','T3','T1','C5','C3','head']
ya=np.array([J[k][0][1] for k in SP]); yf=np.array([J[k][1][1] for k in SP])
ya=np.r_[0.0,ya]; yf=np.r_[J['pelv'][1][1]-(J['pelv'][0][1])*3.45,yf]
Ymap=PchipInterpolator(ya,yf,extrapolate=True)
za=PchipInterpolator(ya[1:],[J[k][0][2] for k in SP],extrapolate=True); zf=PchipInterpolator(yf[1:],[J[k][1][2] for k in SP],extrapolate=True)
xa=PchipInterpolator(ya[1:],[J[k][0][0] for k in SP],extrapolate=True); xf=PchipInterpolator(yf[1:],[J[k][1][0] for k in SP],extrapolate=True)
K=3.55
def TRUNK(X):
    y=X[:,1]; Y=Ymap(y); yc=np.clip(y,ya[1],ya[-1]); Yc=np.clip(Y,yf[1],yf[-1])
    return np.stack([(X[:,0]-xa(yc))*K+xf(Yc),Y,(X[:,2]-za(yc))*K+zf(Yc)],1)
TR=TRUNK(P)
TBONES={('pelv','L5'),('L5','L3'),('L3','L1'),('L1','T12'),('T12','T9'),('T9','T6'),('T6','T3'),('T3','T1'),('T1','C5'),('C5','C3'),('C3','head'),('pelv','hipr'),('pelv','hipl')}
for bi,(a,b) in enumerate(B):
    a0,a1=J[a][0],J[b][0]; f0,f1=J[a][1],J[b][1]
    e,u,w=frame(a1-a0); R=rot(a1-a0,f1-f0); s=np.linalg.norm(f1-f0)/np.linalg.norm(a1-a0)
    eF,uF,wF=R@e,R@u,R@w
    # per-bin, per-side perpendicular scales from skin
    XA=P[ownA==bi]-a0; XF=sk[ownF==bi]-f0
    tA=(XA@e)/np.linalg.norm(a1-a0); tF=(XF@eF)/np.linalg.norm(f1-f0)
    sc=np.full((NB,4),3.55)  # u+,u-,w+,w-: one perpendicular scale everywhere, so neighbouring bones agree
    nb=0
    for k in range(nb):
        lo,hi=k/nb,(k+1)/nb
        ma=(tA>=lo-.05)&(tA<hi+.05); mf=(tF>=lo-.05)&(tF<hi+.05)
        if ma.sum()<30 or mf.sum()<20: continue
        au,aw=XA[ma]@u,XA[ma]@w; fu,fw=XF[mf]@uF,XF[mf]@wF
        if (a,b) in SPINE:  # front extent from the midline only (keeps chest muscles under, not inside, the breast)
            mid=np.abs(sk[ownF==bi][mf][:,0])<0.12
            if mid.sum()>5:
                front=np.sign((wF)[2]) # +w points to front?
                pass
        r=[]
        for A_,F_ in [(au,fu),(aw,fw)]:
            for sg in (1,-1):
                qa=np.percentile(np.maximum(sg*A_,0),97); qf=np.percentile(np.maximum(sg*F_,0),97)
                r.append(np.clip(0.93*qf/max(qa,1e-4),0.5*s,1.6*s))
        sc[k*NB//nb:(k+1)*NB//nb]=[r[0],r[1],r[2],r[3]]
    # smooth bins
    if nb>1 and False: sc=(np.roll(sc,1,0)+2*sc+np.roll(sc,-1,0))/4*0+sc
    info.append((a,b,round(s,2),sc.mean(0).round(2)))
    X=P-a0; t=X@e; pu=X@u; pw=X@w; tt=np.clip(t/np.linalg.norm(a1-a0),0,.999)
    kk=(tt*NB).astype(int); su=np.where(pu>0,sc[kk,0],sc[kk,1]); sw=np.where(pw>0,sc[kk,2],sc[kk,3])
    Y=f0+np.outer(t*s,eF)+np.outer(pu*su,uF)+np.outer(pw*sw,wF)
    if (a,b) in TBONES: Y=TR
    out+=W[:,bi:bi+1]*Y
for i in info: print(i)
np.save('Mf.npy',out.astype(np.float32)); np.save('Gv.npy',G[M['pid']])
