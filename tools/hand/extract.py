import json,base64,gzip,struct,numpy as np,sys
sys.path.insert(0,'/home/claude/build')
b=gzip.decompress(base64.b64decode(open('/home/claude/build/mdz.b64').read()))
jl=struct.unpack('<I',b[:4])[0]; meta=json.loads(b[4:4+jl]); base=4+jl; names=json.load(open('/home/claude/build/nmz.json'))
out=[]
for i,p in enumerate(meta['parts']):
    bb=np.array(p['b']); 
    c=(bb[:3]+bb[3:])/2
    # right hand/forearm region (x<0): wrist and below, include forearm lower part
    if c[0]<-0.55 and c[1]<0.55 and bb[1]<0.3 and p['v']>0:
        q=np.frombuffer(b,np.uint16,p['v']*3,base+p['o']).reshape(-1,3).astype(np.float64)/65535
        pos=bb[:3]+q*(bb[3:]-bb[:3])
        ix=np.frombuffer(b,np.uint16,p['i'],base+p['o']+p['v']*6).astype(int)
        out.append(dict(n=names[i],l=p.get('l'),v=np.round(pos,5).tolist(),f=ix.tolist()))
print(len(out),sum(len(o['v']) for o in out))
from collections import Counter
print(Counter(o['l'] for o in out))
json.dump(out,open('hand_parts.json','w'))
# female skin hand
from oldmodel import load
m,parts=load('mdlf','nmf'); sk=parts[0]
json.dump(dict(v=np.round(sk['pos'],5).tolist(),f=sk['idx'].astype(int).tolist()),open('fskin.json','w'))
