// ===================== live layer 25: share the doctor summary by link (expires), see and revoke shared links =====================
{
const P=SX.p,S=SX.S;
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1','x-dokko-key':(S.key||'')},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status});return j});
const fmt=t=>new Date(t*1000).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'});
let links=[];
const load=()=>{if(!SX.user)return;J('/summary/share').then(r=>{links=r||[];if(page==='dash')render()}).catch(()=>{})};
// the app's own summary builder hands us its HTML when asked (p25 patches the print path)
function grab(m){let html='';SX.__summaryGrab=h=>{html=h};try{SX.act.summary([m.id])}finally{SX.__summaryGrab=null}return html}
SX.act.sumshare=async([hours])=>{const m=SX.me();if(!SX.user){toast(P('Sign in to share a link'));return}const html=grab(m);if(!html){toast(P('Could not build the summary'));return}
 try{const r=await J('/summary/share','POST',{member:m.id,name:m.name,label:P('Doctor summary')+' · '+m.name,html,hours:+hours||48});SX.ledger('summary',true,P('Summary link shared for')+' '+m.name+' · '+P('expires')+' '+fmt(r.expires),m.id);SX.save();load();
  SX.modal(`<h2>${P('Link ready')}</h2><p class="mute sm">${P('Anyone with this link can read')} ${E(m.name.split(' ')[0])}${P('’s summary until')} <b>${fmt(r.expires)}</b>. ${P('You can end it any time from Home → For the doctor.')}</p><input id="lv25url" readonly value="${E(r.url)}" style="width:100%"><div class="lv-row-end" style="margin-top:10px"><button class="btn s" data-sx="closeModal">${P('Close')}</button><a class="btn s" href="https://wa.me/?text=${encodeURIComponent(P('Health summary for')+' '+m.name+': '+r.url)}" target="_blank" rel="noopener">WhatsApp</a><button class="btn p" id="lv25copy">${P('Copy link')}</button></div>`,{label:P('Share')});
  document.getElementById('lv25copy').onclick=async()=>{try{if(navigator.share)await navigator.share({title:P('Health summary'),url:r.url});else{await navigator.clipboard.writeText(r.url);toast(P('Link copied'))}}catch(e){try{await navigator.clipboard.writeText(r.url);toast(P('Link copied'))}catch(_){}}}}
 catch(e){toast(e.message)}};
SX.act.sumrevoke=async([tok])=>{try{await J('/summary/share/'+encodeURIComponent(tok),'DELETE');toast(P('Link ended'));load()}catch(e){toast(e.message)}};
SX.act.sumpick=()=>{const m=SX.me();SX.modal(`<h2>${P('Share with a doctor')}</h2><p class="mute sm">${P('A link to')} ${E(m.name.split(' ')[0])}${P('’s one-page summary. It stops working by itself.')}</p><div class="lv25-opts"><button class="btn p" data-sx="sumshare:48">${P('48 hours')} <small>${P('for a visit')}</small></button><button class="btn s" data-sx="sumshare:168">${P('7 days')} <small>${P('for a second opinion')}</small></button><button class="btn s" data-sx="summary:${E(m.id)}">${P('Print instead')}</button></div><div class="lv-row-end"><button class="btn s" data-sx="closeModal">${P('Cancel')}</button></div>`,{label:P('Share')})};
SX.extend('dash',{after(){const m=SX.me();const mine=links.filter(l=>l.member===m.id);
 return `<div class="card lv25-card"><div class="hd"><div><h3>${P('Share with a doctor')}</h3><small class="mute">${P('A link to the one-page summary that expires by itself — nothing to download, nothing to print.')}</small></div></div><div class="lv25-row"><button class="btn p sm" data-sx="sumpick">${P('Share a link')}</button><button class="btn s sm" data-sx="summary:${E(m.id)}">${P('Print')}</button></div>
  ${mine.length?`<div class="lv25-links">${mine.map(l=>`<div class="lv25-link"><div class="grow"><b>${P('Active link')}</b><small>${P('till')} ${fmt(l.expires)} · ${l.views} ${P('views')}</small></div><button class="btn s sm" data-sx="sumrevoke:${E(l.token)}">${P('End')}</button></div>`).join('')}</div>`:''}</div>`}});
setTimeout(load,2500);
}
