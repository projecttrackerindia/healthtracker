import json,re,numpy as np
from scipy.spatial import cKDTree
orig=open('/home/claude/work/orig.html').read()
J=json.loads(re.search(r'<script id="fwarp" type="application/json">(.*?)</script>',orig,re.S).group(1))
M=np.load('mskin_v.npy'); sk=json.load(open('fskin.json')); V=np.array(sk['v'])
def umeyama(X,Y,scale=True):
    mx,my=X.mean(0),Y.mean(0); Xc,Yc=X-mx,Y-my
    C=Yc.T@Xc/len(X); U,S,Vt=np.linalg.svd(C); D=np.eye(3)
    if np.linalg.det(U)*np.linalg.det(Vt)<0: D[2,2]=-1
    R=U@D@Vt; s=(S*np.diag(D)).sum()/ (Xc**2).sum()*len(X) if scale else 1.0
    s=(S*np.diag(D)).sum()/((Xc**2).sum()/len(X)) if scale else 1.0
    t=my-s*R@mx; return s,R,t
res={}
for side,sd in (('1',1),('-1',-1)):
    A=J['A'][side]; jm=np.array(A['jm']);dm=np.array(A['dm']);jf=np.array(A['jf']);df=np.array(A['df'])
    # mirror male (stored for x<0 right hand) when side=='1' (x>0)
    Msrc=M.copy()
    if sd==1: Msrc[:,0]*=-1   # male is symmetric enough; use x<0 hand mirrored for left side
    # male hand points: those on x*sd>0.7 with t>wrist
    mm=Msrc[(Msrc[:,0]*sd>.7)]
    tm=(mm-jm)@dm; mm=mm[tm>1.80]
    # female hand points
    Fm=V[(V[:,0]*sd>1.0)]
    tf=(Fm-jf)@df; dd=np.linalg.norm((Fm-jf)-np.outer(tf,df),axis=1); Fm=Fm[(tf>1.80)&(dd<.5)&(tf<2.6)]
    print(side,'male pts',len(mm),'female pts',len(Fm))
    # init: centroid + current arm rotation R, scale 1.05
    R0=np.array(A['R'])
    best=None
    for s0 in (1.0,1.1):
        for Rinit in (R0,np.eye(3)):
            s,R,t=s0,Rinit.copy(),None
            t=Fm.mean(0)-s*R@mm.mean(0)
            kt=cKDTree(Fm)
            for it in range(80):
                Y=(s*(R@mm.T)).T+t
                d,i=kt.query(Y)
                keep=d<np.percentile(d,80)
                s,R,t=umeyama(mm[keep],Fm[i[keep]],True)
            Y=(s*(R@mm.T)).T+t; d1=kt.query(Y)[0]; d2=cKDTree(Y).query(Fm)[0]
            err=np.sqrt((d1**2).mean())+np.sqrt((d2**2).mean())
            if best is None or err<best[0]: best=(err,s,R,t)
    err,s,R,t=best
    print(' best err',round(err,4),'scale',round(s,3))
    res[side]=dict(s=float(s),R=R.tolist(),t=t.tolist(),Wm_mean=mm.mean(0).tolist())
json.dump(res,open('icp_pose.json','w'))
