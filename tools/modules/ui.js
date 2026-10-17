// ===================== DoKKo NX: motion & flow layer =====================
(()=>{
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const root=document.documentElement,nav=$('#nav');
// ---- sliding nav indicator ----
const ind=document.createElement('i');ind.className='nx-ind';nav.prepend(ind);
function moveInd(instant){const b=nav.querySelector('button.on');if(!b){ind.style.opacity=0;return}ind.style.opacity=1;if(instant)ind.style.transition='none';ind.style.transform=`translateY(${b.offsetTop}px)`;ind.style.height=b.offsetHeight+'px';if(instant){ind.offsetWidth;ind.style.transition=''}}
new ResizeObserver(()=>moveInd(true)).observe(nav);
// ---- page enter / tab swap animations ----
let entering=false,lastKey='';
function stagger(el){[...el.children].forEach((c,i)=>c.style.setProperty('--i',Math.min(i,8)))}
function play(el,cls,ms){if(reduce)return;el.classList.remove('nx-enter','nx-swap');void el.offsetWidth;el.classList.add(cls);clearTimeout(el._nx);el._nx=setTimeout(()=>el.classList.remove(cls),ms)}
const _render=render;
render=function(...a){const r=_render.apply(this,a),pg=$('#page'),key=page+'|'+(page==='preg'&&typeof PS!=='undefined'?PS.tab:'');
 if(entering){stagger(pg);play(pg,'nx-enter',1100)}
 else if(lastKey&&key!==lastKey&&lastKey.split('|')[0]===page){// same page, new tab: animate only the changing content
  const kids=[...pg.children],t=kids.find(k=>k.querySelector&&k.querySelector('.ptabs'));if(t){[...t.children].slice(1).forEach(c=>c.classList.add('nx-swap-t'));play(pg,'nx-swap',600)}}
 lastKey=key;return r};
// ---- stage cross-fade when switching between anatomy / heart / pregnancy stages ----
const stages=['#stage','#pstage','#hstage'].map(s=>$(s));
const visStage=()=>stages.find(s=>s&&!s.hidden);
const _go=go;
go=function(p,opt){const before=visStage(),prevPage=page;entering=p!==prevPage||!!(opt&&opt.force);const r=_go.call(this,p,opt||{});entering=false;
 const after=visStage();if(after&&after!==before&&!reduce){after.classList.remove('nx-in');void after.offsetWidth;after.classList.add('nx-in');setTimeout(()=>after.classList.remove('nx-in'),700)}
 moveInd(false);if(p!==prevPage&&innerWidth>1170)window.scrollTo({top:0,behavior:reduce?'auto':'smooth'});return r};
// ---- week badge tick + play-button glow ----
const pb=$('#pbadge');let lastW=null;
if(pb)new MutationObserver(()=>{const w=typeof PS!=='undefined'?PS.week:null;if(w!==lastW&&lastW!==null&&!reduce){pb.classList.remove('nx-tick');void pb.offsetWidth;pb.classList.add('nx-tick')}lastW=w}).observe(pb,{childList:true,subtree:true});
// ---- hints fade out once the user has seen them ----
setTimeout(()=>{const h=$('#mhint');if(h)h.classList.add('fade')},9000);
['#c','#pc','#hc'].forEach(s=>{const c=$(s);if(c)c.addEventListener('pointerdown',()=>{['#mhint','#phint'].forEach(h=>{const e=$(h);e&&e.classList.add('fade')})},{once:true})});
// ---- smooth theme switching ----
const tst=document.createElement('style');tst.textContent='.nx-theming *,.nx-theming *::before,.nx-theming *::after{transition:background-color .45s ease,color .45s ease,border-color .45s ease,fill .45s ease!important}';document.head.append(tst);
new MutationObserver(m=>{if(m.some(x=>x.attributeName==='data-theme')&&!reduce){root.classList.add('nx-theming');clearTimeout(root._nx);root._nx=setTimeout(()=>root.classList.remove('nx-theming'),520)}}).observe(root,{attributes:true});
// ---- keyboard: Esc closes floating panels ----
addEventListener('keydown',e=>{if(e.key!=='Escape')return;['#ptip','#htip'].forEach(s=>{const el=$(s);if(el)el.hidden=true})});
// initial state
moveInd(true);stagger($('#page'));play($('#page'),'nx-enter',1100);lastKey=page+'|'+(page==='preg'&&typeof PS!=='undefined'?PS.tab:'');
})();
// ---- womb lighting follows the stage of pregnancy (red early, warm amber mid, deep warm late) ----
(()=>{const st=$('#pstage');if(!st)return;let lw=-1;const pal=w=>w<6?['#8a2436','#3d0d1c','#16040a']:w<26?['#b4552c','#561a0c','#1d0703']:['#8c3424','#34100b','#130505'];
 (function tick(){if(typeof PS!=='undefined'&&PS.week!==lw){lw=PS.week;const p=pal(lw);st.style.setProperty('--wb1',p[0]);st.style.setProperty('--wb2',p[1]);st.style.setProperty('--wb3',p[2])}setTimeout(tick,400)})()})();
