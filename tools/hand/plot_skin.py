import json,sys,numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
sk=json.load(open('fskin.json')); V=np.array(sk['v']); import os; (V.__setitem__((slice(None),0),-V[:,0]) if os.environ.get('MIR') else None); F=np.array(sk['f']).reshape(-1,3)
P=json.load(open(sys.argv[2]))
def hand_box(V):
    m=(V[:,0]<-1.2)&(V[:,1]<0.15)
    return V[m]
hb=hand_box(V); print('skin hand verts',len(hb),hb.min(0).round(3),hb.max(0).round(3))
cx,cy=(hb[:,0].min()+hb[:,0].max())/2,(hb[:,1].min()+hb[:,1].max())/2
fig,axs=plt.subplots(1,2,figsize=(12,6.5))
for k,(ax,idx) in enumerate(zip(axs,[(0,1),(2,1)])):
    tri=V[F]; keep=(tri[:,:,0].mean(1)<-.9)&(tri[:,:,1].mean(1)<0.4)
    t=tri[keep][:,:,list(idx)]
    ax.add_collection(PolyCollection(list(t),facecolors=(.85,.7,.6,.35),edgecolors=(.5,.3,.2,.25),linewidths=.2))
    for p in P:
        if p['l'] not in (1,2): continue
        v=np.array(p['v']);f=np.array(p['f']).reshape(-1,3)
        tt=v[f][:,:,list(idx)]
        ax.add_collection(PolyCollection(list(tt),facecolors=(.3,.3,.9,.5) if p['l']==1 else (.8,.2,.1,.5),edgecolors='none'))
    if k==0: ax.set_xlim(cx-.7,cx+.7)
    else: ax.set_xlim(-.7,.7)
    ax.set_ylim(cy-.8,cy+.5); ax.set_aspect('equal'); ax.set_title(['front (x,y)','side (z,y)'][k])
plt.tight_layout(); plt.savefig(sys.argv[1],dpi=70)
