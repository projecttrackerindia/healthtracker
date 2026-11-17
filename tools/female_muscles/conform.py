import numpy as np, sys
from scipy.spatial import cKDTree
from dec import *
INSET=float(sys.argv[1]) if len(sys.argv)>1 else 0.045
R=float(sys.argv[2]) if len(sys.argv)>2 else 0.16
ab,meta,base,names=female(); sk,tri=fpart(ab,meta,base,0); tri=tri.astype(np.int64)
# skin normals
n=np.zeros_like(sk); fn=np.cross(sk[tri[:,1]]-sk[tri[:,0]],sk[tri[:,2]]-sk[tri[:,0]])
for k in range(3): np.add.at(n,tri[:,k],fn)
n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12
# outward check: normals should point away from body axis on average
if ((sk-sk.mean(0))*n).sum()<0: n=-n
# exclude breast mound: in chest band, points in front of the midline skin
mid=sk[np.abs(sk[:,0])<0.06]
def zmid(y):
    m=mid[np.abs(mid[:,1]-y)<0.05]; return m[:,2].max() if len(m) else 9
ok=np.ones(len(sk),bool)
for i,(x,y,z) in enumerate(sk):
    if 0.85<y<1.85 and 0.08<abs(x)<0.8 and (z>zmid(y)+0.02 or n[i,2]>0.35): ok[i]=False
    if y>2.2: ok[i]=False
S=sk[ok]; N=n[ok]; T=S-INSET*N
J=np.load('J.npy',allow_pickle=True).item()
segs={'arm':[('sh','el'),('el','wr'),('wr','tip')],'leg':[('hip','knee'),('knee','ankle'),('ankle','toe')]}
def segd(X,a,b):
    d=b-a; t=np.clip(((X-a)@d)/(d@d),0,1); return np.linalg.norm(X-(a+t[:,None]*d),axis=1)
tr_=[('pelv','L5'),('L5','L3'),('L3','L1'),('L1','T12'),('T12','T9'),('T9','T6'),('T6','T3'),('T3','T1'),('T1','C5'),('C5','C3'),('C3','head'),('pelv','hipr'),('pelv','hipl')]
dt=np.min([segd(S,J[a][1],J[b][1]) for a,b in tr_],0)
da=np.min([segd(S,J[a+s][1],J[b+s][1]) for a,b in segs['arm'] for s in 'rl'],0)
dl=np.min([segd(S,J[a+s][1],J[b+s][1]) for a,b in segs['leg'] for s in 'rl'],0)
SR=np.array(['trunk','arm','leg'])[np.argmin(np.stack([dt,da*1.0,dl]),0)]
Gv=np.load('Gv.npy'); Gv=np.where(Gv=='gird','trunk',Gv)
X=np.load('Mf.npy').astype(np.float64)
for it in range(6):
    dd=[];jj=[];idx_all=[]
    for g in ('trunk','arm','leg'):
        mi=np.where(Gv==g)[0]; si=np.where(SR==g)[0]
        d,j=cKDTree(X[mi]).query(S[si]); k=d<0.35
        idx_all.append((si[k],mi[j[k]]))
    si=np.concatenate([a for a,b in idx_all]); mj=np.concatenate([b for a,b in idx_all])
    yy=S[si][:,1]; zz=S[si][:,2]
    ins=np.where(SR[si]=='arm',INSET*1.7,INSET)
    ins=np.where((yy>-1.1)&(yy<0.45)&(SR[si]!='arm'),INSET*1.7,ins)      # hips, buttocks, upper thighs carry more fat
    ins=np.where((yy>0.0)&(yy<0.95)&(zz>0.15),INSET*1.7,ins)             # lower belly
    ins=ins[:,None]
    disp=(S[si]-ins*N[si])-X[mj]; anc=X[mj]
    from scipy.ndimage import gaussian_filter, map_coordinates
    h=0.03; lo=X.min(0)-0.5; shp=tuple(((X.max(0)+0.5-lo)/h).astype(int)+1)
    gi=np.round((anc-lo)/h).astype(int)
    acc=np.zeros((4,)+shp,np.float32)
    for k in range(3): np.add.at(acc[k],tuple(gi.T),disp[:,k])
    np.add.at(acc[3],tuple(gi.T),1)
    sg=R/2/h
    for k in range(4): acc[k]=gaussian_filter(acc[k],sg,truncate=3)
    co=((X-lo)/h).T
    Wt=map_coordinates(acc[3],co,order=1)
    D=np.stack([map_coordinates(acc[k],co,order=1) for k in range(3)],1)/np.maximum(Wt,1e-9)[:,None]
    pk=gaussian_filter(np.ones(shp,np.float32)*0,1)  # noop
    D*=np.clip(Wt/(0.3*Wt.max()/ (Wt.max() if Wt.max()>0 else 1)+1e-9),0,1)[:,None]*0+np.clip(Wt/np.percentile(Wt[Wt>0],20),0,1)[:,None]
    L=np.linalg.norm(D,axis=1,keepdims=True); D*=np.minimum(1,0.08/np.maximum(L,1e-9))
    X+=D*0.8
    print(it, np.percentile(np.linalg.norm(D,axis=1),[50,95,99]).round(3))
np.save('Mf.npy',X.astype(np.float32))
