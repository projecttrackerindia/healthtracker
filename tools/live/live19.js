// ===================== live layer 19: watches & devices — Bluetooth inside the phone app, Withings and Oura clouds =====================
{
const P=SX.p,S=SX.S;
const J=(path,method,body)=>fetch('/api/v1'+path,{method:method||'GET',headers:{'content-type':'application/json','x-tht':'1','x-dokko-key':(S.key||'')},credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)}).then(async r=>{let j={};try{j=await r.json()}catch(e){}if(!r.ok)throw Object.assign(new Error(typeof j.detail==='string'?j.detail:'Request failed'),{status:r.status});return j});

// ---------------------------------------------------------------- A. Web Bluetooth inside the phone app
// The WebView has no navigator.bluetooth. The native BluetoothLe plugin is wrapped in the same shape the web code
// already uses (requestDevice → gatt.connect → getPrimaryService → getCharacteristic → notifications), so the
// blood-pressure / oximeter / scale / thermometer reader and the Polar H10 ECG work unchanged in the Android and iOS apps.
const SIG={heart_rate:0x180d,heart_rate_measurement:0x2a37,blood_pressure:0x1810,blood_pressure_measurement:0x2a35,health_thermometer:0x1809,temperature_measurement:0x2a1c,glucose:0x1808,glucose_measurement:0x2a18,
 weight_scale:0x181d,weight_measurement:0x2a9d,pulse_oximeter:0x1822,plx_spot_check_measurement:0x2a5e,plx_continuous_measurement:0x2a5f,battery_service:0x180f,battery_level:0x2a19,device_information:0x180a};
const uuid=u=>{if(typeof u==='number')return ('00000000'+u.toString(16)).slice(-8)+'-0000-1000-8000-00805f9b34fb';u=String(u).toLowerCase();if(SIG[u]!==undefined)return uuid(SIG[u]);if(/^0x[0-9a-f]{4}$/.test(u))return uuid(parseInt(u,16));if(/^[0-9a-f]{4}$/.test(u))return uuid(parseInt(u,16));return u};
const short=u=>{const m=/^0000([0-9a-f]{4})-0000-1000-8000-00805f9b34fb$/.exec(u);return m?m[1]:u};
const hex2dv=h=>{const parts=String(h||'').trim().split(/\s+/).filter(Boolean);const b=new Uint8Array(parts.length);parts.forEach((p,i)=>b[i]=parseInt(p,16));return new DataView(b.buffer)};
const dv2hex=v=>{const b=v instanceof DataView?new Uint8Array(v.buffer,v.byteOffset,v.byteLength):new Uint8Array(v.buffer||v);return Array.from(b).map(x=>('0'+x.toString(16)).slice(-2)).join(' ')};
function makeBluetooth(BLE){let ready=null;const init=()=>ready||(ready=BLE.initialize({androidNeverForLocation:true}).catch(e=>{ready=null;throw e}));
 class Chr{constructor(dev,svc,id){this.dev=dev;this.svc=svc;this.uuid=id;this.value=null;this.ls=[];this.h=null}
  addEventListener(n,f){if(n==='characteristicvaluechanged')this.ls.push(f)}
  removeEventListener(n,f){this.ls=this.ls.filter(x=>x!==f)}
  _fire(dv){this.value=dv;const ev={target:this,type:'characteristicvaluechanged'};this.ls.forEach(f=>{try{f(ev)}catch(e){}})}
  async startNotifications(){const on=ev=>this._fire(hex2dv(ev&&ev.value));// iOS reports base-UUID services in their short form (180d), Android in full; listen to both spellings
   this.h=[];for(const k of new Set(['notification|'+this.dev.id+'|'+this.svc+'|'+this.uuid,'notification|'+this.dev.id+'|'+short(this.svc)+'|'+short(this.uuid)]))this.h.push(await BLE.addListener(k,on));
   await BLE.startNotifications({deviceId:this.dev.id,service:this.svc,characteristic:this.uuid});return this}
  async stopNotifications(){try{await BLE.stopNotifications({deviceId:this.dev.id,service:this.svc,characteristic:this.uuid})}catch(e){}(this.h||[]).forEach(h=>{try{h.remove()}catch(e){}});this.h=null;return this}
  async readValue(){const r=await BLE.read({deviceId:this.dev.id,service:this.svc,characteristic:this.uuid});this.value=hex2dv(r&&r.value);return this.value}
  async writeValue(v){await BLE.write({deviceId:this.dev.id,service:this.svc,characteristic:this.uuid,value:dv2hex(v)})}
  async writeValueWithResponse(v){return this.writeValue(v)}
  async writeValueWithoutResponse(v){await BLE.writeWithoutResponse({deviceId:this.dev.id,service:this.svc,characteristic:this.uuid,value:dv2hex(v)})}}
 class Svc{constructor(dev,id){this.dev=dev;this.uuid=id}async getCharacteristic(c){return new Chr(this.dev,this.uuid,uuid(c))}}
 class Gatt{constructor(dev){this.device=dev;this.connected=false}
  async connect(){await init();await BLE.connect({deviceId:this.device.id,timeout:15000});this.connected=true;try{BLE.addListener('disconnected|'+this.device.id,()=>{this.connected=false})}catch(e){}return this}
  disconnect(){this.connected=false;BLE.disconnect({deviceId:this.device.id}).catch(()=>{})}
  async getPrimaryService(s){const id=uuid(s);try{const r=await BLE.getServices({deviceId:this.device.id});const have=(r&&r.services||[]).map(x=>String(x.uuid).toLowerCase());if(have.length&&!have.includes(id))throw new Error('No service '+s)}catch(e){if(/No service/.test(e.message))throw e}return new Svc(this.device,id)}}
 class Dev{constructor(d){this.id=d.deviceId;this.name=d.name||'';this.gatt=new Gatt(this)}}
 return {_native:true,
  async getAvailability(){try{await init();const r=await BLE.isEnabled();return !!(r&&r.value)}catch(e){return false}},
  async requestDevice(o){await init();o=o||{};const f=o.filters||[];const svcs=[],prefixes=[];f.forEach(x=>{(x.services||[]).forEach(s=>svcs.push(uuid(s)));if(x.namePrefix)prefixes.push(x.namePrefix);if(x.name)prefixes.push(x.name)});
   const q={optionalServices:Array.from(new Set(svcs.concat((o.optionalServices||[]).map(uuid))))};
   if(prefixes.length){let p=prefixes[0];prefixes.forEach(x=>{let i=0;while(i<p.length&&i<x.length&&p[i]===x[i])i++;p=p.slice(0,i)});if(p.trim())q.namePrefix=p.trim()}
   else if(svcs.length)q.services=Array.from(new Set(svcs));
   try{const r=await BLE.isEnabled();if(r&&r.value===false){try{await BLE.requestEnable()}catch(e){}}}catch(e){}
   let d;try{d=await BLE.requestDevice(q)}catch(e){throw new Error(/cancel/i.test(e.message||'')?'cancelled':(e.message||'No device chosen'))}
   if(!d||!d.deviceId)throw new Error('cancelled');return new Dev(d)}}}
SX.bleShim=makeBluetooth;
try{const C=window.Capacitor;const BLE=C&&C.isNativePlatform&&C.isNativePlatform()&&C.Plugins&&C.Plugins.BluetoothLe;if(BLE&&!(navigator.bluetooth&&navigator.bluetooth.requestDevice)){Object.defineProperty(navigator,'bluetooth',{value:makeBluetooth(BLE),configurable:true});SX.nativeBle=true}}catch(e){}

// ---------------------------------------------------------------- B. Withings and Oura (cloud) beside Fitbit on the Devices tab
const WEAR={providers:[],links:[]};
const fmtT=t=>new Date(t).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
const ICON={withings:'⌚',oura:'💍'};
const status=()=>J('/wear/status').then(r=>{WEAR.providers=r.providers||[];WEAR.links=r.links||[];if(page==='devices')render()}).catch(()=>{});
status();
function card(p,m){const link=WEAR.links.find(l=>l.member===m.id&&l.provider===p.id);
 return `<div class="lv11-src ${link?'on':''}"><div class="lv11-ic">${ICON[p.id]||'⌚'}</div><div class="grow"><b>${E(p.label)}</b><small>${link?P('Linked')+(link.lastSync?' · '+P('last sync')+' '+fmtT(link.lastSync*1000):''):E(p.about)}</small>${!link&&!p.enabled?`<small>${P('Account linking opens once Urban Health’s developer access is approved.')}</small>`:''}</div>${link?`<button class="btn p sm" data-sx="wearsync:${p.id}">${P('Sync')}</button><button class="btn s sm" data-sx="wearunlink:${p.id}">${P('Unlink')}</button>`:p.enabled?`<button class="btn p sm" data-sx="wearlink:${p.id}">${P('Link')}</button>`:''}</div>`}
SX.extend('devices',{after(){const m=SX.me();if(!m||!WEAR.providers.length)return '';return `<div class="card wide lv11-dev lv19-wear"><div class="hd"><div><h3>${P('Watch and ring accounts')}</h3><small class="mute">${P('For watches that keep their readings in their own cloud. Most watches need none of this: their phone app shares with Health Connect or Apple Health, and the Urban Health app reads it from there.')}</small></div></div>${WEAR.providers.map(p=>card(p,m)).join('')}</div>`}});
const label=id=>{const p=WEAR.providers.find(x=>x.id===id);return p?p.label:id};
SX.act.wearlink=async([p])=>{const m=SX.me();try{const r=await fetch('/api/v1/wear/'+encodeURIComponent(p)+'/start?member='+encodeURIComponent(m.id),{method:'POST',headers:{'x-tht':'1','x-dokko-key':S.key||''},credentials:'same-origin'});const j=await r.json();if(!r.ok)throw new Error(j.detail||'failed');location.href=j.url}catch(e){toast(e.message)}};
SX.act.wearsync=async([p])=>{const m=SX.me();toast(P('Syncing')+' '+label(p)+'…');try{const r=await J('/wear/'+encodeURIComponent(p)+'/sync','POST',{member:m.id,days:7});const data=r.data||{};const ecg=data.ecg||[];delete data.ecg;
  let n=SX.hcMerge(m,data,p);(S.vitals[m.id]||[]).forEach(v=>{if(v.src===p&&!v._w){v.dev=label(p);v._w=1}});if(ecg.length&&SX.ecgImport)n+=SX.ecgImport(m,ecg,p);
  S.hc[m.id]={t:Date.now(),n,src:p};SX.ledger('reading',true,'Synced from '+label(p),m.id);SX.save();status();render();toast(n?P('Added')+' '+n+' '+P('new readings'):P('Nothing new since the last sync'))}catch(e){toast(e.message);if(e.status===401)status()}};
SX.act.wearunlink=async([p])=>{const m=SX.me();if(!confirm(P('Unlink')+' '+label(p)+' '+P('from this profile?')))return;try{await J('/wear/'+encodeURIComponent(p)+'/'+encodeURIComponent(m.id),'DELETE');status();toast(label(p)+' '+P('unlinked'))}catch(e){toast(e.message)}};
if(/#wear=/.test(location.hash)){const mm=/#wear=([a-z]+):([a-z]+)/.exec(location.hash);history.replaceState(null,'',location.pathname);if(mm)setTimeout(()=>{const p=mm[1],st=mm[2];if(st==='done'){toast(label(p)+' '+P('linked — syncing'));go('devices');SX.act.wearsync([p])}else toast(st==='cancelled'?P('Linking was cancelled'):P('Linking did not complete'))},1200)}
}
