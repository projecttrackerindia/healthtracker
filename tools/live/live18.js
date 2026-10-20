// ===================== live layer 18: reference-board theme — SOS in the app bar, the assistant's orb screen =====================
{
const P=SX.p,S=SX.S;
const phone=()=>matchMedia('(max-width:720px)').matches;
// the Health Card banner is optional now (the lock-screen card is the native app's job); SOS lives in the bar
if(S.hcBannerDefaulted!==2){S.hcBanner=false;S.hcBannerDefaulted=2}
function sosBtn(){if(!phone())return;const tb=document.querySelector('.topb');if(!tb||document.getElementById('lv18sos'))return;const b=document.createElement('button');b.id='lv18sos';b.type='button';b.dataset.sx='sos';b.setAttribute('aria-label',P('SOS: emergency help'));b.textContent='SOS';tb.appendChild(b)}
// the assistant opens on an orb and a question, like the boards, until the first message
function orb(){if(!phone()||page!=='assist')return;const chat=document.getElementById('lv5chat');if(!chat||chat.querySelector('.bub')||document.getElementById('lv18orb'))return;const m=SX.me();
 chat.innerHTML=`<div id="lv18orb"><div class="orb"></div><small>${P('Hello')} ${E((m?m.name:'').split(' ')[0])}</small><b>${P('How can I help you today?')}</b></div>`}
new MutationObserver(()=>{sosBtn();orb()}).observe(document.getElementById('page'),{childList:true,subtree:false});
new MutationObserver(()=>setTimeout(()=>{sosBtn();orb()},0)).observe(document.body,{attributes:true,attributeFilter:['data-page']});
setTimeout(()=>{sosBtn();orb()},500);
}
