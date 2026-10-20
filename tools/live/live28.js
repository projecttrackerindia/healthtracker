// ===================== live layer 28: Hindi and Telugu — the core by hand (inline), the rest from the phrase table =====================
{
const P=SX.p,S=SX.S;
const ls=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){return null}};
// the hand-written core ships inside the page, so the first paint in Hindi/Telugu never waits for the network
SX.addPhrases(/*LV28_CORE*/{}/*/LV28_CORE*/);
let loaded=false;
async function table(){if(loaded)return;try{const c=ls('tht.i18n');if(c){SX.addPhrases(JSON.parse(c));loaded=true}}catch(e){}
 try{const r=await fetch('/api/v1/i18n',{cache:'force-cache'});if(r.ok){const j=await r.json();SX.addPhrases(j);ls('tht.i18n',JSON.stringify(j));loaded=true}}catch(e){}}
// switching language loads the table first, then re-renders; the choice is remembered on the device as well as in the record
const lang0=SX.act.lang;SX.act.lang=async([k])=>{ls('tht.lang',k);if(k!=='en')await table();lang0([k]);try{render()}catch(e){}};
if(S.lang&&S.lang!=='en')table().then(()=>{try{render();if(SX.paintNav)SX.paintNav()}catch(e){}});
// a language choice on the sign-in / first screens, where parents start
SX.extend('set',{before(){return `<div class="card lv28"><div class="hd"><div><h3>${P('Language')}</h3><small class="mute">${P('Hindi and Telugu cover the everyday screens; medical guidance stays in English until a doctor has reviewed each translation.')}</small></div></div><div class="lv28-langs">${[['en','English'],['hi','हिन्दी'],['te','తెలుగు']].map(([k,t])=>`<button class="btn ${S.lang===k||(!S.lang&&k==='en')?'p':'s'} sm" data-sx="lang:${k}">${t}</button>`).join('')}</div></div>`}});
SX.lv28={table};
}
