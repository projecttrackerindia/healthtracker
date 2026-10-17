// ---- body detail tier: Light (default, a few MB) / HD atlas (full detail, loaded on request) ----
(()=>{if(!window.QUALITY||typeof PAGES==='undefined')return;
 const ld=()=>document.querySelector('#ld');
 window.onAssetProgress=(id,got,len)=>{const l=ld();if(l&&l.style.display!=='none'&&id.startsWith('#mdz'))l.textContent='Loading anatomy… '+(got/1e6).toFixed(1)+(len?' / '+(len/1e6).toFixed(1):'')+' MB'};
 const mk=()=>{const q=QUALITY.get();return `<div class="card"><div class="hd"><h3>Detail</h3><span class="demo">${q==='hd'?'HD atlas':'Light'}</span></div>
  <div class="chips"><button class="chip ${q==='lite'?'on':''}" data-q="lite">Light · fast</button><button class="chip ${q==='hd'?'on':''}" data-q="hd">HD atlas · loads once</button></div>
  <p class="mute sm" style="margin:8px 0 0">Light works on any phone. HD adds the full-resolution atlas and is kept on this device after the first load.</p></div>`};
 const _lab=PAGES.lab;PAGES.lab=()=>mk()+_lab();
 document.addEventListener('click',async e=>{const b=e.target.closest('[data-q]');if(!b||b.dataset.q===QUALITY.get())return;
  const old=QUALITY.get();QUALITY.set(b.dataset.q);try{delete cacheD['#mdz:'+old]}catch(_){ }
  const l=ld();if(l){l.style.display='grid';l.textContent='Loading anatomy…'}
  try{await A.setSex(A.sex)}catch(err){console.warn(err);QUALITY.set(old)}
  if(page==='lab')render()});
})();
