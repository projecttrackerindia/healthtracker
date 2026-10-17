function makeFemWarp(J){
 const ss=(a,b,x)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t)};
 const lin=(spec,arr)=>{const[a,b,n]=spec;return x=>{const f=(x-a)/(b-a)*(n-1);if(f<=0)return arr[0];if(f>=n-1)return arr[n-1];const i=Math.floor(f),w=f-i;return arr[i]*(1-w)+arr[i+1]*w}};
 const T={SX:lin(J.TY,J.SX),SZ:lin(J.TY,J.SZ),zbm:lin(J.TY,J.zbm),zbf:lin(J.TY,J.zbf)},LG={},AR={},AA={};
 for(const s of ['1','-1']){const g=J.LEG[s];LG[s]={};for(const k in g)LG[s][k]=lin(J.LY,g[k]);const a=J.ARM[s];AR[s]={};for(const k in a)AR[s][k]=lin(J.AT,a[k]);AA[s]=J.A[s]}
 const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2],CM=J.CM;
 const core=function(x,y,z,o,na){const P=[x,y,z],Q=[x,y,z],W={};
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
 // ---- rigid hands: a hand is a rigid structure, so it follows the wrist instead of being squeezed with the forearm ----
 const HS=.9,RA=.8,R0=.775,R1=.815,nrm=a=>{const l=Math.hypot(a[0],a[1],a[2])||1;return[a[0]/l,a[1]/l,a[2]/l]},crs=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
 const rod=(a,b)=>{const c=dot(a,b),k=crs(a,b),s2=dot(k,k);if(s2<1e-12)return[[1,0,0],[0,1,0],[0,0,1]];const f=(1-c)/s2;return[[1-f*(k[1]*k[1]+k[2]*k[2]),-k[2]+f*k[0]*k[1],k[1]+f*k[0]*k[2]],[k[2]+f*k[0]*k[1],1-f*(k[0]*k[0]+k[2]*k[2]),-k[0]+f*k[1]*k[2]],[-k[1]+f*k[0]*k[2],k[0]+f*k[1]*k[2],1-f*(k[0]*k[0]+k[1]*k[1])]]};
 const mm=(A,B)=>A.map((r,i)=>[0,1,2].map(j=>r[0]*B[0][j]+r[1]*B[1][j]+r[2]*B[2][j])),mv=(M,v)=>[dot(M[0],v),dot(M[1],v),dot(M[2],v)];
 const H={};
 for(const s of ['1','-1']){const A=AA[s],g=AR[s],sc=A.Lf/A.Lm,R=A.R,Rt=[[R[0][0],R[1][0],R[2][0]],[R[0][1],R[1][1],R[2][1]],[R[0][2],R[1][2],R[2][2]]];
  const male=tf=>{const t=tf*A.Lf,c=[A.jf[0]+t*A.df[0]+g.cum(tf)*A.u[0]+g.cvm(tf)*A.v[0],A.jf[1]+t*A.df[1]+g.cum(tf)*A.u[1]+g.cvm(tf)*A.v[1],A.jf[2]+t*A.df[2]+g.cum(tf)*A.u[2]+g.cvm(tf)*A.v[2]],q=[c[0]-A.jf[0],c[1]-A.jf[1],c[2]-A.jf[2]],v2=mv(Rt,q),tm=dot(v2,A.dm)/sc,pp=[v2[0]-dot(v2,A.dm)*A.dm[0],v2[1]-dot(v2,A.dm)*A.dm[1],v2[2]-dot(v2,A.dm)*A.dm[2]];return[A.jm[0]+pp[0]+tm*A.dm[0],A.jm[1]+pp[1]+tm*A.dm[1],A.jm[2]+pp[2]+tm*A.dm[2]]};
  const fem=tf=>{const t=tf*A.Lf;return[A.jf[0]+t*A.df[0]+g.cuf(tf)*A.u[0]+g.cvf(tf)*A.v[0],A.jf[1]+t*A.df[1]+g.cuf(tf)*A.u[1]+g.cvf(tf)*A.v[1],A.jf[2]+t*A.df[2]+g.cuf(tf)*A.u[2]+g.cvf(tf)*A.v[2]]};
  const e=.04,m1=male(RA-e),m2=male(RA+e),f1=fem(RA-e),f2=fem(RA+e),a=nrm(mv(R,nrm([m2[0]-m1[0],m2[1]-m1[1],m2[2]-m1[2]]))),b=nrm([f2[0]-f1[0],f2[1]-f1[1],f2[2]-f1[2]]),Rw=mm(rod(a,b),R);
  H[s]={Wm:male(RA),Wf:fem(RA),M:Rw.map(r=>r.map(v=>v*HS))}}
 return function(x,y,z,o,na){core(x,y,z,o,na);if(na)return o;
  for(const s of ['1','-1']){const A=AA[s],sd=+s,h=H[s],v=[x-A.jm[0],y-A.jm[1],z-A.jm[2]],t=dot(v,A.dm),d=Math.hypot(v[0]-t*A.dm[0],v[1]-t*A.dm[1],v[2]-t*A.dm[2]),hw=ss(R0,R1,t/A.Lm)*ss(.62,.46,d)*ss(.5,.7,x*sd)*((t<A.Lm+.3)?1:0);if(hw<=0)continue;
   const q=mv(h.M,[x-h.Wm[0],y-h.Wm[1],z-h.Wm[2]]);o[0]=o[0]*(1-hw)+(h.Wf[0]+q[0])*hw;o[1]=o[1]*(1-hw)+(h.Wf[1]+q[1])*hw;o[2]=o[2]*(1-hw)+(h.Wf[2]+q[2])*hw}
  return o}}
