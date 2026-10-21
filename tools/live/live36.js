// ===================== live layer 36: watching your technician come =====================
// The other half of the lab slice. A technician's phone is now sending its position; this is what the family
// sees. It appears on Today as well as Orders, because a family waiting for someone at the door should not
// have to go looking for the screen that tells them where they are.
//
// The rule throughout: never draw a marker we cannot stand behind. A pin that has not moved in four minutes
// is labelled as such, and a technician who is not sharing gets a phone number instead of a map. A stationary
// pin presented as live reads as broken, and costs more trust than showing nothing.
{
const P = SX.p, E = SX.E || (s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));

SX.addPhrases({
  'On the way': ['रास्ते में', 'దారిలో ఉన్నారు'],
  'is on the way': ['रास्ते में हैं', 'దారిలో ఉన్నారు'],
  'has arrived': ['पहुँच गए हैं', 'చేరుకున్నారు'],
  'is assigned': ['तय हो गए हैं', 'కేటాయించబడ్డారు'],
  'Your technician': ['आपके टेक्नीशियन', 'మీ టెక్నీషియన్'],
  'away': ['दूर', 'దూరంలో'],
  'Last seen': ['आख़िरी बार देखा', 'చివరిగా చూసింది'],
  'just now': ['अभी', 'ఇప్పుడే'],
  'min ago': ['मिनट पहले', 'నిమిషాల క్రితం'],
  'They will set off closer to your slot.': ['वे आपके समय के क़रीब निकलेंगे।', 'మీ సమయానికి దగ్గరగా బయలుదేరుతారు.'],
  'Not sharing their location right now — call them if you need to.':
    ['अभी लोकेशन साझा नहीं हो रही — ज़रूरत हो तो कॉल करें।', 'ప్రస్తుతం లొకేషన్ పంచుకోవడం లేదు — అవసరమైతే కాల్ చేయండి.'],
  'Sample collected': ['सैंपल ले लिया गया', 'శాంపిల్ సేకరించారు'],
});

const TRACKABLE = ['assigned', 'en_route', 'arrived'];
const T = {};              // order id -> last track payload
let timer = null, inflight = false;

const St = () => SX.S || {};
const liveLabs = () => (St().liveOrders || []).filter(o => o.kind === 'lab' && TRACKABLE.includes(o.status));
let fetched = 0;

// Today does not load live orders — only the Orders page does. A family waiting at the door should not have
// to go and find that page, so this card asks for them itself.
async function ensureOrders() {
  // Shorter than the poll interval, so every tick really does refetch. A longer throttle than the loop means
  // the first fetch (which happens before the family has even signed in) pins an empty result for its whole
  // window, and the card does not appear until long after the technician set off.
  if (Date.now() - fetched < 8000) return;
  fetched = Date.now();
  try {
    const r = await SX.api('/orders', { silent: true });
    if (r && r.orders) { St().liveOrders = r.orders; SX.save && SX.save(); }
  } catch (e) {}
}

// ---------------------------------------------------------------- distance, not invented minutes
// We have the technician's position and the family's address. Straight-line distance is something we can
// actually stand behind. "8 minutes" would need a routing call we are not making, and a wrong ETA on a
// doorstep is worse than no ETA.
function km(a, b) {
  if (!a || !b || a.lat == null || b.lat == null) return null;
  const R = 6371, d = x => x * Math.PI / 180;
  const dLat = d(b.lat - a.lat), dLng = d(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(d(a.lat)) * Math.cos(d(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
const far = n => n == null ? '' : n < 1 ? `${Math.round(n * 1000)} m ${P('away')}` : `${n.toFixed(1)} km ${P('away')}`;
const ago = s => s < 45 ? P('just now') : `${Math.round(s / 60)} ${P('min ago')}`;

// ---------------------------------------------------------------- the card
function card(o) {
  const t = T[o.id] || {};
  const who = (t.agent && t.agent.name) || P('Your technician');
  const phone = (t.agent && t.agent.phone) || '';
  const home = o.addr && o.addr.lat != null ? { lat: o.addr.lat, lng: o.addr.lng } : null;
  const at = t.live ? { lat: t.lat, lng: t.lng } : null;
  const dist = at && home ? km(at, home) : null;

  // One line that is true, whatever we happen to know.
  let line, cls;
  if (o.status === 'arrived') { line = `${who} ${P('has arrived')}`; cls = 'here'; }
  else if (t.live) { line = `${who} ${P('is on the way')}`; cls = 'moving'; }
  else if (o.status === 'en_route') { line = `${who} ${P('is on the way')}`; cls = 'moving'; }
  else { line = `${who} ${P('is assigned')}`; cls = 'soon'; }

  const sub = o.status === 'assigned' ? P('They will set off closer to your slot.')
    : t.live ? [far(dist), o.slot].filter(Boolean).join(' · ')
    : t.ageS != null ? `${P('Last seen')} ${ago(t.ageS)}`
    : P('Not sharing their location right now — call them if you need to.');

  // Without a maps key SX.gmapHTML still returns a container, which paints as an empty grey box — worse than
  // no map, because it looks like something that failed to load. The distance line already carries the fact.
  const mapsOn = !!(SX.cfg && SX.cfg.maps && SX.cfg.maps.provider === 'google' && SX.cfg.maps.key);
  const map = (t.live && at && mapsOn && SX.gmapHTML)
    ? SX.gmapHTML(at, [
        { id: 'tech', name: who, lat: at.lat, lng: at.lng },
        ...(home ? [{ id: 'home', name: P('You'), lat: home.lat, lng: home.lng }] : [])
      ], { h: 190, zoom: 15 })
    : '';

  return `<div class="card wide lv36 lv36-${cls}" data-oid="${E(o.id)}">
    <div class="lv36-hd">
      <span class="lv36-av">${E((who.trim()[0] || '?').toUpperCase())}</span>
      <div class="grow"><b>${E(line)}</b><small>${E(sub)}</small></div>
      ${phone ? `<a class="btn s sm lv36-call" href="tel:${E(phone)}">${P('Call')}</a>` : ''}
    </div>
    ${map ? `<div class="lv36-map">${map}</div>` : ''}
    <div class="lv36-steps">${['assigned', 'en_route', 'arrived', 'collected'].map(k => {
      const order = ['assigned', 'en_route', 'arrived', 'collected'];
      const on = order.indexOf(o.status) >= order.indexOf(k);
      return `<i class="${on ? 'on' : ''}"></i>`;
    }).join('')}</div>
  </div>`;
}

function html() {
  const rows = liveLabs();
  return rows.length ? rows.map(card).join('') : '';
}

// ---------------------------------------------------------------- polling, only while it is worth it
SX.__p = { polls: 0, rows: 0, painted: 0, err: '' };
async function poll() {
  SX.__p.polls++;
  if (inflight || document.hidden) return;
  await ensureOrders();
  const rows = liveLabs();
  SX.__p.rows = rows.length;
  if (!rows.length) { return; }
  inflight = true;
  try {
    for (const o of rows) {
      try { T[o.id] = await SX.api(`/orders/${o.id}/track`, { silent: true }); } catch (e) {}
    }
    try { paint(); SX.__p.painted++; } catch (e) { SX.__p.err = String(e && e.message); }
  } finally { inflight = false; }
}

function start() {
  if (timer) return;
  poll();
  timer = setInterval(poll, 10000);     // the technician pings every 15s; polling faster buys nothing
}
function stop() { if (timer) { clearInterval(timer); timer = null; } }

// Repaint in place. Re-rendering the page would rebuild the Google map on every tick, which is exactly the
// fault that made the places list shake in round 34.
function paint() {
  const host = document.getElementById('page');
  if (!onPage()) { document.querySelectorAll('.lv36').forEach(e => e.remove()); return; }
  const rows = liveLabs();

  // Somebody is on their way to this family's door. That belongs at the top of the screen, not below the
  // step counter — so the card is placed first in #page and kept there, whatever else re-renders around it.
  if (host && rows.length && !document.querySelector('.lv36')) {
    const slot = document.createElement('div');
    slot.innerHTML = html();
    const node = slot.firstElementChild;
    if (node) host.prepend(node);
    return;
  }
  const first = document.querySelector('.lv36');
  if (host && first && host.firstElementChild !== first) host.prepend(first);
  document.querySelectorAll('.lv36').forEach(el => {
    const o = (St().liveOrders || []).find(x => x.id === el.dataset.oid);
    if (!o) { el.remove(); return; }
    const t = T[o.id] || {};
    const fresh = document.createElement('div');
    fresh.innerHTML = card(o);
    const next = fresh.firstElementChild;
    // keep the existing map node alive; swap only the text and the dots
    const oldMap = el.querySelector('.lv36-map'), newMap = next.querySelector('.lv36-map');
    if (oldMap && newMap) newMap.replaceWith(oldMap);
    if (oldMap && t.live && SX.gmapPan) SX.gmapPan({ lat: t.lat, lng: t.lng });
    el.replaceWith(next);
  });
}

SX.trackHTML = html;

// The loop runs on its own rather than hanging off a page's mounted hook: a family may be anywhere in the app
// when their technician sets off, and the card has to be able to appear without them navigating to find it.
// paint() decides whether this page is one that should show it.
const SHOW_ON = ['dash', 'orders'];
const onPage = () => SHOW_ON.includes(document.body.dataset.page || '');
start();
setInterval(() => { if (!timer && onPage()) start(); }, 5000);

document.addEventListener('visibilitychange', () => { if (!document.hidden && liveLabs().length) poll(); });
}
