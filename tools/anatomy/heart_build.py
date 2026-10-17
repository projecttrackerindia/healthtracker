# Atlas heart for the Heart Lab, built from Z-Anatomy (CC BY-SA 4.0) heart meshes plus generated structures:
# closed LV wall, thick chamber/vessel walls, anterior mitral leaflet, anterolateral LV papillary muscle,
# mitral chordae, moderator band, conduction system, aortic arch, epicardial fat, Latin names.
import json, re, csv, gzip, base64, struct, math
import numpy as np, trimesh, networkx as nx
from scipy.spatial import cKDTree
rng=np.random.default_rng(7)
H=json.load(open('/home/claude/zexp/heart2.json'))
def TM(k): m=trimesh.Trimesh(np.array(H[k]['v'],float),np.array(H[k]['f']),process=True); m.merge_vertices(digits_vertex=6); return m
def outward(m):
    if len(m.faces) and np.mean(np.einsum('ij,ij->i',m.vertex_normals,m.vertices-m.vertices.mean(0)))<0: m.invert()
    return m
def loops(m):
    e=m.edges_sorted;u,c=np.unique(e,axis=0,return_counts=True);b=u[c==1];G=nx.Graph();G.add_edges_from(b.tolist());out=[]
    for comp in nx.connected_components(G):
        sg=G.subgraph(comp)
        try: cyc=[u for u,v in nx.find_cycle(sg)]
        except Exception: cyc=list(comp)
        if len(cyc)<len(comp)*0.8:  # walk degree-2 path
            cyc=list(nx.dfs_preorder_nodes(sg,source=next(iter(comp))))
        out.append(np.array(cyc))
    return out
def smooth_patch(V,F,fixed,it=20):
    nb=[[] for _ in range(len(V))]
    for a,b,c in F: nb[a]+=[b,c];nb[b]+=[a,c];nb[c]+=[a,b]
    V=V.copy()
    for _ in range(it):
        N=np.array([V[list(set(n))].mean(0) if n else V[i] for i,n in enumerate(nb)])
        V[~fixed]=V[~fixed]*.4+N[~fixed]*.6
    return V
# ---------------- 1. parts ----------------
CH=['Left ventricle','Right ventricle','Left atrium','Right atrium']
ART=['Left coronary artery','Right coronary artery','Circumflex artery of heart','Anterior interventricular artery','Right inferolateral branch of right coronary artery','Septal branches of anterior interventricular artery']
VEIN=['Great cardiac vein','Middle cardiac vein','Inferior vein of left ventricle',"Inferior vein of left ventricle (//Posterior '')",'Coronary sinus']
GV_A=['Ascending aorta','Thoracic aorta','Brachiocephalic trunk','Left common carotid artery','Right common carotid artery','Left subclavian artery','Right subclavian artery']
GV_P=['Pulmonary trunk','Bifurcation of pulmonary trunk','Left pulmonary artery','Right pulmonary artery']
GV_V=['Superior vena cava','Inferior vena cava (thoracic part)','Right superior pulmonary vein','Right inferior pulmonary vein','Left superior pulmonary vein','Left inferior pulmonary vein']
LEAF=[k for k in H if 'leaflet' in k]; PAP=[k for k in H if 'papillary' in k]
M={k:TM(k) for k in CH+ART+VEIN+GV_A+GV_P+GV_V+LEAF+PAP if k in H}
# frame: centre on ventricles
C0=np.vstack([M['Left ventricle'].vertices,M['Right ventricle'].vertices]).mean(0)
UP=np.array([0,0,1.]); FRONT=np.array([0,-1.,0]); LEFT=np.array([1.,0,0])
LVc=M['Left ventricle'].vertices.mean(0); RVc=M['Right ventricle'].vertices.mean(0); LAc=M['Left atrium'].vertices.mean(0); RAc=M['Right atrium'].vertices.mean(0)
# ---------------- 2. close the pre-cut LV window ----------------
lv=M['Left ventricle']; Ls=loops(lv)
big=max(Ls,key=len)
P=lv.vertices[big]; c=P.mean(0)
# local frame of the hole
w,v=np.linalg.eigh(np.cov((P-c).T)); n=v[:,0]; n=n if np.dot(n,c-LVc)>0 else -n; e1=v[:,2]; e2=np.cross(n,e1)
near=lv.vertices[np.linalg.norm(lv.vertices-c,axis=1)<np.linalg.norm(P-c,axis=1).max()*1.6]
uv=np.c_[(near-c)@e1,(near-c)@e2]; h=(near-c)@n
A=np.c_[np.ones(len(uv)),uv,uv**2,uv[:,0]*uv[:,1]]; coef=np.linalg.lstsq(A,h,rcond=None)[0]
K=14; ring=[P]; rv=[];
for k in range(1,K):
    t=k/K; Q=P*(1-t)+c*t; quv=np.c_[(Q-c)@e1,(Q-c)@e2]; qh=np.c_[np.ones(len(quv)),quv,quv**2,quv[:,0]*quv[:,1]]@coef
    Q=c+quv[:,:1]*e1+quv[:,1:]*e2+qh[:,None]*n; ring.append(Q)
cen=c+(coef[0])*n
NV=[];NF=[];base=len(lv.vertices);N=len(big)
idx=[big]
for k in range(1,K): idx.append(base+np.arange(N)+(k-1)*N)
for k in range(1,K): NV.append(ring[k])
cidx=base+(K-1)*N; NV.append(cen[None])
for k in range(K-1):
    a=idx[k];b=idx[k+1]
    for i in range(N):
        j=(i+1)%N; NF+=[[a[i],a[j],b[j]],[a[i],b[j],b[i]]]
a=idx[K-1]
for i in range(N): NF.append([a[i],a[(i+1)%N],cidx])
V2=np.vstack([lv.vertices]+NV); F2=np.vstack([lv.faces,np.array(NF)])
fixed=np.ones(len(V2),bool); fixed[base:]=False
# smooth the patch only
V2=smooth_patch(V2,F2,fixed,12)
lv=trimesh.Trimesh(V2,F2,process=True); lv.fix_normals(); M['Left ventricle']=outward(lv)
def tube(pts,r0,r1,sides=6):
    pts=np.asarray(pts,float); n=len(pts); V=[];F=[]
    T=[]
    for i in range(n):
        t=pts[min(i+1,n-1)]-pts[max(i-1,0)]; t=t/(np.linalg.norm(t)+1e-12) if np.linalg.norm(t)>1e-9 else np.array([0,0,1.]); T.append(t)
    a=np.cross(T[0],[0,0,1.]); a=a if np.linalg.norm(a)>.1 else np.cross(T[0],[1.,0,0]); a/=np.linalg.norm(a)
    for i in range(n):
        if i>0:
            a=a-T[i]*np.dot(a,T[i]); a/=np.linalg.norm(a)+1e-12   # parallel transport
        b=np.cross(T[i],a); r=r0+(r1-r0)*i/max(n-1,1)
        for k in range(sides):
            th=2*math.pi*k/sides; V.append(pts[i]+r*(math.cos(th)*a+math.sin(th)*b))
    for i in range(n-1):
        for k in range(sides):
            a=i*sides+k;b=i*sides+(k+1)%sides;F+=[[a,b,b+sides],[a,b+sides,a+sides]]
    V.append(pts[0]);V.append(pts[-1]);c0=len(V)-2;c1=len(V)-1
    for k in range(sides):
        F.append([c0,(k+1)%sides,k]);F.append([c1,(n-1)*sides+k,(n-1)*sides+(k+1)%sides])
    return np.array(V),np.array(F)
def thicken(m,t,taper=3):
    m=outward(m.copy()); n=m.vertex_normals.copy(); nv=len(m.vertices)
    e=m.edges_sorted;u,c=np.unique(e,axis=0,return_counts=True);bd=u[c==1]
    w=np.ones(nv);
    inner=m.vertices-n*t*w[:,None]
    # relax inner surface to avoid folds
    nb=m.vertex_neighbors
    for _ in range(4): inner=np.array([inner[i]*.5+inner[nb[i]].mean(0)*.5 if nb[i] else inner[i] for i in range(nv)])
    bset=np.zeros(nv,bool); bset[bd.ravel()]=True; inner[bset]=m.vertices[bset]-n[bset]*t
    V=np.vstack([m.vertices,inner]); F=[m.faces,m.faces[:,::-1]+nv]
    if len(bd):
        # orient rim quads consistently with the outer faces
        fe={}
        for f in m.faces:
            for a,b in [(f[0],f[1]),(f[1],f[2]),(f[2],f[0])]: fe[(a,b)]=1
        rim=[]
        for a,b in bd:
            if (a,b) in fe: a,b=b,a
            rim+=[[a,b,b+nv],[a,b+nv,a+nv]]
        F.append(np.array(rim))
    out=trimesh.Trimesh(V,np.vstack(F),process=False)
    side=np.r_[np.zeros(nv,int),np.ones(nv,int)]
    return out,side
MYO={'Left ventricle':(1,.0095,(168,74,70)),'Right ventricle':(2,.0045,(176,84,78)),'Left atrium':(3,.0025,(196,118,104)),'Right atrium':(4,.0022,(200,124,108))}
def classify(m):
    m=m.copy(); c=m.vertices.mean(0)
    bodies=m.split(only_watertight=False)
    big=max(bodies,key=lambda b:len(b.vertices))
    if np.mean(np.einsum('ij,ij->i',big.vertex_normals,big.vertices-c)>0)<.5: m.invert()
    n=m.vertex_normals; o=m.vertices+n*0.0004
    idx=np.arange(len(o)); hit=np.zeros(len(o),bool)
    for s0 in range(0,len(o),4000):
        sl=idx[s0:s0+4000]; loc,ri,_=m.ray.intersects_location(o[sl],n[sl],multiple_hits=False)
        d=np.full(len(sl),9.);
        if len(ri): d[ri]=np.linalg.norm(loc-o[sl][ri],axis=1)
        hit[sl]=d<0.06
    # majority smoothing over the mesh graph
    nb=m.vertex_neighbors
    for _ in range(3): hit=np.array([np.mean(hit[n_]+0.)>.5 if n_ else hit[i] for i,n_ in enumerate(nb)])
    return m,hit.astype(int)
TH={k:classify(M[k]) for k in MYO}
for k in MYO: print(k,'inner fraction',round(TH[k][1].mean(),3))
def inner_of(k):
    m,side=TH[k]; return m.vertices[side==1]
# ---------------- 3. generated mitral apparatus (anatomical proportions) ----------------
lv=M['Left ventricle']; Ls=loops(lv)
mit=min([L for L in Ls if len(L)>20],key=lambda L:np.linalg.norm(lv.vertices[L].mean(0)-LAc))
R=lv.vertices[mit]; mc=R.mean(0)
apex=lv.vertices[np.argmax(np.linalg.norm(lv.vertices-mc,axis=1))]
LAX=np.linalg.norm(apex-mc); AX=(apex-mc)/LAX
E1=np.cross(AX,[0,0,1.]); E1/=np.linalg.norm(E1); E2=np.cross(AX,E1)
ang=np.arctan2((R-mc)@E2,(R-mc)@E1); order=np.argsort(ang); R=R[order]; ang=ang[order]
rA=np.linalg.norm(R-mc,axis=1).mean()
aov=np.vstack([np.array(H[k]['v']) for k in ['Right coronary leaflet','Non-coronary leaflet','Left coronary leaflet']]).mean(0)
th_a=math.atan2((aov-mc)@E2,(aov-mc)@E1)
def wrap(x): return (x+math.pi)%(2*math.pi)-math.pi
half_a=math.radians(62)
from scipy.interpolate import interp1d
NA=96; angs=th_a+math.pi+np.linspace(0,2*math.pi,NA,endpoint=False)   # start opposite the anterior leaflet
rr=np.r_[ang-2*math.pi,ang,ang+2*math.pi]; RR=np.vstack([R,R,R]); fR=interp1d(rr,RR,axis=0)
ring=fR(np.array([wrap(a_) for a_ in angs]))
for _ in range(3): ring=(np.roll(ring,1,0)+ring*2+np.roll(ring,-1,0))/4
dA=np.array([wrap(th-th_a) for th in angs])
def leaflet_len(d):
    if abs(d)<half_a: u=abs(d)/half_a; return .0235*(1-.55*u**3)
    u=(abs(d)-half_a)/(math.pi-half_a); sc=abs(math.sin(u*math.pi*1.5))
    return .0145*(.62+.38*sc)*(1-.45*math.exp(-(u/.12)**2))
rows=12; GRID=np.zeros((rows,NA,3))
for r,t in enumerate(np.linspace(0,1,rows)):
    for i in range(NA):
        a_=ring[i]; Ln=leaflet_len(dA[i]); toC=mc-a_
        p=a_+AX*Ln*t*.92+toC*(.42*t+.08*math.sin(math.pi*t))
        GRID[r,i]=p-AX*.0018*math.sin(math.pi*t)*(1 if abs(dA[i])<half_a else .5)
def leaf_mesh(cols):
    V=[];F=[];n=len(cols)
    for r in range(rows):
        for i in cols: V.append(GRID[r,i])
    for r in range(rows-1):
        for j in range(n-1):
            a_=r*n+j;F+=[[a_,a_+1,a_+n+1],[a_,a_+n+1,a_+n]]
    return trimesh.Trimesh(np.array(V),np.array(F),process=False)
cols_ant=[i for i in range(NA) if abs(dA[i])<=half_a+.07]; cols_post=[i for i in range(NA) if abs(dA[i])>=half_a-.07]
# posterior arc wraps through index 0 -> reorder contiguously
cols_post=sorted(cols_post,key=lambda i:wrap(angs[i]-(th_a+math.pi)))
ant_leaf=leaf_mesh(cols_ant); post_leaf=leaf_mesh(cols_post)
FREE=GRID[-1]; ROUGH=GRID[-3]
comm=[mc+(math.cos(th_a+s_*half_a)*E1+math.sin(th_a+s_*half_a)*E2)*rA for s_ in (1,-1)]
LVin=TH['Left ventricle'][0].vertices[TH['Left ventricle'][1]==1]; tLVin=cKDTree(LVin)
def papillary(cdir):
    d=(cdir-mc)/np.linalg.norm(cdir-mc)
    base=LVin[tLVin.query(mc+AX*LAX*.62+d*rA*1.25)[1]]
    tip=mc+AX*LAX*.36+d*rA*.62
    path=np.array([base+(tip-base)*t+np.cross(AX,d)*.002*math.sin(math.pi*t) for t in np.linspace(0,1,10)])
    v,f=tube(path,.0062,.0034,14); m=trimesh.Trimesh(v,f,process=True)
    heads=[]
    for k in (-1,1):
        hc=tip+np.cross(AX,d)*k*.0022-AX*.0012; hs=trimesh.creation.icosphere(2,radius=1.); hs.vertices=hs.vertices*.0028+hc; heads.append(hs)
    return trimesh.util.concatenate([m]+heads),tip,np.array([h.vertices.mean(0) for h in heads]),cdir
P1=papillary(comm[0]);P2=papillary(comm[1])
score=lambda P:(P[1]@FRONT)+(P[1]@LEFT)*.5
PAPS={'Anterolateral papillary muscle':P1 if score(P1)>=score(P2) else P2,'Posteromedial papillary muscle':P2 if score(P1)>=score(P2) else P1}
def curve(a,b,sag,n=8):
    d=b-a; L_=np.linalg.norm(d); side=np.cross(d,AX); side=side/(np.linalg.norm(side)+1e-9)
    return np.array([a+d*t+side*sag*L_*math.sin(math.pi*t) for t in np.linspace(0,1,n)])
def merge(meshes):
    V=[];F=[];o=0
    for v,f in meshes: V.append(v);F.append(f+o);o+=len(v)
    return trimesh.Trimesh(np.vstack(V),np.vstack(F),process=False)
ch=[]
for nm,(m,tip,heads,cdir) in PAPS.items():
    cd=(cdir-mc)/np.linalg.norm(cdir-mc)
    side_ok=[i for i in range(NA) if np.dot((FREE[i]-mc)/np.linalg.norm(FREE[i]-mc),cd)>-0.05]
    for i in side_ok[::3]:
        h=heads[rng.integers(len(heads))]; p=FREE[i]; mid=h+(p-h)*rng.uniform(.5,.68)
        ch.append(tube(curve(h,mid,.03*rng.uniform(-1,1)),.00045,.00034))
        for k in range(rng.integers(2,4)):
            j=(i+rng.integers(-1,2))%NA; q=(FREE[j] if k else ROUGH[j])+rng.normal(0,.0006,3)
            ch.append(tube(curve(mid,q,.05*rng.uniform(-1,1),6),.00028,.00017))
mit_chordae=merge(ch)
TIP={'al':PAPS['Anterolateral papillary muscle'][1][None],'pm':PAPS['Posteromedial papillary muscle'][1][None]}
# ---------------- 4. moderator band, conduction system ----------------
rv=M['Right ventricle']; la=M['Left atrium']; ra=M['Right atrium']
treeRV=cKDTree(rv.vertices); treeLV=cKDTree(lv.vertices); treeRA=cKDTree(ra.vertices)
LVi=inner_of('Left ventricle');RVi=inner_of('Right ventricle');RAi=inner_of('Right atrium')
LVo=TH['Left ventricle'][0].vertices[TH['Left ventricle'][1]==0];RVo=TH['Right ventricle'][0].vertices[TH['Right ventricle'][1]==0]
sept_rv=RVi[cKDTree(LVi).query(RVi)[0]<0.016]; sept_lv=LVi[cKDTree(RVi).query(LVi)[0]<0.016]
print('septal pts rv',len(sept_rv),'lv',len(sept_lv))
apap=M['Anterior papillary muscle of right ventricle']
apb=apap.vertices[np.argmax((apap.vertices-apap.vertices.mean(0))@(RVc-mc))] if False else apap.vertices[np.argmin(apap.vertices[:,2])]
sh=sept_rv[(sept_rv[:,2]>np.percentile(sept_rv[:,2],25))&(sept_rv[:,2]<np.percentile(sept_rv[:,2],55))]
mb0=sh[np.argmin(np.linalg.norm(sh-apb,axis=1))]
moderator=trimesh.Trimesh(*tube(curve(mb0,apb,.08,10),.0016,.0014,8),process=False)
# conduction landmarks
svc=M['Superior vena cava']; sv_low=svc.vertices[svc.vertices[:,2]<np.percentile(svc.vertices[:,2],10)].mean(0)
SA=ra.vertices[treeRA.query(sv_low+np.array([-.006,0,-.004]))[1]];treeRAi=cKDTree(RAi)
cs=M['Coronary sinus']; tl=M['Septal leaflet of right atrioventricular valve']
cs_end=cs.vertices[np.argmin(np.linalg.norm(cs.vertices-RAc,axis=1))]; tl_top=tl.vertices[np.argmax(tl.vertices[:,2])]
AVp=RAi[treeRAi.query((cs_end+tl_top)/2)[1]]
aov=np.vstack([np.array(H[k]['v']) for k in ['Right coronary leaflet','Non-coronary leaflet','Left coronary leaflet']]).mean(0)
hs=sept_lv[np.argsort(np.linalg.norm(sept_lv-aov,axis=1))[:30]].mean(0); HIS=hs-AX*0.004
def surf_path(a,b,tree,V,inward,n=24,bulge=None):
    pts=[]
    for t in np.linspace(0,1,n):
        p=a+(b-a)*t
        if bulge is not None: p=p+bulge*math.sin(math.pi*t)
        q=V[tree.query(p)[1]]; pts.append(q)
    pts=np.array(pts);
    for _ in range(3): pts[1:-1]=(pts[:-2]+pts[1:-1]*2+pts[2:])/4
    return pts+inward
cond=[];act=[]   # (mesh, activation per vertex)
def add_tube(pts,r0,r1,t0,t1,sides=6):
    v,f=tube(pts,r0,r1,sides); n=len(pts)
    a=np.r_[np.repeat(np.linspace(t0,t1,n),sides),t0,t1]; cond.append((v,f)); act.append(a)
def add_blob(c,r,t):
    s=trimesh.creation.icosphere(2,radius=1.); v=s.vertices*np.array(r)+c; cond.append((v,s.faces)); act.append(np.full(len(v),t))
add_blob(SA,(.0045,.0025,.0025),0.0); add_blob(AVp,(.003,.002,.002),0.18)
ra_in=(RAc-SA); ra_in/=np.linalg.norm(ra_in)
for k,bul in enumerate([np.array([0,-.01,0]),np.array([0,0,0]),np.array([0,.01,0])]):
    add_tube(surf_path(SA,AVp,treeRAi,RAi,ra_in*0.0008,18,bul),.0007,.0006,0.0,0.16)
add_tube(np.array([AVp,(AVp+HIS)/2,HIS]),.0011,.001,0.18,0.3)
# bundle branches down the septum
apexL=apex
def sept_path(a,b,S,tree_side,inward):
    t=cKDTree(S); pts=[]
    for x in np.linspace(0,1,22):
        p=a+(b-a)*x; pts.append(S[t.query(p)[1]])
    pts=np.array(pts)
    for _ in range(4): pts[1:-1]=(pts[:-2]+pts[1:-1]*2+pts[2:])/4
    return pts+inward
lv_in=(LVc-sept_lv.mean(0));lv_in/=np.linalg.norm(lv_in)
rv_in=(RVc-sept_rv.mean(0));rv_in/=np.linalg.norm(rv_in)
rbb=sept_path(HIS,mb0,sept_rv,treeRV,rv_in*.0012); add_tube(rbb,.0009,.0008,0.3,0.42)
add_tube(curve(mb0,apb,.08,10)+rv_in*0.0015,.0008,.0007,0.42,0.5)
lowS=sept_lv[np.argsort(np.linalg.norm(sept_lv-apexL,axis=1))[:40]].mean(0)
lbb=sept_path(HIS,lowS,sept_lv,treeLV,lv_in*.0012); add_tube(lbb,.0011,.0009,0.3,0.44)
add_tube(curve(lbb[6],TIP['al'].mean(0),.1,12),.0008,.0006,0.34,0.5)
add_tube(curve(lbb[8],TIP['pm'].mean(0),-.1,12),.0008,.0006,0.35,0.5)
# Purkinje networks over the ventricle inner walls
def purkinje(starts,Vs,inward_c,thick,t0,count,outer=None):
    tree=cKDTree(Vs)
    if outer is not None: OV,onrm=outer; otree=cKDTree(OV)
    stack=[(s,None,t0,0) for s in starts]; segs=0
    while stack and segs<count:
        p,d,t,dep=stack.pop(0)
        if d is None: d=rng.normal(0,1,3)
        path=[p]
        for k in range(6):
            d=d/np.linalg.norm(d)+rng.normal(0,.35,3); d/=np.linalg.norm(d)
            q=path[-1]+d*0.0032; q=Vs[tree.query(q)[1]]; inw=inward_c-q; inw/=np.linalg.norm(inw)
            q=q+inw*thick
            if outer is not None:
                j=otree.query(q)[1]; dd=np.dot(q-OV[j],onrm[j])
                if dd>-0.0016: q=q-onrm[j]*(dd+0.0016)
            path.append(q)
        path=np.array(path); r=max(.00022,.0006*(.8**dep))
        add_tube(path,r,r*.85,t,t+.05,5); segs+=1
        for b in range(2 if dep<5 else 1):
            if rng.random()<.85: stack.append((path[-1],d+rng.normal(0,.8,3),t+.05,dep+1))
        rng.shuffle(stack) if len(stack)>40 else None
purkinje([lbb[-1],lbb[12],TIP['al'].mean(0),TIP['pm'].mean(0)],LVi,LVc,0.0007,0.5,260,(TH['Left ventricle'][0].vertices[TH['Left ventricle'][1]==0],TH['Left ventricle'][0].vertex_normals[TH['Left ventricle'][1]==0]))
purkinje([apb,rbb[-1]],RVi,RVc,0.0007,0.5,140,(TH['Right ventricle'][0].vertices[TH['Right ventricle'][1]==0],TH['Right ventricle'][0].vertex_normals[TH['Right ventricle'][1]==0]))
conduction=merge(cond); cond_act=np.concatenate(act)
# ---------------- 5. aortic arch ----------------
def end_loop(m,which):
    L=loops(m)
    if not L: return None
    ends=[(m.vertices[l].mean(0),np.linalg.norm(m.vertices[l]-m.vertices[l].mean(0),axis=1).mean(),l) for l in L]
    return ends
asc=M['Ascending aorta'];thr=M['Thoracic aorta']
ea=max(end_loop(asc,0),key=lambda e:e[0][2])     # top of ascending aorta
et=max(end_loop(thr,0),key=lambda e:e[0][2])     # top of descending (thoracic) aorta
br=[min(end_loop(M[k],0),key=lambda e:e[0][2]) for k in ['Brachiocephalic trunk','Left common carotid artery','Left subclavian artery']]
r_arch=(ea[1]+et[1])/2
ea_dir=ea[0]-asc.vertices.mean(0); ea_dir/=np.linalg.norm(ea_dir); et_dir=et[0]-thr.vertices[thr.vertices[:,2]<np.percentile(thr.vertices[:,2],60)].mean(0); et_dir/=np.linalg.norm(et_dir)
bb=np.array([b[0] for b in br]); top=bb.mean(0)-UP*r_arch*0.9
ctrl=[ea[0]-ea_dir*0.004,ea[0]+ea_dir*0.004,(ea[0]+top)/2+UP*0.003,top,(et[0]+top)/2+UP*0.003,et[0]+et_dir*0.004,et[0]-et_dir*0.004]
ctrl=np.array(ctrl)
from scipy.interpolate import CubicSpline
tt=np.r_[0,np.cumsum(np.linalg.norm(np.diff(ctrl,axis=0),axis=1))]; cs_=CubicSpline(tt,ctrl)
cpts=cs_(np.linspace(0,tt[-1],90)); radii=np.linspace(ea[1],et[1],90)*1.0
v,f=tube(cpts,radii[0],radii[-1],28); arch=trimesh.Trimesh(v[:-2],f[[i for i in range(len(f)) if (f[i]<len(v)-2).all()]],process=True)
# ---------------- 6. trim long vessels ----------------
heart_top=max(br,key=lambda e:e[0][2])[0][2]+0.03
apexZ=apex[2]
def trim(m,lo=None,hi=None,xlim=None):
    for (nrm,orig) in ([(np.array([0,0,-1.]),np.array([0,0,hi]))] if hi is not None else [])+([(np.array([0,0,1.]),np.array([0,0,lo]))] if lo is not None else [])+([(np.array([-1.,0,0]),np.array([C0[0]+xlim,0,0])),(np.array([1.,0,0]),np.array([C0[0]-xlim,0,0]))] if xlim else []):
        try: m=trimesh.intersections.slice_mesh_plane(m,nrm,orig,cap=False)
        except Exception as e: pass
    return m
for k in ['Brachiocephalic trunk','Left common carotid artery','Right common carotid artery','Left subclavian artery','Right subclavian artery']: M[k]=trim(M[k],hi=heart_top,xlim=0.065)
M['Thoracic aorta']=trim(M['Thoracic aorta'],lo=apexZ-0.005)
M['Inferior vena cava (thoracic part)']=trim(M['Inferior vena cava (thoracic part)'],lo=apexZ-0.012)
M['Superior vena cava']=trim(M['Superior vena cava'],hi=heart_top)
for k in ['Left pulmonary artery','Right pulmonary artery']+[k for k in GV_V if 'pulmonary vein' in k]: M[k]=trim(M[k],xlim=0.075)
# ---------------- 7. thick walls ----------------
# ---------------- 8. assemble parts ----------------
TA={}
for line in open('/home/claude/zanat/TA2.csv',encoding='utf-8'):
    row=line.strip().strip('"').split(';')
    if len(row)>2 and row[1]: TA.setdefault(row[1].strip().lower(),row[2].strip())
LAT_EXTRA={'left ventricle':'Ventriculus sinister','right ventricle':'Ventriculus dexter','left atrium':'Atrium sinistrum','right atrium':'Atrium dextrum','arch of aorta':'Arcus aortae',
 'anterior leaflet of mitral valve':'Cuspis anterior valvae mitralis','posterior leaflet of mitral valve':'Cuspis posterior valvae mitralis','anterolateral papillary muscle':'Musculus papillaris anterior','posteromedial papillary muscle':'Musculus papillaris posterior',
 'chordae tendineae':'Chordae tendineae','septomarginal trabecula (moderator band)':'Trabecula septomarginalis','sinu-atrial node':'Nodus sinuatrialis','atrioventricular node':'Nodus atrioventricularis',
 'conduction system of heart':'Systema conducente cordis','circumflex artery':'Ramus circumflexus arteriae coronariae sinistrae','anterior interventricular artery (lad)':'Ramus interventricularis anterior',
 'great cardiac vein':'Vena cardiaca magna','middle cardiac vein':'Vena cardiaca media','coronary sinus':'Sinus coronarius','left coronary artery':'Arteria coronaria sinistra','right coronary artery':'Arteria coronaria dextra',
 'superior vena cava':'Vena cava superior','inferior vena cava':'Vena cava inferior','pulmonary trunk':'Truncus pulmonalis','ascending aorta':'Pars ascendens aortae','descending aorta':'Pars descendens aortae',
 'brachiocephalic trunk':'Truncus brachiocephalicus','left common carotid artery':'Arteria carotis communis sinistra','right common carotid artery':'Arteria carotis communis dextra','left subclavian artery':'Arteria subclavia sinistra','right subclavian artery':'Arteria subclavia dextra',
 'left pulmonary artery':'Arteria pulmonalis sinistra','right pulmonary artery':'Arteria pulmonalis dextra','tricuspid valve':'Valva tricuspidalis','pulmonary valve':'Valva trunci pulmonalis','aortic valve':'Valva aortae','mitral valve':'Valva mitralis'}
def latin(name):
    s=name.lower().strip()
    for cand in [s,s.replace('right atrioventricular valve','tricuspid valve'),re.sub(r'^(left|right) ','',s)]:
        if cand in LAT_EXTRA: return LAT_EXTRA[cand]
        if cand in TA: return TA[cand]
    return ''
PARTS=[]
def nice(k):
    k=k.replace("Inferior vein of left ventricle (//Posterior '')",'Posterior vein of left ventricle').replace('Inferior vena cava (thoracic part)','Inferior vena cava').replace('Thoracic aorta','Descending aorta').replace('Circumflex artery of heart','Circumflex artery').replace('Anterior interventricular artery','Anterior interventricular artery (LAD)')
    k=k.replace('right atrioventricular valve','tricuspid valve').replace('left atrioventricular valve','mitral valve').replace('Inferior papillary muscle of left ventricle','Posteromedial papillary muscle')
    return k
def addpart(name,m,kind,col,ch=0,group='',sideflag=None,actv=None,colv=None):
    PARTS.append(dict(name=nice(name),lat=latin(nice(name)),V=np.asarray(m.vertices,float),F=np.asarray(m.faces,int),kind=kind,col=col,ch=ch,group=group,side=sideflag,act=actv,colv=colv))
# epicardial fat bake: distance to coronary vessels (they run in the grooves)
vess_pts=np.vstack([M[k].vertices for k in ART+VEIN if k in M]); vtree=cKDTree(vess_pts)
def fbm(P,f):
    s=0;a=.5
    for o in range(4): s+=a*np.sin(P[:,0]*f*1.7+np.sin(P[:,1]*f*1.3))*np.sin(P[:,1]*f*1.9+np.sin(P[:,2]*f*1.1))*np.sin(P[:,2]*f*1.5+np.sin(P[:,0]*f)); f*=2.1;a*=.5
    return s
for k,(chid,t,col) in MYO.items():
    m,side=TH[k]
    V=m.vertices; d=vtree.query(V)[0]
    fat=np.clip(1-(d-0.0035)/0.009,0,1)*(side==0)
    if chid in (1,2): fat=np.maximum(fat,np.clip(((apex-V)@(-AX)*-1+0.012)/0.012,0,1)*0.55*(side==0))  # apex
    fat*=np.clip(.8+.5*fbm(V,700),0,1)
    base=np.array(col,float); inner=np.array((214,130,120) if chid in (1,2) else (222,160,146),float); fatc=np.array((236,222,190),float)
    mar=fbm(V,500)[:,None]*.5
    C=np.where((side==0)[:,None],base*(1+.08*mar),inner*(1+.05*mar))
    C=C*(1-fat[:,None]*.9)+fatc*fat[:,None]*.9
    addpart(k,m,1,None,chid,'Chambers',side,None,np.clip(C,0,255))
for k in ART:
    if k in M: addpart(k,M[k],8,(196,34,38),0,'Coronary arteries')
for k in VEIN:
    if k in M: addpart(k,M[k],9,(52,82,190),0,'Cardiac veins')
for k in GV_A+GV_P+GV_V:
    if k in M and len(M[k].faces):
        m,side=thicken(M[k],max(.0009,min(.0022,np.ptp(M[k].vertices,0).min()*.08)))
        col=(214,160,138) if k in GV_A else (206,150,138) if k in GV_P else (196,146,140)
        addpart(k,m,4,col,0,'Great vessels',side)
m,side=thicken(arch,.0022); addpart('Arch of aorta',m,4,(214,160,138),0,'Great vessels',side)
for k in LEAF:
    if 'left atrioventricular' in k: continue
    col=(230,232,236); addpart(k,M[k],5,col,0,'Valves')
addpart('Anterior leaflet of mitral valve',ant_leaf,5,(232,234,238),0,'Valves')
addpart('Posterior leaflet of mitral valve',post_leaf,5,(232,234,238),0,'Valves')
for k in PAP:
    if 'left ventricle' in k: continue
    addpart(k,M[k],6,(170,64,62),2,'Papillary muscles')
for nm,P in PAPS.items(): addpart(nm,P[0],6,(170,64,62),1,'Papillary muscles')
addpart('Chordae tendineae',mit_chordae,7,(240,238,232),1,'Valves')
addpart('Septomarginal trabecula (moderator band)',moderator,6,(176,70,66),2,'Papillary muscles')
addpart('Conduction system of heart',conduction,10,(244,214,92),0,'Conduction',None,cond_act)
# ---------------- 9. pack (heart-local cm, x=patient left, y=up, z=anterior) ----------------
SDF_V=np.array([0.9,-0.78,1.68])
def toH(V): return np.c_[(V[:,0]-C0[0]),(V[:,2]-C0[2]),-(V[:,1]-C0[1])]*100+SDF_V
OUTER={chid:cKDTree(TH[k][0].vertices[TH[k][1]==0]) for k,(chid,t,col) in MYO.items()}
def chv(P):
    D=np.stack([OUTER[c].query(P)[0] for c in (1,2,3,4)],1); i=D.argmin(1); return np.where(D.min(1)<0.014,i+1,0)
metas=[];chunks=[];off=0;tot=0
for p in PARTS:
    V=toH(p['V']);F=p['F']
    if len(V)>65535 or len(F)==0: print('skip',p['name'],len(V)); continue
    mn=V.min(0);mx=V.max(0);ext=np.maximum(mx-mn,1e-6)
    q=np.clip(np.round((V-mn)/ext*65535),0,65535).astype(np.uint16)
    if p['colv'] is not None: col=np.clip(p['colv'],0,255).astype(np.uint8)
    else: col=np.tile(np.array(p['col'],np.uint8),(len(V),1))
    side=(p['side'] if p['side'] is not None else np.zeros(len(V))).astype(np.uint8)
    cv=np.full(len(V),p['ch']) if p['ch'] else chv(p['V'])
    if p['kind'] in (4,) : cv=np.zeros(len(V),int)
    side=(side|(cv.astype(np.uint8)<<1)).astype(np.uint8)
    act=(np.clip(p['act'],0,1)*255 if p['act'] is not None else np.zeros(len(V))).astype(np.uint8)
    b=q.tobytes()+F.astype(np.uint16).tobytes()+col.tobytes()+side.tobytes()+act.tobytes()
    if len(b)%4: b+=b'\0'*(4-len(b)%4)
    metas.append({'n':p['name'],'la':p['lat'],'k':p['kind'],'ch':p['ch'],'gr':p['group'],'v':len(V),'i':F.size,'b':[round(float(x),4) for x in list(mn)+list(mx)],'o':off,'c':[round(float(x),3) for x in V.mean(0)]})
    chunks.append(b);off+=len(b);tot+=len(V)
# windows (heart-local): centre on outer surface, outward normal, radius, depth
def win(chamber,dirv,r,depth):
    P=[p for p in PARTS if p['name']==chamber][0]; V=toH(P['V'][P['side']==0]); c=V.mean(0)
    i=np.argmax((V-c)@dirv); s=V[i]; n=(s-c)/np.linalg.norm(s-c)
    return [round(float(x),3) for x in list(s)+list(n)]+[r,depth]
WIN={'RA':win('Right atrium',np.array([-1,0,.35]),1.9,1.4),'RV':win('Right ventricle',np.array([-.25,-.15,1]),2.5,1.6),'LV':win('Left ventricle',np.array([1,-.2,.25]),2.6,2.2),'LA':win('Left atrium',np.array([.25,.1,-1]),1.9,1.4)}
# affine heart-local -> body frame (same per-axis fit as the anatomy blob)
XF=[(3.4817,0.0001),(3.5856,-3.0438),(3.4429,0.0013)]
s=np.array([XF[0][0]/100,XF[1][0]/100,XF[2][0]/100])
o=np.array([XF[0][0]*(C0[0]-SDF_V[0]/100)+XF[0][1], XF[1][0]*(C0[2]-SDF_V[1]/100)+XF[1][1], XF[2][0]*(-C0[1]-SDF_V[2]/100)+XF[2][1]])
meta={'parts':metas,'win':WIN,'toBody':{'s':s.round(6).tolist(),'o':o.round(6).tolist()},'axis':(np.array([AX[0],AX[2],-AX[1]])).round(4).tolist()}
js=json.dumps(meta,separators=(',',':')); pad=(4-(4+len(js))%4)%4; js+=' '*pad
blob=struct.pack('<I',len(js))+js.encode()+b''.join(chunks)
b64=base64.b64encode(gzip.compress(blob,9)).decode()
open('/home/claude/build/heartz.b64','w').write(b64)
print('parts',len(metas),'verts',tot,'MB',round(len(b64)/1e6,2))
# also export generated structures (blender frame) for the anatomy blob
json.dump({'Anterior leaflet of left atrioventricular valve':{'v':ant_leaf.vertices.tolist(),'f':ant_leaf.faces.tolist(),'sys':'cardio'},
           'Posterior leaflet of left atrioventricular valve':{'v':post_leaf.vertices.tolist(),'f':post_leaf.faces.tolist(),'sys':'cardio'},'Anterolateral papillary muscle of left ventricle':{'v':PAPS['Anterolateral papillary muscle'][0].vertices.tolist(),'f':PAPS['Anterolateral papillary muscle'][0].faces.tolist(),'sys':'cardio'},'Posteromedial papillary muscle of left ventricle':{'v':PAPS['Posteromedial papillary muscle'][0].vertices.tolist(),'f':PAPS['Posteromedial papillary muscle'][0].faces.tolist(),'sys':'cardio'},
           'Chordae tendineae of mitral valve':{'v':mit_chordae.vertices.tolist(),'f':mit_chordae.faces.tolist(),'sys':'cardio'},
           'Septomarginal trabecula':{'v':moderator.vertices.tolist(),'f':moderator.faces.tolist(),'sys':'cardio'},
           'Conduction system of heart':{'v':conduction.vertices.tolist(),'f':conduction.faces.tolist(),'sys':'cardio'},
           'Arch of aorta':{'v':arch.vertices.tolist(),'f':arch.faces.tolist(),'sys':'cardio'},
           'Left ventricle':{'v':M['Left ventricle'].vertices.tolist(),'f':M['Left ventricle'].faces.tolist(),'sys':'cardio'}},open('/home/claude/zexp/heart_gen.json','w'))
