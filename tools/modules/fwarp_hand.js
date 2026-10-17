function makeFemWarp(J){
 const ss=(a,b,x)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t)};
 const lin=(spec,arr)=>{const[a,b,n]=spec;return x=>{const f=(x-a)/(b-a)*(n-1);if(f<=0)return arr[0];if(f>=n-1)return arr[n-1];const i=Math.floor(f),w=f-i;return arr[i]*(1-w)+arr[i+1]*w}};
 const T={SX:lin(J.TY,J.SX),SZ:lin(J.TY,J.SZ),zbm:lin(J.TY,J.zbm),zbf:lin(J.TY,J.zbf)},LG={},AR={},AA={};
 for(const s of ['1','-1']){const g=J.LEG[s];LG[s]={};for(const k in g)LG[s][k]=lin(J.LY,g[k]);const a=J.ARM[s];AR[s]={};for(const k in a)AR[s][k]=lin(J.AT,a[k]);AA[s]=J.A[s]}
 const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],CM=J.CM;
 const core=function(x,y,z,o,na){const P=[x,y,z],Q=[x,y,z],W={};core.W=W;
  for(const s of ['1','-1']){const A=AA[s],sd=+s,v=[x-A.jm[0],y-A.jm[1],z-A.jm[2]],t=dot(v,A.dm),pp=[v[0]-t*A.dm[0],v[1]-t*A.dm[1],v[2]-t*A.dm[2]],d=Math.hypot(...pp),r=t/A.Lm;
   const lim=ss(.34,.22,d)*(1-ss(.55,.75,r))+ss(.45,.36,d)*ss(.55,.75,r),hip=Math.min(1,Math.max(0,ss(.64,.75,x*sd)+ss(.35,.2,y)));
   const w=na?0:ss(-.1,.16,t)*lim*hip*((x*sd>.18)?1:0)*((t<A.Lm+.3)?1:0);W[s]=w;if(w<=0)continue;
   const sc=A.Lf/A.Lm,v2=[pp[0]+t*sc*A.dm[0],pp[1]+t*sc*A.dm[1],pp[2]+t*sc*A.dm[2]],R=A.R;
   for(let i=0;i<3;i++){const q=R[i][0]*v2[0]+R[i][1]*v2[1]+R[i][2]*v2[2]+A.jf[i];Q[i]+=(q-P[i])*w}}
  const qy=Q[1];let tx=Q[0]*T.SX(qy),tz=T.zbf(qy)+(Q[2]-T.zbm(qy))*T.SZ(qy),lx=tx,lz=tz;
  for(const s of ['1','-1'])if(Q[0]*(+s)>0){const g=LG[s];lx=g.cxf(qy)+(Q[0]-g.cxm(qy))*g.sx(qy);lz=g.czf(qy)+(Q[2]-g.czm(qy))*g.sz(qy)}
  const bw=ss(CM+.15,CM-.2,qy);let ox=tx*(1-bw)+lx*bw,oy=qy,oz=tz*(1-bw)+lz*bw;
  for(const s of ['1','-1']){const w=W[s];if(!(w>0))continue;const A=AA[s],g=AR[s],rel=[Q[0]-A.jf[0],Q[1]-A.jf[1],Q[2]-A.jf[2]],t=dot(rel,A.df),tf=Math.min(1,Math.max(0,t/A.Lf)),pu=dot(rel,A.u),pv=dot(rel,A.v),k=ss(0,.1,tf);
   const su=1+(g.su(tf)-1)*k,sv=1+(g.sv(tf)-1)*k,nu=(g.cuf(tf)+(pu-g.cum(tf))*su)*k+pu*(1-k),nv=(g.cvf(tf)+(pv-g.cvm(tf))*sv)*k+pv*(1-k);
   const ax=A.jf[0]+t*A.df[0]+nu*A.u[0]+nv*A.v[0],ay=A.jf[1]+t*A.df[1]+nu*A.u[1]+nv*A.v[1],az=A.jf[2]+t*A.df[2]+nu*A.u[2]+nv*A.v[2];
   ox=ox*(1-w)+ax*w;oy=oy*(1-w)+ay*w;oz=oz*(1-w)+az*w}
  o[0]=ox;o[1]=oy;o[2]=oz;return o};
 // ---- hands: rigid, fitted to the skin hand (similarity ICP), so fingers keep their shape and sit inside the skin ----
 const HH=J.H,R0=.775,R1=.815,hp=(h,v)=>{const R=h.R;return[h.s*(R[0][0]*v[0]+R[0][1]*v[1]+R[0][2]*v[2])+h.t[0],h.s*(R[1][0]*v[0]+R[1][1]*v[1]+R[1][2]*v[2])+h.t[1],h.s*(R[2][0]*v[0]+R[2][1]*v[1]+R[2][2]*v[2])+h.t[2]]};
 if(HH)for(const s of ['1','-1']){const h=HH[s],tmp=[0,0,0];core(h.wc[0],h.wc[1],h.wc[2],tmp,0);const q=hp(h,h.wc);h.g=[q[0]-tmp[0],q[1]-tmp[1],q[2]-tmp[2]]}
 return function(x,y,z,o,na){core(x,y,z,o,na);if(na||!HH)return o;const Wc=core.W;
  for(const s of ['1','-1']){const A=AA[s],sd=+s,h=HH[s],v=[x-A.jm[0],y-A.jm[1],z-A.jm[2]],t=dot(v,A.dm),d=Math.hypot(v[0]-t*A.dm[0],v[1]-t*A.dm[1],v[2]-t*A.dm[2]),r=t/A.Lm,w=Wc[s]||0;
   if(w>0){const k=ss(.5,.8,r)*w;o[0]+=h.g[0]*k;o[1]+=h.g[1]*k;o[2]+=h.g[2]*k}
   const hw=ss(R0,R1,r)*ss(.62,.46,d)*ss(.5,.7,x*sd)*((t<A.Lm+.3)?1:0);if(hw<=0)continue;
   const q=hp(h,[x,y,z]);o[0]=o[0]*(1-hw)+q[0]*hw;o[1]=o[1]*(1-hw)+q[1]*hw;o[2]=o[2]*(1-hw)+q[2]*hw}
  return o}}
