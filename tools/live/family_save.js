SX.chg.fsave=([id],f)=>{const fd=new FormData(f),err=f.querySelector('.lv-err'),say=t=>{if(err){err.textContent=t;err.hidden=false}else toast(t)};
 const name=String(fd.get('name')||'').replace(/\s+/g,' ').trim().slice(0,60),dob=String(fd.get('dob')||''),w=+fd.get('w')||0,h=+fd.get('h')||0,sex=String(fd.get('sex')||''),rel=String(fd.get('rel')||'Other'),blood=String(fd.get('blood')||''),rawPh=String(fd.get('ph')||'').trim();
 if(name.length<2)return say('Please enter the full name.');
 if(!dob||new Date(dob+'T00:00')>new Date()||SX.ageFrom(dob)>120)return say('Please check the date of birth.');
 if(sex!=='female'&&sex!=='male')return say('Please choose Female or Male.');
 if(w&&(w<2||w>300)||h&&(h<30||h>250))return say('Please check weight and height.');
 let ph='';if(rawPh){ph=SX.phoneNorm(rawPh);if(!ph||!/^\+\d{10,15}$/.test(ph))return say('Please check the mobile number.')}
 const age=SX.ageFrom(dob),av=name.split(' ').map(x=>x[0]).join('').slice(0,2).toUpperCase();
 let m;if(id){m=SX.member(id);const sex0=m.sex;Object.assign(m,{name,age,dob,sex,sexOk:true,rel:m.rel==='You'?'You':rel,w,h,av,ph:ph||m.ph||''});delete m.review;const p=SX.pat(m);if(p){p.n=name;p.age=age}
  if(sex!==sex0&&m.id===S.active){SX.pendingModel=true;SX.applyModel()}toast('Saved '+name)}
 else{m={id:uid('m'),pid:null,name,rel,age,dob,sex,sexOk:true,w,h,av,ph,c:['','m','g','y'][S.members.length%4],shared:true,htid:SX.newHtid()};S.members.push(m);toast(name+' added')}
 const mid=SX.midOf(m.id);mid.blood=blood;m.bloodUnknown=!blood;
 SX.ledger('member',true,(id?'Updated ':'Added ')+name,m.id);famEdit=null;SX.save();SX.syncPreg();render();SX.paintWho();if(!id)SX.act.lvcardshow([m.id])};
