// ===================== live layer 13: phone shell — bottom tab bar, More sheet, compact app bar =====================
{
const P=SX.p,S=SX.S;
const PRIMARY=['home','records','meds','care'];
const phone=()=>matchMedia('(max-width:720px)').matches;
const svg=k=>`<svg viewBox="0 0 24 24">${I[k]||''}</svg>`;const short=k=>{const t=SX.t('nav.'+k);return t.split(/ & | and /)[0]};
I.more='<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>';
function groupOf(){try{return SX.grpOf(page)}catch(e){return 'home'}}
function tabBar(){let bar=document.getElementById('mtab');if(!bar){bar=document.createElement('nav');bar.id='mtab';bar.setAttribute('aria-label','Main');document.body.appendChild(bar)}
 const cur=groupOf(),inMore=!PRIMARY.includes(cur);
 bar.innerHTML=PRIMARY.map(k=>{const g=SX.G.find(x=>x.k===k);if(!g)return '';const f=SX.badge&&SX.badge[k],n=f?f():0;return `<button class="${cur===k?'on':''}" data-g="${k}" aria-label="${E(SX.t('nav.'+k))}">${svg(g.ic)}<span>${E(short(k))}</span>${n?`<em>${n}</em>`:''}</button>`}).join('')+`<button class="${inMore?'on':''}" data-g="more" aria-label="${E(P('More'))}">${svg('more')}<span>${P('More')}</span>${moreBadge()?`<em>${moreBadge()}</em>`:''}</button>`;
 bar.querySelectorAll('button').forEach(b=>b.onclick=()=>{const k=b.dataset.g;if(k==='more'){moreSheet();return}const g=SX.G.find(x=>x.k===k);if(!g)return;const first=g.tabs.find(t=>!SX.tabVisible||SX.tabVisible(t))||g.tabs[0];go(first);window.scrollTo({top:0})})}
function moreBadge(){let n=0;SX.G.forEach(g=>{if(PRIMARY.includes(g.k))return;const f=SX.badge&&SX.badge[g.k];n+=f?(f()||0):0});return n}
function moreSheet(){const cur=groupOf();const rest=SX.G.filter(g=>!PRIMARY.includes(g.k));
 SX.modal(`<h2>${P('Everything')}</h2><div class="lv13-more">${rest.map(g=>`<button class="${cur===g.k?'on':''}" data-mg="${g.k}">${svg(g.ic)}<span>${E(SX.t('nav.'+g.k))}</span></button>`).join('')}</div>
  <div class="lv13-quick"><button class="btn s sm" id="m13lang">🌐 ${E(document.getElementById('sxLang')?document.getElementById('sxLang').textContent:'EN')} · ${P('Language')}</button><button class="btn s sm" id="m13theme">◐ ${P('Theme')}</button><button class="btn s sm" id="m13tour">▶ ${P('Tour')}</button><button class="btn s sm" id="m13dev">📱 ${P('Devices')}</button></div>
  <p class="mute sm" style="margin:10px 0 0">${P('Safety: SOS is the red button; Medical ID and first aid are under Safety.')}</p>`,{label:'Menu'});
 document.querySelectorAll('.lv13-more [data-mg]').forEach(b=>b.onclick=()=>{const g=SX.G.find(x=>x.k===b.dataset.mg);SX.closeModal();if(!g)return;const first=g.tabs.find(t=>!SX.tabVisible||SX.tabVisible(t))||g.tabs[0];go(first);window.scrollTo({top:0})});
 const click=id=>{const el=document.getElementById(id);SX.closeModal();if(el)el.click()};
 document.getElementById('m13lang').onclick=()=>click('sxLang');document.getElementById('m13theme').onclick=()=>click('theme');document.getElementById('m13tour').onclick=()=>click('tourBtn');document.getElementById('m13dev').onclick=()=>{SX.closeModal();go('devices')}}
// keep the bar in step with navigation and badges
new MutationObserver(()=>{try{tabBar()}catch(e){}}).observe(document.body,{attributes:true,attributeFilter:['data-page']});
const paint13=SX.paintNav;if(paint13)SX.paintNav=function(){const r=paint13.apply(this,arguments);try{tabBar()}catch(e){}return r};
setTimeout(tabBar,0);setInterval(tabBar,15000);addEventListener('resize',tabBar);
// the sub-tab row scrolls the active tab into view on phones
const tv13=SX.extend;document.addEventListener('click',()=>{if(!phone())return;setTimeout(()=>{const on=document.querySelector('.sx-tabs button.on');if(on)on.scrollIntoView({block:'nearest',inline:'center',behavior:'smooth'})},50)});void tv13;
}
// ===================== Google Maps when GOOGLE_MAPS_KEY is set (roads, Places autocomplete, routes); OpenStreetMap otherwise =====================
{
const P=SX.p,S=SX.S;
let G={loading:false,ready:false,key:''};
const key=()=>{try{return (SX.cfg&&SX.cfg.maps&&SX.cfg.maps.key)||G.key}catch(e){return ''}};
SX.gmapsOn=()=>!!key();
function load(){if(G.ready||G.loading||!key())return;G.loading=true;const s=document.createElement('script');s.src=`https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key())}&libraries=places,marker&loading=async&callback=__gmapsReady&region=IN&language=${S.lang==='hi'?'hi':S.lang==='te'?'te':'en'}`;s.async=true;s.onerror=()=>{G.loading=false;G.key='';toast(P('Maps could not load; using OpenStreetMap'))};document.head.appendChild(s)}
window.__gmapsReady=()=>{G.ready=true;G.loading=false;boot()};
const fetchCfg=()=>{if(SX.cfg)return Promise.resolve();return fetch('/api/v1/config').then(r=>r.json()).then(j=>{SX.cfg=SX.cfg||j}).catch(()=>{})};
fetchCfg().then(()=>{if(key())load()});
let seq=0;const PENDING={};
SX.gmapHTML=(center,items,opt={})=>{const id='gm'+(++seq);PENDING[id]={center,items,opt};setTimeout(()=>mount(id),0);return `<div class="lv6-map lv13-gmap" id="${id}" style="height:${opt.h||300}px"><div class="lv13-gmap-in"></div>${opt.act?'':''}</div>`};
function mount(id){const el=document.getElementById(id),job=PENDING[id];if(!el||!job)return;if(!G.ready){load();setTimeout(()=>mount(id),400);return}delete PENDING[id];const {center,items,opt}=job;
 const map=new google.maps.Map(el.querySelector('.lv13-gmap-in'),{center:{lat:center.lat,lng:center.lng},zoom:opt.zoom||13,disableDefaultUI:true,zoomControl:true,gestureHandling:'greedy',clickableIcons:false,mapId:'THT'});
 const bounds=new google.maps.LatLngBounds();bounds.extend({lat:center.lat,lng:center.lng});
 new google.maps.Marker({map,position:{lat:center.lat,lng:center.lng},title:P('You'),icon:{path:google.maps.SymbolPath.CIRCLE,scale:8,fillColor:'#2f5bff',fillOpacity:1,strokeColor:'#fff',strokeWeight:3}});
 items.filter(p=>p.lat&&p.lng).forEach(p=>{const m=new google.maps.Marker({map,position:{lat:p.lat,lng:p.lng},title:p.name||'',icon:p.partner?undefined:{path:google.maps.SymbolPath.CIRCLE,scale:7,fillColor:'#dc2626',fillOpacity:.95,strokeColor:'#fff',strokeWeight:2}});bounds.extend({lat:p.lat,lng:p.lng});
  if(opt.act)m.addListener('click',()=>{const f=SX.act[opt.act];if(f)f([p.id])})});
 if(items.length)map.fitBounds(bounds,40);
 if(opt.route&&opt.route.from&&opt.route.to){try{const ds=new google.maps.DirectionsService(),dr=new google.maps.DirectionsRenderer({map,suppressMarkers:true,polylineOptions:{strokeColor:'#2f5bff',strokeWeight:5}});ds.route({origin:opt.route.from,destination:opt.route.to,travelMode:'DRIVING'},(res,st)=>{if(st==='OK'){dr.setDirections(res);const leg=res.routes[0].legs[0];const et=el.parentElement&&el.parentElement.querySelector('.lv13-eta');if(et)et.textContent=leg.duration.text+' · '+leg.distance.text}})}catch(e){}}}
function boot(){Object.keys(PENDING).forEach(mount)}
// Places autocomplete on the address form when Google is on
document.addEventListener('focusin',e=>{const inp=e.target;if(!G.ready||!inp||!inp.matches('#adf input[name=line1]')||inp.dataset.ac)return;inp.dataset.ac='1';try{const ac=new google.maps.places.Autocomplete(inp,{componentRestrictions:{country:'in'},fields:['address_components','geometry','name']});ac.addListener('place_changed',()=>{const p=ac.getPlace();if(!p||!p.address_components)return;const F=document.getElementById('adf');const get=t=>{const c=p.address_components.find(x=>x.types.includes(t));return c?c.long_name:''};
 const street=[get('premise'),get('street_number'),get('route')].filter(Boolean).join(', ');F.line1.value=p.name&&!/^\d/.test(p.name)?p.name:(street||F.line1.value);if(street&&F.line1.value!==street)F.line2.value=street;F.area.value=get('sublocality_level_1')||get('sublocality')||get('neighborhood')||F.area.value;F.city.value=get('locality')||get('administrative_area_level_2')||F.city.value;F.state.value=get('administrative_area_level_1')||F.state.value;F.pin.value=get('postal_code')||F.pin.value;
 if(p.geometry&&p.geometry.location){F.dataset.lat=p.geometry.location.lat();F.dataset.lng=p.geometry.location.lng();const st=document.getElementById('adgeo');if(st)st.textContent=P('Pinned from Google Maps')}})}catch(e){}});
}
