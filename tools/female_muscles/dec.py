import gzip,json,struct,numpy as np
A='/home/claude/healthtracker/web/a/'
def gunz(p):
    b=open(p,'rb').read()
    return gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b
def atlas(sys):
    meta=json.load(open(A+'anat-parts.3be04e70.json'))[sys]
    import os;fn=[f for f in os.listdir(A) if f.startswith('anat-'+sys+'.') and f.endswith('.bin')][0]
    ab=gunz(A+fn); nv,ni=struct.unpack_from('<II',ab,4); lo=np.frombuffer(ab,'<f4',3,16); hi=np.frombuffer(ab,'<f4',3,28)
    o=40; q=np.frombuffer(ab,'<u2',nv*3,o).reshape(-1,3); o+=nv*6
    n8=np.frombuffer(ab,'i1',nv*3,o).reshape(-1,3); o+=nv*3
    idx=np.frombuffer(ab,'<u4',ni,o); o+=ni*4
    pid=np.frombuffer(ab,'<u2',nv,o)
    pos=lo+q/65535*(hi-lo)
    return dict(pos=pos,n=n8,idx=idx,pid=pid,parts=meta['parts'],lo=lo,hi=hi,head=ab[:40])
def female():
    ab=gunz(A+'female.ab5cf751.bin'); jl=struct.unpack_from('<I',ab,0)[0]
    meta=json.loads(ab[4:4+jl]); base=4+jl
    names=json.load(open(A+'names-f.a07a3541.json'))
    return ab,meta,base,names
def fpart(ab,meta,base,i):
    p=meta['parts'][i]; b=p['b']; v=p['v']
    q=np.frombuffer(ab,'<u2',v*3,base+p['o']).reshape(-1,3).astype(np.float64)
    lo=np.array(b[:3]);hi=np.array(b[3:])
    return lo+q/65535*(hi-lo), np.frombuffer(ab,'<u2',p['i'],base+p['o']+v*6).reshape(-1,3)
