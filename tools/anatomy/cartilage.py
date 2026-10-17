# Generate articular cartilage caps (not present in Z-Anatomy/BodyParts3D) from joint proximity.
import json, numpy as np, trimesh
from scipy.spatial import cKDTree
meta=json.load(open('/home/claude/zexp/bone.json')); z=np.load('/home/claude/zexp/bone.npz')
IDX={m['n']:i for i,m in enumerate(meta)}
def mesh(n):
    i=IDX[n]; m=trimesh.Trimesh(z[f'v{i}'].astype(np.float64),z[f'f{i}'],process=True); m.merge_vertices(digits_vertex=5)
    if np.mean(np.einsum('ij,ij->i',m.vertex_normals,m.vertices-m.vertices.mean(0)))<0: m.invert()
    return m
# (bone, partner, reach mm, label)
J=[('Humerus','Scapula',26,'head of humerus (shoulder)'),('Scapula','Humerus',9,'glenoid cavity (shoulder)'),
   ('Humerus','Ulna',14,'trochlea of humerus (elbow)'),('Humerus','Radius',14,'capitulum of humerus (elbow)'),('Ulna','Humerus',9,'trochlear notch of ulna (elbow)'),('Radius','Humerus',12,'head of radius (elbow)'),
   ('Radius','Scaphoid bone',8,'distal radius (wrist)'),('Radius','Lunate bone',8,'distal radius (wrist)'),
   ('Femur','Hip bone',30,'head of femur (hip)'),('Hip bone','Femur',12,'acetabulum (hip)'),
   ('Femur','Tibia',22,'condyles of femur (knee)'),('Femur','Patella',18,'patellar surface of femur (knee)'),('Tibia','Femur',12,'tibial plateau (knee)'),('Patella','Femur',10,'patella (knee)'),
   ('Talus','Tibia',12,'trochlea of talus (ankle)'),('Tibia','Talus',8,'distal tibia (ankle)')]
def cap(A,B,reach,t=0.0022):
    dist,_=cKDTree(B.vertices).query(A.vertices); n=A.vertex_normals
    near=B.vertices[cKDTree(B.vertices).query(A.vertices)[1]]
    toward=np.einsum('ij,ij->i',n,near-A.vertices)/np.maximum(dist,1e-9)
    sel=(dist<reach/1000)&((toward>0.15)|(dist<0.003))
    # clean up: two passes of majority smoothing over the vertex graph
    nb=A.vertex_neighbors
    for _ in range(2):
        s2=sel.copy()
        for i,ns in enumerate(nb):
            if ns: f=np.mean(sel[ns]); s2[i]=f>0.5 if sel[i] else f>0.6
        sel=s2
    fsel=sel[A.faces].all(1)
    if fsel.sum()<20: return None
    sub=A.submesh([np.where(fsel)[0]],append=True); sub.merge_vertices()
    # keep the largest connected patch(es) > 15% of the biggest
    parts=sub.split(only_watertight=False); parts=sorted(parts,key=lambda m:-len(m.faces)); parts=[p for p in parts if len(p.faces)>=.15*len(parts[0].faces)]
    sub=trimesh.util.concatenate(parts)
    # thickness tapers to zero at the rim
    bd=np.zeros(len(sub.vertices),bool); e=sub.edges_sorted; u,c=np.unique(e,axis=0,return_counts=True); bd[u[c==1].ravel()]=True
    vn=sub.vertex_normals.copy(); g=sub.vertex_neighbors; w=np.where(bd,0.0,1.0)
    for _ in range(3): w=np.array([min(w[i],0.5+0.5*np.mean(w[ns])) if ns else w[i] for i,ns in enumerate(g)])
    sub.vertices=sub.vertices+vn*(t*w+0.0004)[:,None]
    v0=sub.vertices.copy();trimesh.smoothing.filter_laplacian(sub,lamb=0.4,iterations=3,implicit_time_integration=False,volume_constraint=False)
    if not np.isfinite(sub.vertices).all() or np.abs(sub.vertices-v0).max()>0.01: sub.vertices=v0
    return sub
out=[]
for side in ['.r','.l']:
    for a,b,reach,label in J:
        if a+side not in IDX or b+side not in IDX: print('missing',a,b); continue
        c=cap(mesh(a+side),mesh(b+side),reach)
        if c is None: print('none',a,b); continue
        out.append({'n':('Right ' if side=='.r' else 'Left ')+'articular cartilage of '+label,'v':c.vertices.tolist(),'f':c.faces.tolist()})
        print(out[-1]['n'],len(c.vertices))
json.dump(out,open('/home/claude/zexp/cartilage.json','w'))
