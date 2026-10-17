// One-time clean-up of the sample household that earlier versions saved into people's browsers.
// Removes only items that match the old sample data exactly; anything a person added or changed is kept.
// A full copy of the old state is kept on this device first (localStorage "dk6.backup").
const SAMPLE_M={m1:['p1','Prasanna',34],m2:['p3','Ananya',29],m3:['p2','Ramesh',61],m4:['p4','Lakshmi',58],m5:['p5','Arjun',24]};
const SAMPLE_LAB=new Set(['ldl|162|2026-10-12','tc|231|2026-10-12','hdl|38|2026-10-12','tg|168|2026-10-12','alt|58|2026-10-12','hba1c|5.6|2026-09-28','glu_f|95|2026-09-28','creat|0.9|2026-09-28','hb|14.6|2026-09-28','tsh|2.1|2026-09-28','vitd|18|2026-09-28','ldl|171|2026-04-09','vitd|22|2026-04-09',
 'hb|11.4|2026-10-02','tsh|4.6|2026-10-02','vitd|16|2026-10-02','glu_f|104|2026-10-02','hba1c|5.5|2026-10-02','b12|310|2026-10-02',
 'hba1c|6.8|2026-10-05','glu_f|138|2026-10-05','creat|1.4|2026-10-05','ldl|118|2026-10-05','tg|190|2026-10-05','uric|7.9|2026-10-05','hba1c|7.1|2026-06-20','creat|1.3|2026-06-20',
 'hb|12.6|2026-09-20','vitd|22|2026-09-20','alt|62|2026-09-20','tc|224|2026-09-20','b12|180|2026-09-20','ca|9.4|2026-09-20',
 'hb|15.2|2026-08-14','wbc|6.4|2026-08-14','vitd|24|2026-08-14','glu_f|88|2026-08-14']);
const SAMPLE_FIND=new Set(['Ultrasound abdomen|2026-10-10','ECG|2026-10-12','Chest X-ray|2026-08-30','Blood test (CBC)|2026-10-18']);
const SAMPLE_MED=new Set(['m1|Atorvastatin|10 mg tablet','m1|Ursodeoxycholic acid|300 mg tablet','m1|Vitamin D3|60,000 IU sachet','m2|Iron + folic acid|1 tablet','m2|Vitamin D3|1000 IU softgel',
 'm3|Atorvastatin|20 mg tablet','m3|Amlodipine|5 mg tablet','m4|Calcium + Vitamin D3|1 tablet','m4|Vitamin B12|1500 mcg tablet']);
const SAMPLE_NAMES=new Set(['Prasanna','Ananya','Ramesh','Lakshmi','Arjun']);
const SAMPLE_MID={m1:{blood:'B+',allergies:['Penicillin'],conditions:['High cholesterol','Gallstones'],donor:'yes',doctor:'Dr. Sarah Wilson'},m2:{blood:'O+',doctor:'Dr. Fatima Khan'},m3:{blood:'A+',allergies:['Sulfa drugs'],conditions:['Coronary artery disease','Enlarged prostate'],doctor:'Dr. Sarah Wilson'},m4:{},m5:{}};
function purgeSample(s){try{
 if(!s||s.mig>=2)return s;
 const had=s.members.some(m=>/^p[1-5]$/.test(m.pid||''))||(s.vault||[]).some(v=>v.demo)||(s.orders||[]).length>0||Object.values(s.appts||{}).some(l=>(l||[]).some(a=>a&&a.doc));
 if(!had){s.mig=2;return s}
 try{if(!localStorage.getItem('dk6.backup'))localStorage.setItem('dk6.backup',JSON.stringify({t:Date.now(),s}))}catch(e){}
 let n=0;const drop=(arr,f)=>{if(!Array.isArray(arr))return arr;const o=arr.filter(x=>!f(x));n+=arr.length-o.length;return o};
 const isLab=r=>r&&r.k==='lab'&&SAMPLE_LAB.has(r.key+'|'+(+r.val)+'|'+r.date),isFind=r=>r&&r.k==='find'&&SAMPLE_FIND.has(r.n+'|'+r.date);
 for(const id in (s.results||{}))s.results[id]=drop(s.results[id],r=>isLab(r)||isFind(r));
 s.vault=drop(s.vault||[],v=>v&&v.demo);
 for(const id in (s.meds||{}))s.meds[id]=drop(s.meds[id],x=>x&&SAMPLE_MED.has(id+'|'+x.n+'|'+x.dose));
 for(const id in (s.appts||{}))s.appts[id]=drop(s.appts[id],a=>a&&a.doc);          // bookings with fictional doctors were never sent anywhere
 for(const id in (s.contacts||{}))s.contacts[id]=drop(s.contacts[id],c=>c&&/^c[1-6]$/.test(c.id)&&!c.ph&&SAMPLE_NAMES.has(c.n));
 n+=(s.orders||[]).length;s.orders=[];                                                 // simulated orders: nothing was ever sent to a pharmacy
 for(const id in SAMPLE_MID){const a=(s.mid||{})[id],b=SAMPLE_MID[id];if(!a)continue;
  const same=(k,d)=>JSON.stringify(a[k]==null?d:a[k])===JSON.stringify(b[k]==null?d:b[k]);
  if(['blood','donor','doctor'].every(k=>same(k,''))&&['allergies','conditions'].every(k=>same(k,[]))&&!a.notes&&!a.policy){delete s.mid[id];n++}}
 const keep=[];
 for(const m of s.members){const d=SAMPLE_M[m.id];
  if(d&&m.pid===d[0]){const own=(s.results&&s.results[m.id]||[]).length+(s.meds&&s.meds[m.id]||[]).length+(s.appts&&s.appts[m.id]||[]).length+(s.contacts&&s.contacts[m.id]||[]).length+(s.vault||[]).filter(v=>v.m===m.id).length+((s.mid||{})[m.id]?1:0)+(s.preg&&s.preg[m.id]?1:0);
   if(m.name===d[1]&&m.age===d[2]&&!own){n++;['results','meds','appts','contacts','taken','mid','preg','vitals'].forEach(k=>{if(s[k])delete s[k][m.id]});continue}
   m.pid=null;m.review=1}                                                              // the person changed or used it: keep, but unlink the sample findings
  else if(m.pid&&/^p[1-5]$/.test(m.pid)){m.pid=null;m.review=1}
  keep.push(m)}
 s.members=keep;
 if(Array.isArray(s.cart))s.cart=s.cart.filter(c=>keep.some(m=>m.id===c.m));
 if(!s.members.some(m=>m.rel==='You'))s.members.unshift({id:'m'+Math.random().toString(36).slice(2,9),pid:null,name:'You',rel:'You',age:0,sex:'male',w:0,h:0,av:'YO',c:'',shared:true});
 if(!s.members.some(m=>m.id===s.active))s.active=s.members[0].id;
 try{const p=JSON.parse(localStorage.getItem('dk-preg-prof')||'null');if(p&&p.name==='Ananya'&&p.lmp==='2026-04-23')localStorage.removeItem('dk-preg-prof')}catch(e){}
 s.mig=2;s.purged={t:Date.now(),n};return s}catch(e){console.warn('purge',e);return s}}
