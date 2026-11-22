/* ================= helpers ================= */
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const DAY=864e5,addDays=(d,n)=>new Date(d.getTime()+n*DAY),iso=d=>d.toISOString().slice(0,10);
const fmt=d=>d.toLocaleDateString("en-IN",{weekday:"short",day:"numeric",month:"short"});
const rs=n=>"₹"+Math.round(n).toLocaleString("en-IN");
const CHECK='<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l4 4 10-10"/></svg>';
const INFO='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.5"/></svg>';

/* ================= data ================= */
const CAT={
  m:{label:"Mother",h:"Mother.",s:"Nursing and recovery, from Mee Mee and Pee Safe."},
  b:{label:"Baby",h:"Baby.",s:"Clothes from SuperBottoms, everything else from Mee Mee."},
  d:{label:"Bag",h:"The bag.",s:"Carries it all, with pockets for the MCP card and reports."}
};
const BRANDS=[["Mee Mee","Baby care and nursing"],["SuperBottoms","Baby clothes"],["Pee Safe","Care after birth"]];
// id, cat, name, note, price, qty in complete bag, 2D art, 3D model, in complete bag, colour, options, printed label, brand
/* Prices: field 4 is the brand's own price (the list price). Every item sells at least OFF% below it, rounded down to the
   rupee, exactly as the server does (bagshop.offer_price), and badges round the percentage down, so they never overstate. */
const OFF=30;
const offerPrice=l=>{const n=l*(100-OFF);return (n-n%100)/100};
const pctOff=(l,p)=>{if(!l)return 0;const n=(l-p)*100;return (n-n%l)/l};
const ITEMS=[
["mm-bra","m","Nursing bra","Wire-free, padded, 100% cotton",749,2,"vest","bra",1,"#E3C9BE",["S","M","L","XL"],"","Mee Mee"],
["mm-bpads","m","Breast pads","Ultra-thin and disposable, pack of 24",229,1,"pack","pack",1,"#E8DDEB",null,"BREAST PADS · 24","Mee Mee"],
["ps-pads","m","Maternity pads","Extra-long 480 mm, two packs of 8",419,1,"pack","pack",1,"#D9D2EA",null,"MATERNITY PADS · 16","Pee Safe"],
["ps-undies","m","Disposable underwear","Comfort panty, pack of 4",180,1,"pack","pack",1,"#E6D2CF",["L–XL","XL–XXL"],"COMFORT PANTY · 4","Pee Safe"],
["ps-wash","m","Intimate wash","pH-balanced and soap-free, 105 ml",126,1,"bottle","wash",1,"#E7D3E2",null,"INTIMATE WASH","Pee Safe"],
["mm-belt","m","Belly support belt","Pre- and post-natal corset belt",799,0,"fold","belt",0,"#D6C5B6",null,"","Mee Mee"],
["sb-jhabla","b","Mulmul jhablas","100% mulmul cotton, snap buttons",411,6,"vest","jhabla",1,"#EEEAE3",["0–3 m","3–6 m"],"","SuperBottoms"],
["sb-caps","b","Cap, mittens, booties and bib","100% cotton newborn set",399,2,"vest","capset",1,"#E0CDD3",null,"","SuperBottoms"],
["mm-swad","b","Muslin swaddles","Set of 3, 120 × 100 cm",999,1,"fold","fold",1,"#BFD0E2",null,"","Mee Mee"],
["mm-towel","b","Bamboo cotton towels","Soft and absorbent, wraps the whole body",799,2,"fold","towel",1,"#E5D7C3",null,"","Mee Mee"],
["mm-diaper","b","Newborn diapers","Tape diapers with wetness indicator, pack of 16",215,2,"pack","pack",1,"#C5D6EA",null,"NEWBORN · 16","Mee Mee"],
["mm-wipes","b","Baby wipes","Aloe vera, with a lid, pack of 72",149,1,"pack","pack",1,"#D3E6DC",null,"BABY WIPES · 72","Mee Mee"],
["mm-nest","b","Padded carry nest","Warm and snug, in place of a loose blanket",999,1,"roll","roll",1,"#CDD5E0",null,"","Mee Mee"],
["sb-home","b","Going-home set","Pure Love gift set, 5 pieces",1049,0,"vest","outfit",0,"#E3D2B3",null,"","SuperBottoms"],
["mm-bag","d","Diaper backpack","12 pockets, with room for the MCP card and reports",1999,1,"pouch","backpack",1,"#5E6B7A",null,"","Mee Mee"],
["uh-card","d","Emergency card","Laminated, with your Medical ID QR",0,1,"folder","card",1,"#2C2C2E",null,"MEDICAL ID","Urban Health"]
].map(r=>({id:r[0],cat:r[1],name:r[2],note:r[3],list:r[4],price:offerPrice(r[4]),def:r[5],kind:r[6],model:r[7],inB:!!r[8],col:r[9],opts:r[10],lab:r[11],brand:r[12],free:r[4]===0}));
window.ITEMS=ITEMS;
const byId=id=>ITEMS.find(i=>i.id===id);
const catItems=k=>ITEMS.filter(i=>i.cat===k);
const ESS=ITEMS.filter(i=>i.inB).length;
window.THUMB={};
const HOSP=[["mm-diaper","Newborn diapers"],["ps-pads","Maternity pads"],["sb-jhabla","Baby clothes"]];
// what the family packs themselves (the server's HOME_ITEMS; the live list replaces this when it loads)
let HOME=[["mcp","MCP card"],["scan","Scan and lab reports"],["idp","ID proof"],["ins","Insurance card"],["h-nighty","Two or three front-open nighties"],["h-clothes","Loose clothes to go home in"],["h-slip","Slippers and socks"],["h-toil","Toothbrush, paste, soap and comb"],["h-bottle","Water bottle"],["h-snack","Snacks for you and your partner"],["h-hair","Hair ties"],["ph","Phone, charger and power bank"]];
const price=it=>it.free?"Free":rs(it.price);
const wasHTML=it=>it.free||!(it.list>it.price)?"":`<div class="was"><s>${rs(it.list)}</s><i>${pctOff(it.list,it.price)}% off</i></div>`;

/* ================= state ================= */
const today=new Date();
const S={due:iso(addDays(today,56)),plan:"normal",twins:false,start:"complete",hosp:new Set(),travel:false,man:{},own:new Set(),vr:{},
  winterAdd:false,q:{},why:{},recent:[],date:1,packed:{}};

function weekNow(){return Math.max(4,Math.min(41,Math.round(40-(new Date(S.due)-today)/DAY/7)))}
function delDates(){const min=addDays(today,3),w36=addDays(new Date(S.due),-28),best=w36<min?min:w36;
  const wk=d=>Math.min(40,Math.round(40-(new Date(S.due)-d)/DAY/7));
  return [addDays(best,-4),best,addDays(best,3)].map((d,i)=>{const dd=d<min?addDays(min,i):d;return {d:dd,t:"Week "+wk(dd)+(i===1?" · suggested":"")}})}
function optIdx(it){if(S.vr[it.id]!=null)return S.vr[it.id];let d=it.id==="ps-undies"&&S.plan==="cs"?1:0;
  if(it.opts&&it.stock&&it.stock[it.opts[d]]===0){const j=it.opts.findIndex(o=>it.stock[o]!==0);if(j>=0)d=j}return d}
window.__optIdx=optIdx;
/* live price, stock and availability come from /api/v1/shop/bag; a size the team doesn't count has no limit */
const optKey=it=>it.opts?it.opts[optIdx(it)]:"";
const left=(it,k=optKey(it))=>{const v=it.stock&&it.stock[k];return v==null?Infinity:v};
const avail=it=>!it.off&&left(it)>0;
const lowTxt=it=>{const n=left(it);return !it.off&&n>0&&n<=3?`<div class="low">Only ${n} left${optKey(it)?" in "+optKey(it):""}</div>`:""};

function compute(){
  const q={},why={},winter=[10,11,0,1].includes(new Date(S.due).getMonth());
  ITEMS.forEach(i=>q[i.id]=S.start==="complete"?i.def:0);
  const add=(id,n,w)=>{q[id]+=n;why[id]=w};
  if(S.plan==="cs"){add("mm-belt",1,"Added for support after a C-section");why["ps-undies"]="Set one size up, so it sits comfortably above the stitches"}
  if(S.twins)ITEMS.filter(i=>i.cat==="b"&&q[i.id]).forEach(i=>{q[i.id]*=2;why[i.id]="Doubled for twins"});
  if(S.winterAdd){add("sb-caps",1,"One more set for a cooler-month birth")}
  S.hosp.forEach(id=>{if(q[id]||S.start==="complete"){q[id]=0;why[id]="Your hospital provides this"}});
  ITEMS.forEach(i=>q[i.id]=Math.max(0,Math.min(i.free?1:99,q[i.id]+(S.man[i.id]||0))));
  ITEMS.forEach(i=>{if(!q[i.id])return;if(i.off){q[i.id]=0;why[i.id]="Not available right now";return}
    const n=left(i);if(q[i.id]>n){q[i.id]=n;why[i.id]=n?`Only ${n} left${optKey(i)?" in "+optKey(i):""}`:`Sold out${optKey(i)?" in "+optKey(i):""} right now`}});
  S.own.forEach(id=>{q[id]=0;why[id]="You have this — it stays on your packing list"});
  S.q=q;S.why=why;
}
function totals(){
  let units=0,tot=0,full=0,save=0,complete=true;
  ITEMS.forEach(i=>{const q=S.q[i.id]||0;units+=q;full+=q*i.list;
    const cap=i.inB?i.def*(S.twins&&i.cat==="b"?2:1):0,b=Math.min(q,cap);
    tot+=b*i.price*LIVE.rate+(q-b)*i.price;if(i.inB&&q<i.def)complete=false});
  const total=Math.round(tot);   // whole rupees: full and total are exact sums, so full − save = total to the rupee
  return {units,total,save:full-total,off:pctOff(full,total),complete,full};
}

/* ================= pictures ================= */
const LIVE={policy:[],rate:1};
function pic(it){return THUMB[it.id]?`<img src="${THUMB[it.id]}" alt="" draggable="false">`:(window.NO3D?art(it.kind,it.col):'<span class="ph"></span>')}
/*ART*/

/* ================= builder render ================= */
function stepper(id,q){const it=byId(id),mx=it&&(q>=left(it)||it.off||it.free);return `<div class="step"><button data-dec="${id}" aria-label="One less">${q===1?'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1D1D1F" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>':"−"}</button><span>${q}</span><button data-inc="${id}" aria-label="One more" ${mx?"disabled":""}>+</button></div>`}
function rowHTML(it){
  const q=S.q[it.id]||0,own=S.own.has(it.id),w=S.why[it.id],hosp=S.hosp.has(it.id)&&!q;
  return `<div class="row${own||hosp?" dim":""}" data-row="${it.id}">
  <button class="thumb" data-view="${it.id}" aria-label="View ${it.name}">${pic(it)}</button>
  <div class="info"><div class="brd">${it.brand}</div><div class="nm">${it.name}${it.inB?"":'<span class="xtag">Extra</span>'}</div><div class="nt">${it.note}</div>
   ${it.opts&&!own&&!hosp?`<div class="opts">${it.opts.map((o,j)=>`<button class="opt" data-opt="${it.id}:${j}" aria-pressed="${j===optIdx(it)}" ${it.stock&&it.stock[o]===0?'disabled title="Sold out"':""}>${o}</button>`).join("")}</div>`:""}${!own&&!hosp?lowTxt(it):""}
   ${w?`<div class="why1">${INFO}<span>${w}</span></div>`:""}</div>
  <div class="act"><div class="prc"><div class="pr${it.free?" fr":""}">${price(it)}${q>1?`<span> × ${q}</span>`:""}</div>${wasHTML(it)}</div>
   ${own?`<button class="lnk" data-unown="${it.id}">Add to bag instead</button>`:q?stepper(it.id,q):`${avail(it)?`<button class="addb" data-inc="${it.id}">Add</button>`:`<span class="sold">${it.off?"Unavailable":"Sold out"}</span>`}${hosp?"":`<button class="lnk" data-own="${it.id}">I have one</button>`}`}</div></div>`;
}
function oc(attr,val,cur,b,s,extra=""){return `<button class="oc" ${attr}="${val}" aria-pressed="${cur===val}">${extra}<b>${b}</b><span>${s}</span></button>`}
function renderConfig(){
  const t=totals(),dd=delDates()[1].d,changes=ITEMS.filter(i=>S.why[i.id]);
  $("#config").innerHTML=`
  <section class="cs"><h3>Due date. <span>When is your baby due?</span></h3>
   <label class="due"><input type="date" id="due" value="${S.due}" aria-label="Due date"><span class="dw">You’re in <b>week ${weekNow()}</b>.<br>We’ll suggest delivery by <b>${fmt(dd)}</b>.</span></label>
   ${[10,11,0,1].includes(new Date(S.due).getMonth())?(S.winterAdd?`<div class="sugrow">An extra cap set is in for the cooler months. <button class="lnk" data-winter>Undo</button></div>`:`<div class="sugrow">Due in the cooler months? <button class="lnk" data-winter>Add an extra cap set</button></div>`):""}</section>
  <section class="cs"><h3>Delivery. <span>How are you planning to deliver?</span></h3>
   <div class="cards c3">${oc("data-plan","normal",S.plan,"Normal delivery","The standard list for a hospital stay.")}${oc("data-plan","cs",S.plan,"C-section","Adds support and comfort for recovery.")}${oc("data-plan","ns",S.plan,"Not sure yet","We’ll keep the list flexible.")}</div>
   <button class="swrow" data-twins aria-pressed="${S.twins}"><span><b>Expecting twins</b><span>Doubles the baby essentials.</span></span><i class="tgl"></i></button></section>
  <section class="cs"><h3>Your hospital. <span>Anything they already provide?</span></h3>
   <div class="chips">${HOSP.map(([id,l])=>`<button class="chip" data-hosp="${id}" aria-pressed="${S.hosp.has(id)}"><span class="ck">${CHECK}</span>${l}</button>`).join("")}</div>
   <p class="hint">We’ll take these off your bill. Ask your hospital if you’re not sure.</p></section>
  ${Object.keys(CAT).map(k=>`<section class="cs" id="cat-${k}"><h3>${CAT[k].h} <span>${CAT[k].s}</span></h3><div class="rows">${catItems(k).map(rowHTML).join("")}</div></section>`).join("")}
  <section class="cs" id="home"><h3>From home. <span>Pack these yourself.</span></h3>
   <ul class="hlist">${homeHTML()}</ul>
   <button class="btn sec sm" data-packlist>Open the packing checklist</button></section>
`;
}
function homeHTML(){return HOME.concat([...S.own].map(id=>[id,byId(id).name])).map(([id,n])=>`<li><button class="hi" data-hk="${id}" aria-pressed="${!!S.packed[id]}"><i class="hd">${CHECK}</i><span>${esc(n)}</span></button></li>`).join("")}
function renderHome(){const h=$("#home .hlist");if(h)h.innerHTML=homeHTML()}
function renderRow(id){const el=$(`[data-row="${id}"]`);if(el)el.outerHTML=rowHTML(byId(id))}
const shown={};
function countTo(el,v){const k=el.id,from=shown[k]??v;shown[k]=v;if(from===v){el.textContent=rs(v);return}const t0=performance.now();
  (function f(){const k=Math.min(1,(performance.now()-t0)/450),e=1-Math.pow(1-k,3);el.textContent=rs(from+(v-from)*e);if(k<1)requestAnimationFrame(f)})()}
function renderMeta(){
  const t=totals();
  countTo($("#pTotal"),t.total);$("#pMrp").textContent=t.save?rs(t.full):"";$("#pOff").textContent=t.off?t.off+"% off":"";$("#pOff").hidden=!t.off;
  $("#pNote").textContent=(t.complete?"Complete bag":"Your bag")+(t.save?` · you save ${rs(t.save)} on brand prices`:"");saveBag();
  $("#bUnits").textContent=t.units+(t.units===1?" item":" items");
  $("#smeta").innerHTML=Object.keys(CAT).map(k=>{const n=catItems(k).reduce((a,i)=>a+(S.q[i.id]||0),0);return `<button class="smt" data-jump="${k}"><small>${CAT[k].label}</small><b>${n}</b></button>`}).join("");
  countTo($("#sbTotal"),t.total);
  $("#sbSave").innerHTML=t.save?`<span class="sbo">${t.off}% off · </span>you save ${rs(t.save)}`:"";
  $("#sbMeta").textContent=`${t.units} items · arrives by ${fmt(delDates()[S.date].d)}`;
  const st=ITEMS.filter(i=>S.q[i.id]).slice(-4);
  $("#sbst").innerHTML=st.map(i=>`<div>${pic(i)}</div>`).join("");
}
function refresh(full=true){compute();if(full)renderConfig();renderMeta();syncBag()}
/* ================= 3D bag sync ================= */
const ORDER=["mm-bag","mm-nest","mm-towel","mm-swad","sb-jhabla","sb-home","mm-bra","mm-belt","mm-diaper","ps-pads","mm-wipes","ps-undies","mm-bpads","sb-caps","ps-wash","uh-card"];
function desired(){return ORDER.filter(id=>(S.q[id]||0)>0)}
function syncBag(){if(window.B3&&B3.ok)B3.sync(desired())}

/* ================= interactions ================= */
let tt;function toast(m){$("#toastT").textContent=m;$("#toast").classList.add("on");clearTimeout(tt);tt=setTimeout(()=>$("#toast").classList.remove("on"),1900)}
function activeHost(){return (window.B3&&B3.host)||$("#buildBag")}
function fly(it,fromEl){
  const host=activeHost(),b=host.getBoundingClientRect();if(!fromEl)return;const a=fromEl.getBoundingClientRect();
  if(b.bottom<0||b.top>innerHeight||a.width===0)return;
  const s=Math.max(56,Math.min(96,a.width));const f=document.createElement("div");f.className="flyer";
  f.style.cssText=`left:${a.left+a.width/2-s/2}px;top:${a.top+a.height/2-s/2}px;width:${s}px;height:${s}px`;f.innerHTML=pic(it);document.body.appendChild(f);
  const dx=b.left+b.width/2-(a.left+a.width/2),dy=b.top+b.height*.42-(a.top+a.height/2);
  f.animate([{transform:"translate(0,0) scale(1)",opacity:1},{transform:`translate(${dx*.55}px,${dy*.55-120}px) scale(.85) rotate(-10deg)`,opacity:1,offset:.55},{transform:`translate(${dx}px,${dy}px) scale(.3) rotate(8deg)`,opacity:0}],{duration:760,easing:"cubic-bezier(.45,0,.3,1)"}).onfinish=()=>f.remove();
}
function canAdd(id){const it=byId(id),q=S.q[id]||0;if(it.off){toast(it.name+" isn’t available right now");return false}
  if(it.free&&q>=1){toast("One emergency card comes with every bag");return false}
  const n=left(it);if(q>=n){toast(n?`Only ${n} left${optKey(it)?" in "+optKey(it):""}`:`Sold out${optKey(it)?" in "+optKey(it):""}`);return false}return true}
function inc(id,src){if(!canAdd(id))return;const before=S.q[id]||0;S.man[id]=(S.man[id]||0)+1;compute();renderRow(id);renderMeta();
  navigator.vibrate&&navigator.vibrate(10);fly(byId(id),src);setTimeout(()=>{syncBag();if(before>0&&window.B3&&B3.ok)B3.bump()},620);
  if(V.open)renderVInfo();}
function dec(id){if(!(S.q[id]>0))return;S.man[id]=(S.man[id]||0)-1;compute();renderRow(id);renderMeta();syncBag();if(V.open)renderVInfo()}

document.addEventListener("click",e=>{
  const t=e.target.closest("button,a");if(!t)return;const d=t.dataset;
  if(d.inc){inc(d.inc,t.closest(".row")?.querySelector(".thumb")||$(".vimg.sel")||t)}
  else if(d.dec)dec(d.dec);
  else if(d.opt){const[id,j]=d.opt.split(":");S.vr[id]=+j;compute();renderRow(id);renderMeta();syncBag();if(V.open)renderVInfo()}
  else if(d.own){S.own.add(d.own);refresh(false);renderRow(d.own);toast("Added to your packing list")}
  else if(d.unown){S.own.delete(d.unown);refresh(false);renderRow(d.unown)}
  else if(d.plan){S.plan=d.plan;refresh();toast(d.plan==="cs"?"Updated for a C-section":"Bag updated")}
  else if("winter" in d){S.winterAdd=!S.winterAdd;refresh();toast(S.winterAdd?"Extra cap set added":"Bag updated")}
  else if("twins" in d){S.twins=!S.twins;refresh();toast(S.twins?"Baby essentials doubled":"Bag updated")}
  else if(d.start){S.start=d.start;S.man={};refresh();toast(d.start==="complete"?"Complete bag added":"Bag emptied — add what you need")}
  else if(d.hosp){S.hosp.has(d.hosp)?S.hosp.delete(d.hosp):S.hosp.add(d.hosp);refresh()}
  else if("sug" in d){const a=$("#askT");a.value=t.textContent;a.focus()}
  else if(d.view){openViewer(d.view,t)}
  else if(d.jump){$("#cat-"+d.jump)?.scrollIntoView({behavior:"smooth",block:"start"})}
  else if("packlist" in d){openSheet(5)}
  else if(d.hk){S.packed[d.hk]=!S.packed[d.hk];if(!S.packed[d.hk])delete S.packed[d.hk];navigator.vibrate&&navigator.vibrate(8);renderHome();saveBag();savePack()}
  else if("buy" in d){openSheet(0)}
  else if("signin" in d){openSheet(1)}
  else if("close" in d){closeSheet()}
});
document.addEventListener("change",e=>{if(e.target.id==="due"&&e.target.value){S.due=e.target.value;refresh()}});
document.addEventListener("click",e=>{if(e.target.closest("#askGo"))runAsk()});
document.addEventListener("keydown",e=>{if(e.target.id==="askT"&&e.key==="Enter"&&!e.shiftKey){e.preventDefault();runAsk()}});
function runAsk(){
  const t=($("#askT").value||"").toLowerCase().trim();if(!t)return;
  if(/c-?\s?section|caesar|cesar/.test(t))S.plan="cs";
  if(/twin/.test(t))S.twins=true;
  if(/diaper/.test(t)&&/hospital|give|provide/.test(t))S.hosp.add("mm-diaper");
  if(/pad/.test(t)&&/hospital|give|provide/.test(t))S.hosp.add("ps-pads");
  const HAVE={towel:"mm-towel",blanket:"mm-nest",nest:"mm-nest",swaddle:"mm-swad",jhabla:"sb-jhabla",backpack:"mm-bag",belt:"mm-belt"};
  const hv=(t.match(/(?:already have|we have|i have|have got|already own)\s+([^.]+)/)||[])[1]||"";
  Object.entries(HAVE).forEach(([k,id])=>{if(hv.includes(k))S.own.add(id)});
  refresh();toast("Bag updated for you");setTimeout(()=>$(".changes")?.scrollIntoView({behavior:"smooth",block:"center"}),80);
}

/* ================= product viewer (shared-element) ================= */
const V={open:false,cat:"b",i:0,els:[]};
const viewer=$("#viewer"),vcard=$("#vcard"),vstage=$("#vstage");
function vGeom(){const W=innerWidth,H=innerHeight,mob=W<700;const cw=mob?Math.min(W-56,330):380,ch=Math.max(420,Math.min(H-176,620));
  const top=76,left=W/2-cw/2,sel=Math.min(cw*.74,ch-250);return {W,H,mob,cw,ch,top,left,sel,selTop:top+30,nb:mob?84:Math.min(170,(W-cw)/2-90),gap:mob?cw/2+30:cw/2+150,step:mob?0:230,midY:top+30+sel/2}}
function buildV(){vstage.innerHTML="";V.els=catItems(V.cat).map((it,i)=>{const d=document.createElement("button");d.className="vimg";d.setAttribute("aria-label",it.name);d.innerHTML=pic(it)+`<span class="vcap">${it.name}<span>${price(it)}${it.list>it.price?` <s>${rs(it.list)}</s>`:""}</span></span>`;d.onclick=()=>{if(i!==V.i){V.i=i;layoutV();renderVInfo()}};vstage.appendChild(d);return d});
  $("#vSeg").innerHTML=Object.keys(CAT).map(k=>`<button data-vcat="${k}" aria-pressed="${k===V.cat}">${CAT[k].label}</button>`).join("");
  $$("#vSeg [data-vcat]").forEach(b=>b.onclick=()=>{V.cat=b.dataset.vcat;V.i=0;buildV();layoutV(true);renderVInfo()});}
function layoutV(instant){const g=vGeom(),n=V.els.length;
  Object.assign(vcard.style,{left:g.left+"px",top:g.top+"px",width:g.cw+"px",height:g.ch+"px"});
  V.els.forEach((el,i)=>{const d=i-V.i,sel=d===0,sz=sel?g.sel:g.nb;const cx=g.W/2+(d===0?0:Math.sign(d)*(g.gap+(Math.abs(d)-1)*g.step));
    const vis=sel||(g.mob?Math.abs(d)===1:Math.abs(d)<=2);
    if(instant)el.style.transition="none";
    Object.assign(el.style,{left:(cx-sz/2)+"px",top:(sel?g.selTop:g.midY-sz/2)+"px",width:sz+"px",height:sz+"px",opacity:vis?1:0,pointerEvents:vis?"auto":"none",zIndex:sel?3:2});
    el.classList.toggle("sel",sel);el.querySelector(".vcap").style.opacity=sel||g.mob?0:1;
    if(instant){el.offsetWidth;el.style.transition=""}});
  const ar=$("#vArr");ar.style.top=(g.top+g.ch+16)+"px";$("#vPos").textContent=(V.i+1)+" / "+n;
}
function renderVInfo(){const it=catItems(V.cat)[V.i],q=S.q[it.id]||0;
  $("#vinfo").innerHTML=`<div class="fadein"><small>${it.brand} · ${CAT[it.cat].label}${it.inB?"":" · extra"}</small><h3>${it.name}</h3><p>${it.note}</p></div>
  ${it.opts?`<div class="opts fadein" style="margin:0">${it.opts.map((o,j)=>`<button class="opt" data-opt="${it.id}:${j}" aria-pressed="${j===optIdx(it)}" ${it.stock&&it.stock[o]===0?'disabled title="Sold out"':""}>${o}</button>`).join("")}</div>`:""}
  <div class="vrow fadein"><span class="prw"><span class="pr">${price(it)}</span>${wasHTML(it)}</span>${q?stepper(it.id,q):avail(it)?`<button class="addb" data-inc="${it.id}" style="height:40px;padding:0 20px;font-size:15px">Add to bag</button>`:`<span class="sold">${it.off?"Unavailable":"Sold out"}</span>`}</div>${lowTxt(it)}`}
function openViewer(id,thumb){
  const it=byId(id);V.cat=it.cat;V.i=catItems(V.cat).indexOf(it);V.open=true;V.from=id;
  buildV();viewer.classList.add("open");document.body.classList.add("lock");layoutV(true);renderVInfo();
  const fr=thumb.getBoundingClientRect(),g=vGeom(),E="cubic-bezier(.65,0,.25,1)";
  vcard.animate([{transform:`translate(${fr.left-g.left}px,${fr.top-g.top}px) scale(${fr.width/g.cw},${fr.height/g.ch})`,borderRadius:"60px"},{transform:"none",borderRadius:"32px"}],{duration:620,easing:E});
  $("#vinfo").animate([{opacity:0},{opacity:0,offset:.5},{opacity:1}],{duration:720});
  const el=V.els[V.i],er={left:parseFloat(el.style.left),top:parseFloat(el.style.top),w:parseFloat(el.style.width)};
  el.animate([{transform:`translate(${fr.left-er.left}px,${fr.top-er.top}px) scale(${fr.width/er.w})`,transformOrigin:"0 0"},{transform:"none",transformOrigin:"0 0"}],{duration:620,easing:E});
  V.els.forEach((x,i)=>{if(i!==V.i)x.animate([{opacity:0,transform:`translateX(${(i<V.i?-1:1)*60}px)`},{opacity:0,offset:.35},{opacity:1,transform:"none"}],{duration:700,easing:E})});
  $("#vClose").focus({preventScroll:true});
}
function closeViewer(){if(!V.open)return;const it=catItems(V.cat)[V.i];const th=$(`[data-view="${it.id}"]`);const g=vGeom(),E="cubic-bezier(.65,0,.25,1)";
  let fr=th&&th.getBoundingClientRect();const visible=fr&&fr.bottom>0&&fr.top<innerHeight;
  const done=()=>{viewer.classList.remove("open");document.body.classList.remove("lock");V.open=false;vstage.innerHTML="";renderRow(it.id)};
  if(!visible){viewer.animate([{opacity:1},{opacity:0}],{duration:250}).onfinish=done;return}
  vcard.animate([{transform:"none",borderRadius:"32px"},{transform:`translate(${fr.left-g.left}px,${fr.top-g.top}px) scale(${fr.width/g.cw},${fr.height/g.ch})`,borderRadius:"60px"}],{duration:520,easing:E,fill:"forwards"});
  const el=V.els[V.i],er={left:parseFloat(el.style.left),top:parseFloat(el.style.top),w:parseFloat(el.style.width)};
  el.animate([{transform:"none",transformOrigin:"0 0"},{transform:`translate(${fr.left-er.left}px,${fr.top-er.top}px) scale(${fr.width/er.w})`,transformOrigin:"0 0"}],{duration:520,easing:E,fill:"forwards"});
  V.els.forEach((x,i)=>{if(i!==V.i)x.animate([{opacity:1},{opacity:0}],{duration:200,fill:"forwards"})});
  $("#vinfo").animate([{opacity:1},{opacity:0}],{duration:160,fill:"forwards"});
  viewer.querySelector(".vbg").animate([{opacity:1},{opacity:0}],{duration:520,easing:E,fill:"forwards"});
  setTimeout(()=>{vcard.getAnimations().forEach(a=>a.cancel());viewer.querySelector(".vbg").getAnimations().forEach(a=>a.cancel());$("#vinfo").getAnimations().forEach(a=>a.cancel());done()},520);
}
$("#vClose").onclick=closeViewer;
$("#vPrev").onclick=()=>{if(V.i>0){V.i--;layoutV();renderVInfo()}};
$("#vNext").onclick=()=>{if(V.i<V.els.length-1){V.i++;layoutV();renderVInfo()}};
addEventListener("keydown",e=>{if(V.open){if(e.key==="Escape")closeViewer();if(e.key==="ArrowRight")$("#vNext").click();if(e.key==="ArrowLeft")$("#vPrev").click()}else if(e.key==="Escape")closeSheet()});
{let x0=null;viewer.addEventListener("touchstart",e=>x0=e.touches[0].clientX,{passive:true});viewer.addEventListener("touchend",e=>{if(x0==null)return;const dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>40)(dx<0?$("#vNext"):$("#vPrev")).click();x0=null})}
addEventListener("resize",()=>{if(V.open)layoutV(true)});

/* ================= account, checkout, packing ================= */
// Sign-in is the Urban Health account itself: the same /api/v1/auth calls and /s/auth.js the app uses (passkey,
// mobile code through Firebase, email code). The order is a real shop order (POST /api/v1/shop/bag/order) priced by
// the server; it shows in Orders in the app. Payment is Razorpay (when it is on) or on delivery, nothing else.
const sheet=$("#sheet"),scrim=$("#scrim");
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const first=n=>String(n||"").trim().split(/\s+/)[0]||"there";
const nicePhone=p=>{const m=String(p||"").match(/^\+91(\d{5})(\d{5})$/);return m?`+91 ${m[1]} ${m[2]}`:String(p||"")};
const ymd=d=>d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
const KEYRE=/^[A-Za-z0-9_-]{16,64}$/;
const rid=(n=18)=>{const a=new Uint8Array(n);crypto.getRandomValues(a);return btoa(String.fromCharCode(...a)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"")};
async function API(path,body,o={}){
  const h={"content-type":"application/json","x-tht":"1"};if(o.key)h["x-dokko-key"]=o.key;
  const r=await fetch("/api/"+path,{method:o.method||(body===undefined?"GET":"POST"),headers:h,credentials:"same-origin",cache:"no-store",body:body===undefined?undefined:JSON.stringify(body)});
  let j={};try{j=await r.json()}catch(e){}
  if(!r.ok){const m=j&&j.detail;const e=new Error(typeof m==="string"?m:"Something went wrong ("+r.status+"). Please try again.");e.status=r.status;throw e}
  return j;
}
const loaded={};
const loadScript=src=>loaded[src]||(loaded[src]=new Promise((res,rej)=>{const s=document.createElement("script");s.src=src;s.onload=res;s.onerror=()=>{delete loaded[src];rej(new Error("Couldn’t load. Check your connection and try again."))};document.head.append(s)}));
const authJs=()=>window.THT&&THT.phone?Promise.resolve():loadScript("/s/auth.js?v=20");

const ACC={user:null,key:"",addrs:[],online:false};
const C={step:0,auth:"in",via:"phone",id:"",name:"",terms:false,flow:"",sent:"",fb:false,newFlow:"",err:"",busy:false,
  addr:"",form:{},same:true,bill:{name:"",line:""},pay:"cod",order:null,token:"",pending:false,resendAt:0};

/* the account's family, linked the same way the app links it (/hello answers with the family's key when it has one) */
async function linked(){
  let k="";try{k=localStorage.getItem("uh-bag-key")||""}catch(e){}
  if(!KEYRE.test(k))k=rid();
  try{const r=await API("v1/hello",{members:0},{key:k});if(r.adoptKey&&KEYRE.test(r.adoptKey))k=r.adoptKey}catch(e){}
  try{localStorage.setItem("uh-bag-key",k)}catch(e){}
  ACC.key=k;
  try{ACC.addrs=((await API("v2/addresses")).rows||[]).filter(a=>a.line1&&a.pin)}catch(e){ACC.addrs=[]}
  if(!C.addr&&ACC.addrs[0])C.addr=ACC.addrs[0].id;
}
function navAccount(){window.uhNav&&uhNav(ACC.user)}
const PK={loaded:false,loading:false,remind:[],items:null,t:0};
function applyLive(info){
  (info.items||[]).forEach(x=>{const it=byId(x.id);if(!it)return;if(typeof x.list==="number")it.list=x.list;it.price=Math.min(x.price,it.list||x.price);it.stock=x.stock||{};it.off=x.active===false});
  LIVE.policy=info.policy||[];LIVE.rate=typeof info.rate==="number"&&info.rate>0&&info.rate<=1?info.rate:1;if(Array.isArray(info.home)&&info.home.length)HOME=info.home;
  ACC.online=!!info.online;C.pay=ACC.online?"online":"cod";
  const fp=$("#faqPay");if(fp)fp.textContent=ACC.online?"Pay online with UPI, a card or netbanking, or pay when the bag arrives. Your receipt appears in the Urban Health app.":"Pay when the bag arrives, by cash or UPI. Your receipt appears in the Urban Health app.";
  const fr=$("#faqRet");if(fr&&LIVE.policy.length)fr.innerHTML=LIVE.policy.map(p=>`<li>${esc(p)}</li>`).join("");
  refresh();if(V.open)renderVInfo();
}
(async()=>{
  const deep=location.hash==="#pack";   // from the week 34 and 36 reminders
  try{const [me,info]=await Promise.all([API("v1/auth/me"),API("v1/shop/bag").catch(()=>null)]);
    if(info)applyLive(info);
    if(me&&me.user){ACC.user=me.user;navAccount();await linked()}else navAccount()
  }catch(e){}
  if(deep){if(ACC.user)openSheet(5);else{C.after=5;openSheet(1)}}
})();
function savePack(extra){if(!ACC.user)return;clearTimeout(PK.t);
  PK.t=setTimeout(()=>API("v1/shop/bag/checklist",Object.assign({packed:S.packed},extra||{}),{method:"PUT"}).then(r=>{PK.remind=r.remind||[]}).catch(()=>{}),extra?0:500)}

function openSheet(st){if(C.step>=4&&st===0){C.order=null;C.token="";C.pending=false}
  C.step=st===1&&ACC.user?2:st;C.err="";sheet.classList.add("open");scrim.classList.add("open");document.body.classList.add("lock");renderSheet()}
function closeSheet(){sheet.classList.remove("open");scrim.classList.remove("open");if(!V.open)document.body.classList.remove("lock")}
scrim.onclick=closeSheet;
const th=it=>`<span class="th">${pic(it)}</span>`;
const fail=m=>{C.err=m;renderSheet();return false};
function busy(on,label){C.busy=on;const c=$("#cta");if(c){c.disabled=on;if(on)c.innerHTML=`<span class="spin"></span>${label||"Please wait"}`}}
const errP=()=>`<p class="err" role="alert">${C.err?esc(C.err):""}</p>`;
const go=s=>{C.step=s;C.err="";renderSheet();$("#shbody").scrollTop=0};

/* ---- sign in / create account ---- */
async function sendCode(){
  if(C.busy)return;
  const raw=($("#aid")?.value||"").trim();C.id=raw;
  if(C.auth==="new"){C.name=($("#aname")?.value||"").replace(/\s+/g," ").trim();if(C.name.length<2)return fail("Please enter your full name.");if(!C.terms)return fail("Please accept the Terms and the Privacy Policy.")}
  let id=raw;
  if(C.via==="phone"){const d=raw.replace(/\D/g,"").replace(/^(91|0)(?=[6-9]\d{9}$)/,"");if(!/^[6-9]\d{9}$/.test(d))return fail("Enter a 10-digit mobile number.");id="+91"+d}
  else if(!/^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(raw))return fail("Enter a valid email address.");
  busy(true,"Sending");
  try{await authJs();const r=await THT.api("/otp/start",{id,purpose:"signin"});
    C.flow=r.flow;C.sent=r.sentTo||id;C.fb=!!r.firebase;C.demo=r.demo||"";
    if(r.firebase)await THT.phone.send(r.phone);
    C.resendAt=Date.now()+45e3;C.err="";
  }catch(e){C.flow="";C.err=e.message}
  busy(false);renderSheet();
}
async function verifyCode(){
  if(C.busy)return;
  const code=($("#code")?.value||"").replace(/\D/g,"");if(code.length!==6)return fail("Enter the 6-digit code.");
  busy(true,"Checking");
  try{const body={flow:C.flow};if(C.fb)body.firebaseToken=await THT.phone.token(code);else body.code=code;
    const r=await THT.api("/otp/verify",body);
    if(r.newAccount){C.newFlow=r.newAccount;C.flow="";if(C.auth==="new"&&C.name&&C.terms)return createAccount();busy(false);C.err="";renderSheet();return}
    if(!r.user)throw new Error("That didn’t work. Ask for a new code.");
    await signedIn(r.user,C.auth==="new");
  }catch(e){busy(false);C.err=e.message;renderSheet()}
}
async function createAccount(){
  const el=$("#aname"),name=(el?el.value:C.name).replace(/\s+/g," ").trim();C.name=name;
  if(name.length<2){busy(false);return fail("Please enter your full name.")}
  if(!C.terms){busy(false);return fail("Please accept the Terms and the Privacy Policy.")}
  busy(true,"Creating your account");
  try{const r=await THT.api("/otp/create",{flow:C.newFlow,name,terms:true});await signedIn(r.user,false,true)}
  catch(e){busy(false);C.err=e.message;renderSheet()}
}
async function passkeyIn(){
  if(C.busy)return;C.err="";
  try{await authJs();const r=await THT.passkey.signin({});await signedIn(r.user)}
  catch(e){if(e.message!=="aborted")fail(e.message)}
}
async function signedIn(u,wanted_new,made){
  ACC.user=u;C.flow="";C.newFlow="";C.err="";navAccount();
  busy(true,"Signing in");await linked();busy(false);
  toast(made?"Welcome to Urban Health, "+first(u.name):wanted_new?"This number already has an account. Welcome back, "+first(u.name):"Signed in as "+first(u.name));
  if(!C.form.name)C.form.name=u.name||"";if(!C.form.phone&&u.phone)C.form.phone=String(u.phone).replace(/^\+91/,"");
  const nx=C.after||2;C.after=0;go(nx);
}
async function signOut(){try{await API("v1/auth/logout",{})}catch(e){}ACC.user=null;ACC.addrs=[];ACC.key="";C.addr="";C.form={};Object.assign(PK,{loaded:false,remind:[],items:null});navAccount();go(1)}

function paneAccount(b){
  if(C.newFlow){
    b.innerHTML=`<div class="pane"><h2>Create your account</h2><p class="lead">Your number is confirmed. What’s your name?</p>
    <label class="fld">Full name<input class="in" id="aname" autocomplete="name" value="${esc(C.name)}"></label>
    <button class="chk" data-terms aria-pressed="${C.terms}"><i>${CHECK}</i><span>I agree to the <a href="/terms" target="_blank" rel="noopener">Terms</a> and the <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a>.</span></button>${errP()}</div>`;
    return ["Create account",createAccount];
  }
  const isNew=C.auth==="new",sent=!!C.flow,left=Math.max(0,Math.ceil((C.resendAt-Date.now())/1e3));
  const idf=C.via==="phone"
    ?`<label class="fld">Mobile number<span class="phn"><span class="cc">+91</span><input class="in" id="aid" inputmode="numeric" autocomplete="tel-national" maxlength="14" placeholder="10-digit number" value="${esc(C.id)}" ${sent?"disabled":""}></span></label>`
    :`<label class="fld">Email<input class="in" id="aid" type="email" autocomplete="email" placeholder="you@example.com" value="${esc(C.id)}" ${sent?"disabled":""}></label>`;
  b.innerHTML=`<div class="pane"><h2>${isNew?"Create your account":"Sign in"}</h2><p class="lead">Use your Urban Health account. Your order, receipt and tracking stay with your family’s records in the app.</p>
  <div class="seg" role="tablist"><button role="tab" aria-selected="${!isNew}" data-auth="in">Sign in</button><button role="tab" aria-selected="${isNew}" data-auth="new">Create account</button></div>
  ${isNew&&!sent?`<label class="fld">Full name<input class="in" id="aname" autocomplete="name" value="${esc(C.name)}"></label>`:""}
  ${idf}
  ${!sent&&!isNew?`<button class="lnk via" data-via>${C.via==="phone"?"Use email instead":"Use mobile number instead"}</button>`:""}
  ${isNew&&!sent?`<button class="chk" data-terms aria-pressed="${C.terms}"><i>${CHECK}</i><span>I agree to the <a href="/terms" target="_blank" rel="noopener">Terms</a> and the <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a>.</span></button>`:""}
  ${sent?`<label class="fld">Enter the 6-digit code sent to ${esc(C.sent)}<input class="in code" id="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="••••••"></label>
   <div class="cline"><button class="lnk" data-change>Change ${C.via==="phone"?"number":"email"}</button><button class="lnk" data-resend ${left?"disabled":""}>${left?`Send again in ${left}s`:"Send again"}</button></div>${C.demo?`<p class="note">Test code: ${esc(C.demo)}</p>`:""}`:""}
  ${errP()}
  ${!isNew&&!sent&&window.PublicKeyCredential?`<div class="or">or</div><button class="alt" id="passkey"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1D1D1F" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="8" r="4"/><path d="M3 21a6 6 0 0 1 12 0M17 11a2.5 2.5 0 1 1 2.5 2.5V20l-1.5 1-1-1.5 1-1-1-1 1-1"/></svg>Sign in with a passkey</button>`:""}</div>`;
  $$("[data-auth]",b).forEach(x=>x.onclick=()=>{C.auth=x.dataset.auth;C.via="phone";C.flow="";C.err="";renderSheet()});
  const v=$("[data-via]",b);if(v)v.onclick=()=>{C.via=C.via==="phone"?"email":"phone";C.id="";C.err="";renderSheet()};
  const ch=$("[data-change]",b);if(ch)ch.onclick=()=>{C.flow="";C.err="";renderSheet()};
  const rs_=$("[data-resend]",b);if(rs_)rs_.onclick=()=>{if(rs_.disabled)return;C.flow="";sendCode()};
  if($("#passkey",b))$("#passkey",b).onclick=passkeyIn;
  clearInterval(C.tick);
  if(left&&sent)C.tick=setInterval(()=>{const btn=$("[data-resend]");if(!btn){clearInterval(C.tick);return}const n=Math.max(0,Math.ceil((C.resendAt-Date.now())/1e3));btn.disabled=!!n;btn.textContent=n?`Send again in ${n}s`:"Send again";if(!n)clearInterval(C.tick)},1000);
  const cd=$("#code",b);if(cd){cd.oninput=()=>{cd.value=cd.value.replace(/\D/g,"").slice(0,6);if(cd.value.length===6)verifyCode()};setTimeout(()=>cd.focus(),60)}
  const ai=$("#aid",b);if(ai&&!sent)ai.onkeydown=e=>{if(e.key==="Enter")sendCode()};
  return sent?["Verify",verifyCode]:["Send code",sendCode];
}

/* ---- delivery ---- */
const STATES=["Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Andaman and Nicobar Islands","Chandigarh","Dadra and Nagar Haveli and Daman and Diu","Delhi","Jammu and Kashmir","Ladakh","Lakshadweep","Puducherry"];
const savedAddr=()=>ACC.addrs.find(a=>a.id===C.addr);
const shortAddr=a=>[a.line1,a.line2,a.area,a.city].filter(Boolean).join(", ")+(a.pin?" "+a.pin:"");
function addrBody(){const a=savedAddr();if(a&&a.name&&a.phone)return {id:a.id};const f=C.form;return {name:f.name||"",phone:f.phone||"",line1:f.line1||"",line2:f.line2||"",landmark:f.landmark||"",city:f.city||"",state:f.state||"",pin:f.pin||""}}
function checkAddr(){
  if(!C.same&&(C.bill.name.trim().length<2||C.bill.line.trim().length<8))return fail("Enter the billing name and address.");
  const a=savedAddr();if(a&&a.name&&a.phone)return true;
  const f=C.form,ph=String(f.phone||"").replace(/\D/g,"").replace(/^(91|0)(?=[6-9]\d{9}$)/,"");
  if(String(f.name||"").trim().length<2)return fail("Enter the name of the person receiving the bag.");
  if(!/^[6-9]\d{9}$/.test(ph))return fail("Enter a 10-digit mobile number for the delivery.");
  if(!/^[1-9]\d{5}$/.test(f.pin||""))return fail("PIN code is 6 digits.");
  if(!String(f.line1||"").trim())return fail("Enter the flat or house number.");
  if(String(f.line2||"").trim().length<3)return fail("Enter the building, street and area.");
  if(String(f.city||"").trim().length<2)return fail("Enter the city.");
  return true;
}
function paneDelivery(b){
  const ds=delDates(),u=ACC.user||{},sa=savedAddr(),useSaved=sa&&sa.name&&sa.phone,f=C.form;
  const inp=(k,label,attrs="")=>`<label class="fld">${label}<input class="in" data-f="${k}" value="${esc(f[k]||"")}" ${attrs}></label>`;
  b.innerHTML=`<div class="pane"><h2>Delivery</h2><p class="lead">We suggest a day before week 36, so the bag is ready early.</p>
  <div class="who"><span class="av">${esc(first(u.name).charAt(0).toUpperCase())}</span><span><b>${esc(u.name||"")}</b><small>${esc(nicePhone(u.phone)||u.email||"")}</small></span><button class="lnk" data-out>Sign out</button></div>
  ${ACC.addrs.length?`<div class="fld">Deliver to<div class="chs">${ACC.addrs.map(a=>`<button data-addr="${esc(a.id)}" aria-pressed="${C.addr===a.id}">${esc(a.label||"Saved")}</button>`).join("")}<button data-addr="" aria-pressed="${!C.addr}">New address</button></div></div>`:""}
  ${useSaved?`<div class="acard"><b>${esc(sa.name)}</b><span>${esc(nicePhone(sa.phone))}</span><span>${esc(shortAddr(sa))}</span></div>`:
  `${inp("name","Receiver’s name",'autocomplete="name"')}
   <label class="fld">Mobile<span class="phn"><span class="cc">+91</span><input class="in" data-f="phone" inputmode="numeric" autocomplete="tel-national" maxlength="14" value="${esc(f.phone||"")}"></span></label>
   ${inp("line1","Flat or house number, floor",'autocomplete="address-line1"')}
   ${inp("line2","Building, street and area",'autocomplete="address-line2"')}
   <div class="row2">${inp("pin","PIN code",'inputmode="numeric" maxlength="6" autocomplete="postal-code"')}${inp("city","City",'autocomplete="address-level2"')}</div>
   ${inp("state","State",'list="uhstates" autocomplete="address-level1"')}
   <datalist id="uhstates">${STATES.map(s=>`<option value="${s}">`).join("")}</datalist>`}
  <div class="fld">Delivery day<div class="days">${ds.map((x,i)=>`<button class="day" data-date="${i}" aria-pressed="${S.date===i}"><small>${x.d.toLocaleDateString("en-IN",{weekday:"short"})}</small><b>${x.d.toLocaleDateString("en-IN",{day:"numeric",month:"short"})}</b><span>${x.t}</span></button>`).join("")}</div></div>
  <button class="sw" data-same aria-pressed="${C.same}"><span><b>Bill to the delivery address</b><span>The receipt shows this name and address</span></span><i class="tgl"></i></button>
  ${C.same?"":`<label class="fld">Billing name<input class="in" data-b="name" autocomplete="billing name" value="${esc(C.bill.name)}"></label><label class="fld">Billing address<input class="in" data-b="line" autocomplete="billing street-address" value="${esc(C.bill.line)}"></label>`}
  ${errP()}</div>`;
  $$("[data-f]",b).forEach(x=>x.oninput=()=>{let v=x.value;if(x.dataset.f==="pin")v=x.value=v.replace(/\D/g,"").slice(0,6);C.form[x.dataset.f]=v});
  $$("[data-b]",b).forEach(x=>x.oninput=()=>{C.bill[x.dataset.b]=x.value});
  $$("[data-addr]",b).forEach(x=>x.onclick=()=>{C.addr=x.dataset.addr;const a=savedAddr();if(a&&!(a.name&&a.phone)){Object.assign(C.form,{name:a.name||u.name||"",phone:String(a.phone||u.phone||"").replace(/^\+91/,""),line1:a.line1,line2:a.line2,city:a.city,state:a.state,pin:a.pin});C.addr=""}C.err="";renderSheet()});
  $$("[data-date]",b).forEach(x=>x.onclick=()=>{S.date=+x.dataset.date;renderMeta();renderSheet()});
  $("[data-same]",b).onclick=()=>{C.same=!C.same;renderSheet()};
  $("[data-out]",b).onclick=signOut;
  return ["Continue to payment",()=>{if(checkAddr())go(3)}];
}

/* ---- payment ---- */
function panePayment(b){
  const t=totals(),sa=savedAddr(),a=sa&&sa.name&&sa.phone?sa:C.form,day=fmt(delDates()[S.date].d);
  if(C.pending&&C.order){
    b.innerHTML=`<div class="pane"><h2>Finish paying</h2><p class="lead">Order <b class="mono">UH-${esc(C.order.id)}</b> is saved. Pay ${rs(C.order.total)} now, or pay when the bag arrives.</p>${errP()}
    <button class="alt" id="podi">Pay on delivery instead</button></div>`;
    $("#podi",b).onclick=async()=>{try{const r=await API(`v1/shop/bag/orders/${encodeURIComponent(C.order.id)}/cod`,{});C.order=r.order;C.pending=false;C.pay="cod";done()}catch(e){fail(e.message)}};
    return ["Try again",()=>{C.err="";busy(true,"Opening");payOnline()},"Your order is saved"];
  }
  const P=(ACC.online?[["online","Pay now","UPI, cards or netbanking, secured by Razorpay"]]:[]).concat([["cod","Pay on delivery","Cash or UPI when the bag arrives"]]);
  if(!P.some(p=>p[0]===C.pay))C.pay=P[0][0];
  b.innerHTML=`<div class="pane"><h2>Payment</h2>
  <div class="acard"><span>Delivering to <b>${esc(a.name||"")}</b>, ${esc(shortAddr(a))}</span><span>on <b>${day}</b> · <button class="lnk" data-back>Change</button></span></div>
  ${P.map(p=>`<button class="pay" data-pay="${p[0]}" aria-pressed="${C.pay===p[0]}"><span class="rd"></span><span><b>${p[1]}</b><span>${p[2]}</span></span></button>`).join("")}
  <div class="bill"><div><span>${t.units} items at brand prices</span><span>${rs(t.full)}</span></div>${t.save?`<div><span>Offer · ${t.off}% off</span><span class="ok">−${rs(t.save)}</span></div>`:""}<div><span>Delivery</span><span>Free</span></div><div class="tot"><span>Total</span><span>${rs(t.total)}</span></div></div>
  ${LIVE.policy.length?`<details class="pol"><summary>Returns and refunds</summary><ul>${LIVE.policy.map(p=>`<li>${esc(p)}</li>`).join("")}</ul><a class="more" href="/hospital-bag/policies" target="_blank" rel="noopener">Read the full policy</a></details>`:""}
  ${errP()}<p class="note">Your receipt and tracking will be in Orders in the Urban Health app.</p></div>`;
  $$("[data-pay]",b).forEach(x=>x.onclick=()=>{C.pay=x.dataset.pay;C.err="";renderSheet()});
  $("[data-back]",b).onclick=()=>go(2);
  return [C.pay==="cod"?"Place order":"Pay "+rs(t.total),placeOrder,C.pay==="cod"?"Pay when it arrives":"Secure payment"];
}
async function placeOrder(){
  if(C.busy)return;
  if(!ACC.user)return go(1);
  if(!C.token)C.token=rid(12);
  const items={},opts={};
  ITEMS.forEach(i=>{if(S.q[i.id]>0){items[i.id]=S.q[i.id];if(i.opts)opts[i.id]=i.opts[optIdx(i)]}});
  busy(true,C.pay==="online"?"Opening payment":"Placing order");C.err="";
  try{
    if(!ACC.key)await linked();
    const r=await API("v1/shop/bag/order",{token:C.token,items,opts,twins:S.twins,deliverOn:ymd(delDates()[S.date].d),addr:addrBody(),
      bill:C.same?{same:true}:{same:false,name:C.bill.name,line:C.bill.line},payment:C.pay},{key:ACC.key});
    C.order=r.order;if(r.key&&KEYRE.test(r.key)){ACC.key=r.key;try{localStorage.setItem("uh-bag-key",r.key)}catch(e){}}
    if(C.pay==="online"&&!String(C.order.payment).endsWith("paid"))return payOnline();
    done();
  }catch(e){busy(false);if(e.status===401){ACC.user=null;navAccount();C.step=1}C.err=e.message;renderSheet()}
}
async function payOnline(){
  try{
    const st=await API("v1/pay/online/start",{kind:"order",orderId:C.order.id},{key:ACC.key});
    await loadScript("https://checkout.razorpay.com/v1/checkout.js");
    const u=ACC.user||{};
    const rz=new Razorpay({key:st.keyId,amount:st.amount,currency:st.currency||"INR",name:"Urban Health",description:st.description||"Hospital bag",order_id:st.orderId,
      prefill:{name:u.name||"",contact:u.phone||"",email:u.email||""},theme:{color:"#0071E3"},
      handler:async p=>{try{await API("v1/pay/online/verify",{payment:st.payment,razorpay_order_id:p.razorpay_order_id,razorpay_payment_id:p.razorpay_payment_id,razorpay_signature:p.razorpay_signature},{key:ACC.key});
        C.order.payment="online-paid";C.pending=false;done()}catch(e){C.pending=true;C.step=3;busy(false);C.err=e.message;renderSheet()}},
      modal:{ondismiss:()=>{if(String(C.order.payment).endsWith("paid"))return;C.pending=true;C.step=3;busy(false);renderSheet()}}});
    if(rz.on)rz.on("payment.failed",r=>{C.err=(r&&r.error&&r.error.description)||"The payment didn’t go through. No money was taken."});
    rz.open();
  }catch(e){C.pending=true;C.step=3;busy(false);C.err=e.message;renderSheet()}
}
function done(){busy(false);C.pending=false;C.err="";C.step=4;renderSheet();if(window.B3&&B3.ok)B3.bump();
  API("v1/shop/bag/checklist",{packed:S.packed,remind:true,due:S.due},{method:"PUT"}).then(r=>{PK.loaded=true;PK.remind=r.remind||[];PK.items=r.items&&r.items.length?r.items:null;if(C.step===4)renderSheet()}).catch(()=>{})}

/* ---- the sheet ---- */
function renderSheet(){
  const t=totals(),b=$("#shbody"),f=$("#shfoot"),prog=$("#prog");f.classList.remove("two");
  const foot=(lbl,act,sub)=>{f.innerHTML=`<div class="tt"><small>${sub||t.units+" items · free delivery"}</small><b>${rs(C.order&&C.step>=3?C.order.total:t.total)}</b></div><button class="cta" id="cta">${lbl}</button>`;$("#cta").onclick=act;if(C.busy)busy(true)};
  prog.style.visibility=C.step<4?"visible":"hidden";
  [...prog.children].forEach((x,i)=>x.classList.toggle("on",i<=C.step));
  if(C.step===0){
    const groups=Object.keys(CAT).map(k=>{const ls=catItems(k).filter(i=>S.q[i.id]>0);if(!ls.length)return"";
      return `<div class="grp"><h4>${CAT[k].label} · ${ls.length}</h4>${ls.map(i=>`<div class="ln">${th(i)}<div class="n"><b>${i.name}</b><span>${i.brand} · ${price(i)}${i.list>i.price?` <s>${rs(i.list)}</s>`:""}${i.opts?" · "+i.opts[optIdx(i)].replace(/ /g,"\u00a0"):""}</span></div>${stepper(i.id,S.q[i.id]).replace(/data-inc/g,"data-sinc").replace(/data-dec/g,"data-sdec")}</div>`).join("")}</div>`}).join("");
    b.innerHTML=`<div class="pane"><h2>Your bag</h2><p class="lead">${!t.units?"Your bag is empty. Add a few things first.":(t.complete?`All ${ESS} essentials are in, from Mee Mee, SuperBottoms and Pee Safe.`:"Every item comes sealed in its maker’s own pack.")+(t.save?` As a bag, you save ${rs(t.save)}.`:"")}</p>${groups}</div>`;
    $$("[data-sinc]",b).forEach(x=>x.onclick=()=>{const id=x.dataset.sinc;if(!canAdd(id))return;S.man[id]=(S.man[id]||0)+1;compute();renderRow(id);renderMeta();syncBag();renderSheet()});
    $$("[data-sdec]",b).forEach(x=>x.onclick=()=>{const id=x.dataset.sdec;S.man[id]=(S.man[id]||0)-1;compute();renderRow(id);renderMeta();syncBag();renderSheet()});
    foot("Continue",()=>{if(!t.units)return closeSheet();go(ACC.user?2:1)});
    if(!t.units)$("#cta").textContent="Back to my bag";
  }else if(C.step===1){
    if(ACC.user){C.step=2;return renderSheet()}
    const [l,a]=paneAccount(b);foot(l,a);
  }else if(C.step===2){
    if(!ACC.user){C.step=1;return renderSheet()}
    const [l,a]=paneDelivery(b);foot(l,a);
  }else if(C.step===3){
    if(!ACC.user&&!C.pending){C.step=1;return renderSheet()}
    const [l,a,s]=panePayment(b);foot(l,a,s);
  }else if(C.step===4){
    const o=C.order||{},paid=String(o.payment||"").endsWith("paid"),steps=o.steps||["Order placed","Confirmed","Packed","Shipped","Delivered"],at=Math.max(0,o.step||0);
    const day=o.eta?fmt(new Date(o.eta*1000)):fmt(delDates()[S.date].d);
    b.innerHTML=`<div class="pane done"><div class="okc"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l4 4 10-10"/></svg></div>
    <h2>Order placed</h2><p class="lead" style="margin:0">Your bag arrives by <b style="color:var(--ink)">${day}</b>.</p>
    <p class="note">Order <span class="mono">UH-${esc(o.id||"")}</span> · ${rs(o.total||t.total)} · ${paid?"paid online":"pay when it arrives"}</p>
    <div class="track">${steps.map((s,i,a)=>{const st=i<at||i===0?"ok":i===at?"now":"";return `<div class="trk ${st}"><div class="c"><i>${st==="ok"?CHECK:""}</i>${i<a.length-1?"<u></u>":""}</div><b style="${st?"":"color:var(--ink2);font-weight:500"}">${esc(s)}</b></div>`}).join("")}</div>
    <p class="note">We’ve sent the details to your Urban Health inbox. Track it any time in Orders.${PK.remind.length?` We’ll remind you to pack at week${PK.remind.length>1?"s":""} ${PK.remind.map(r=>r.week).join(" and ")}.`:""}</p></div>`;
    f.classList.add("two");f.innerHTML=`<button class="btn sec" id="pk">Packing checklist</button><a class="cta" href="/app#page=orders">Track in the app</a>`;$("#pk").onclick=()=>{C.step=5;renderSheet()};
  }else{
    if(ACC.user&&!PK.loaded&&!PK.loading){PK.loading=true;API("v1/shop/bag/checklist").then(r=>{PK.loaded=true;PK.loading=false;PK.remind=r.remind||[];PK.items=r.items&&r.items.length?r.items:null;
      S.packed=Object.assign({},r.packed||{},S.packed);if(C.step===5)renderSheet()}).catch(()=>{PK.loading=false;PK.loaded=true})}
    const ls=(PK.items?PK.items.map(x=>({it:byId(x.id),q:x.qty})):ITEMS.filter(i=>S.q[i.id]>0).map(it=>({it,q:S.q[it.id]}))).filter(x=>x.it);
    const home=[...S.own].map(id=>({id,name:byId(id).name,it:byId(id)})).concat(HOME.map(([id,name])=>({id,name})));
    const all=ls.length+home.length,dn=ls.filter(x=>S.packed[x.it.id]).length+home.filter(x=>S.packed[x.id]).length,pc=Math.round(dn*100/Math.max(1,all));
    const pk=(id,name,it)=>`<button class="pk" data-k="${id}" aria-pressed="${!!S.packed[id]}"><span class="r"></span>${it?th(it):""}<b>${name}</b></button>`;
    b.innerHTML=`<div class="pane"><div style="display:flex;align-items:center;gap:18px;margin:6px 0 16px"><svg width="76" height="76" viewBox="0 0 100 100" role="img" aria-label="${pc}% packed"><circle cx="50" cy="50" r="42" fill="none" stroke="#E8E8ED" stroke-width="9"/><circle cx="50" cy="50" r="42" fill="none" stroke="#FF375F" stroke-width="9" stroke-linecap="round" stroke-dasharray="264" stroke-dashoffset="${264-264*pc/100}" transform="rotate(-90 50 50)" style="transition:stroke-dashoffset .6s var(--ease)"/><text x="50" y="57" text-anchor="middle" font-size="21" font-weight="600" fill="#1D1D1F">${pc}%</text></svg><div><h2 style="margin:0">Packing checklist</h2><p class="lead" style="margin:4px 0 0">Tick things off as they go in the bag.</p></div></div>
    ${ACC.user?`<button class="sw rem" data-rem aria-pressed="${!!PK.remind.length}"><span><b>Remind me to pack</b><span>${PK.remind.length?PK.remind.map(r=>`Week ${r.week} · ${fmt(new Date(r.on+"T12:00:00"))}`).join(" and "):"At weeks 34 and 36, in your Urban Health inbox"}</span></span><i class="tgl"></i></button>`
      :`<p class="keep">Sign in to keep this list in your account. <button class="lnk" data-keep>Sign in</button></p>`}
    <div class="grp"><h4>In the bag we deliver</h4>${ls.map(x=>pk(x.it.id,x.it.name+(x.q>1?" × "+x.q:""),x.it)).join("")}</div>
    <div class="grp"><h4>From home</h4>${home.map(x=>pk(x.id,x.name,x.it)).join("")}</div></div>`;
    $$("[data-k]",b).forEach(x=>x.onclick=()=>{S.packed[x.dataset.k]=!S.packed[x.dataset.k];if(!S.packed[x.dataset.k])delete S.packed[x.dataset.k];navigator.vibrate&&navigator.vibrate(8);const st=b.scrollTop;renderSheet();b.scrollTop=st;saveBag();savePack();renderHome()});
    const rm=$("[data-rem]",b);if(rm)rm.onclick=()=>{const on=!PK.remind.length;rm.setAttribute("aria-pressed",on);
      API("v1/shop/bag/checklist",{packed:S.packed,remind:on,due:S.due},{method:"PUT"}).then(r=>{PK.remind=r.remind||[];if(on&&!PK.remind.length)toast("Weeks 34 and 36 have already passed for your due date");else toast(on?"We’ll remind you to pack":"Reminders off");renderSheet()}).catch(e=>{toast(e.message);renderSheet()})};
    const kp=$("[data-keep]",b);if(kp)kp.onclick=()=>{C.after=5;go(1)};
    f.innerHTML=`<div class="tt"><small>${dn} of ${all} packed</small><b>${pc===100?"Ready to go":"Keep going"}</b></div><button class="cta" data-close>Done</button>`;
  }
  const tm=$("[data-terms]",b);if(tm)tm.onclick=e=>{if(e.target.closest("a"))return;C.terms=!C.terms;tm.setAttribute("aria-pressed",C.terms)};
}

/* ================= the one 3D stage ================= */
/* the price bar appears once the price at the top has scrolled away, so the two never show together */
new IntersectionObserver(es=>es.forEach(e=>$("#sumbar").classList.toggle("show",!e.isIntersecting&&e.boundingClientRect.top<60)),{rootMargin:"-52px 0px 0px 0px"}).observe($(".intro .price"));
function stageDist(){const h=$("#buildBag").clientHeight||500;return 8.2*Math.max(1,Math.pow(520/Math.max(280,h),.35))}
window.onB3Ready=()=>{B3.mount($("#buildBag"),stageDist(),1.0);B3.sync(desired(),true)};
window.onThumbs=()=>{renderConfig();renderMeta()};
addEventListener("resize",()=>{if(window.B3&&B3.ok)B3.mount($("#buildBag"),stageDist(),1.0);if(V.open)layoutV(true)});
setTimeout(()=>{if(!window.THUMB["mm-bra"]){window.NO3D=true;window.onThumbs();const h=$("#buildBag");if(!h.querySelector("canvas"))h.innerHTML=bagSVG()}},6000);

/* ================= boot ================= */
// an unfinished bag stays on this device for 60 days, so leaving the page never loses it
const SAVEK="uh-bag-v1";
function saveBag(){clearTimeout(saveBag.t);saveBag.t=setTimeout(()=>{try{localStorage.setItem(SAVEK,JSON.stringify({t:Date.now(),due:S.due,plan:S.plan,twins:S.twins,start:S.start,hosp:[...S.hosp],
  travel:S.travel,man:S.man,own:[...S.own],vr:S.vr,winterAdd:S.winterAdd,date:S.date,packed:S.packed}))}catch(e){}},300)}
function loadBag(){try{const o=JSON.parse(localStorage.getItem(SAVEK)||"null");if(!o||Date.now()-o.t>60*DAY)return;
  if(o.due&&new Date(o.due)>today)S.due=o.due;
  Object.assign(S,{plan:o.plan||S.plan,twins:!!o.twins,start:o.start||S.start,travel:!!o.travel,man:o.man||{},vr:o.vr||{},winterAdd:!!o.winterAdd,date:[0,1,2].includes(o.date)?o.date:S.date,packed:o.packed||{}});
  S.hosp=new Set(o.hosp||[]);S.own=new Set(o.own||[])}catch(e){}}
loadBag();compute();renderConfig();renderMeta();
