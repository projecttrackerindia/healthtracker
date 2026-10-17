import json,sys,numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
def draw(ax,parts,proj,title,lim,ls=(1,2,4,5)):
    cols={1:'#e8dcc0',2:'#c8553a',4:'#4a6fa5',5:'#e0c040'}
    polys=[];cs=[];depth=[]
    for p in parts:
        if p['l'] not in ls: continue
        v=np.array(p['v']);f=np.array(p['f']).reshape(-1,3)
        tri=v[f]; n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); nn=np.linalg.norm(n,axis=1,keepdims=True)+1e-12; n=n/nn
        light=np.array([.3,.4,.85]) if proj==0 else np.array([.85,.3,.4])
        sh=np.clip(np.abs(n@light/np.linalg.norm(light)),0,1)*.75+.25
        base=np.array(matplotlib.colors.to_rgb(cols[p['l']]))
        P=tri[:,:,[0,1]] if proj==0 else tri[:,:,[2,1]]
        d=tri[:,:,2].mean(1) if proj==0 else tri[:,:,0].mean(1)
        polys+=list(P); cs+=list(base[None,:]*sh[:,None]); depth+=list(d)
    o=np.argsort(depth); 
    ax.add_collection(PolyCollection([polys[i] for i in o],facecolors=[cs[i] for i in o],edgecolors='none'))
    ax.set_xlim(*lim[0]);ax.set_ylim(*lim[1]);ax.set_aspect('equal');ax.set_title(title);ax.axis('off')
if __name__=='__main__':
    files=sys.argv[2:]; out=sys.argv[1]
    fig,axs=plt.subplots(2,len(files),figsize=(5.2*len(files),10))
    axs=np.atleast_2d(axs).reshape(2,-1)
    for k,fn in enumerate(files):
        P=json.load(open(fn))
        allv=np.concatenate([np.array(p['v']) for p in P if p['l'] in (1,2,4,5)])
        # center on hand region (y< 0.1)
        h=allv[allv[:,1]<0.15]; cx=(h[:,0].min()+h[:,0].max())/2; cy=(h[:,1].min()+h[:,1].max())/2
        draw(axs[0,k],P,0,fn+' front (x,y)',((cx-.6,cx+.6),(cy-.7,cy+.5)))
        draw(axs[1,k],P,1,fn+' side (z,y)',((-.6,.6),(cy-.7,cy+.5)))
    plt.tight_layout(); plt.savefig(out,dpi=70)
