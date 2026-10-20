// ===================== live layer 26: "backed up" — the proof a family wants, and a copy by email =====================
{
const P=SX.p,S=SX.S;
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1','x-dokko-key':(S.key||'')},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status});return j});
let B=null;
const load=()=>{if(S.demo||!S.key)return;J('/backup/status').then(r=>{B=r;if(page==='data'||page==='dash')render()}).catch(()=>{})};
const fmt=t=>new Date(t*1000).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'});
const lastSync=()=>{try{const m=SX.sync&&SX.sync.meta&&SX.sync.meta();return m&&m.t?m.t:null}catch(e){return null}};
function card(full){const docs=(S.vault||[]).length,ls=lastSync();
 const l1=S.demo?P('Demo: nothing is saved'):ls?P('Record synced')+' · '+new Date(ls).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'}):SX.user?P('Record syncs when you are online'):P('Sign in so the record is kept on the server too');
 const l2=B&&B.lastEmail?P('Copy emailed')+' '+fmt(B.lastEmail)+' · '+P('next on')+' '+fmt(new Date(B.nextEmail).getTime()/1000):B&&B.willEmail&&B.willEmail.length?P('A copy goes to')+' '+E(B.willEmail[0])+' '+P('on the 1st of every month'):B?P('Verify your email to get a monthly copy'):'';
 return `<div class="card lv26"><div class="lv26-row"><div class="lv26-ic ${ls||S.demo?'ok':''}">${SX.ico?SX.ico('shield'):'🛡️'}</div><div class="grow"><b>${P('Backed up')}</b><small>${l1}</small>${l2?`<small>${l2}</small>`:''}<small>${docs} ${P('documents in the vault')}</small></div>${full?'':`<button class="btn s sm" data-sx="tab:data">${P('Details')}</button>`}</div>
  ${full?`<div class="lv26-acts"><button class="btn p sm" data-sx="bkpsend">${P('Email me a copy now')}</button><button class="btn s sm" data-sx="export:1">${P('Download everything')}</button></div>`:''}</div>`}
SX.extend('data',{before(){return card(true)}});
SX.extend('dash',{after(){return card(false)}});
SX.act.bkpsend=async()=>{if(!SX.user){toast(P('Sign in first'));return}toast(P('Sending…'));try{const r=await J('/backup/send','POST',{});B=r;toast(P('Sent to')+' '+(r.to||[]).join(', '));render()}catch(e){toast(e.message)}};
setTimeout(load,2000);
}
