// ===================== live layer 37: how was the visit? =====================
// Somebody came to this family's door with a needle. They have a clear opinion about that person, and they
// have it now — not in two days when the report lands and the question has quietly become "how good is the
// lab?". So the card appears the moment the sample is collected and stops asking once it has an answer.
//
// It is deliberately separate from the store rating. A gentle phlebotomist working for a slow lab, and a
// rushed one working for a fast lab, would score identically under one star, and neither lab would learn
// anything it could act on.
{
const P = SX.p, E = SX.E || (s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
const St = () => SX.S || {};

SX.addPhrases({
  'How was the visit?': ['विज़िट कैसी रही?', 'విజిట్ ఎలా ఉంది?'],
  'collected your sample': ['आपका सैंपल लिया', 'మీ శాంపిల్ తీసుకున్నారు'],
  'Tap a star': ['स्टार चुनें', 'ఒక స్టార్ నొక్కండి'],
  'What went well?': ['क्या अच्छा रहा?', 'ఏది బాగుంది?'],
  'What went wrong?': ['क्या ठीक नहीं था?', 'ఏది సరిగా లేదు?'],
  'Anything else?': ['और कुछ?', 'ఇంకేమైనా?'],
  'Only the lab sees this.': ['यह केवल लैब देखती है।', 'దీన్ని ల్యాబ్ మాత్రమే చూస్తుంది.'],
  'Send': ['भेजें', 'పంపు'],
  'Thank you': ['धन्यवाद', 'ధన్యవాదాలు'],
  'star': ['स्टार', 'స్టార్'],
  'stars': ['स्टार', 'స్టార్‌లు'],
});

// The toast in the main script is not a handle a layer can reach, and the element is. Same node, same class.
function say(msg) {
  try {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg; t.classList.add('show');
    clearTimeout(say.h); say.h = setTimeout(() => t.classList.remove('show'), 2400);
  } catch (e) {}
}

let TAGS = null, sending = false;
async function tags() {
  if (TAGS) return TAGS;
  try { TAGS = await SX.api('/visit-tags', { silent: true }); } catch (e) { TAGS = { good: [], bad: [] }; }
  return TAGS;
}

const pending = () => (St().liveOrders || []).filter(o => o.kind === 'lab' && o.canRateVisit);
const whoFor = o => (o.timeline || []).filter(t => t.s === 'assigned' && t.note).map(t => t.note).pop() || '';

// ---------------------------------------------------------------- the sheet
async function sheet(o, stars) {
  const T = await tags();
  const who = whoFor(o);
  const list = stars >= 4 ? T.good : T.bad;
  const ask = stars >= 4 ? P('What went well?') : P('What went wrong?');
  SX.modal(`<h2>${E(P('How was the visit?'))}</h2>
    <p class="mute sm">${who ? E(who) + ' ' + E(P('collected your sample')) : E(P('collected your sample'))} · ${stars} ${stars === 1 ? E(P('star')) : E(P('stars'))}</p>
    <form class="form" id="lv37f">
      <div class="full lv37-stars" data-live>${[1,2,3,4,5].map(n =>
        `<button type="button" class="lv37-s ${n <= stars ? 'on' : ''}" data-n="${n}" aria-label="${n}">★</button>`).join('')}</div>
      ${list.length ? `<div class="full lv37-tags">${list.map(t =>
        `<button type="button" class="lv37-t" data-t="${E(t)}">${E(P(t) || t)}</button>`).join('')}</div>` : ''}
      <label class="full">${E(P('Anything else?'))} <small>${E(P('Only the lab sees this.'))}</small>
        <input name="note" maxlength="300" autocomplete="off"></label>
      <p class="full lv-err" role="alert" hidden></p>
      <div class="full lv-row-end">
        <button class="btn s" type="button" data-sx="closeModal">${E(P('Later'))}</button>
        <button class="btn p" type="submit">${E(P('Send'))}</button></div>
    </form>`, { label: 'Visit' });

  const f = document.getElementById('lv37f');
  if (!f) return;
  let n = stars;
  const picked = new Set();
  f.querySelectorAll('.lv37-s').forEach(b => b.onclick = () => {
    n = +b.dataset.n;
    f.querySelectorAll('.lv37-s').forEach(x => x.classList.toggle('on', +x.dataset.n <= n));
    // The tag list belongs to the rating: asking "what went well?" under two stars is not listening.
    const want = n >= 4 ? T.good : T.bad;
    const box = f.querySelector('.lv37-tags');
    if (box && box.dataset.for !== String(n >= 4)) {
      box.dataset.for = String(n >= 4);
      picked.clear();
      box.innerHTML = want.map(t => `<button type="button" class="lv37-t" data-t="${E(t)}">${E(P(t) || t)}</button>`).join('');
      wireTags(box);
    }
  });
  function wireTags(box) {
    box.querySelectorAll('.lv37-t').forEach(b => b.onclick = () => {
      const t = b.dataset.t;
      if (picked.has(t)) { picked.delete(t); b.classList.remove('on'); }
      else if (picked.size < 5) { picked.add(t); b.classList.add('on'); }
    });
  }
  wireTags(f);

  f.onsubmit = async ev => {
    ev.preventDefault();
    if (sending) return;
    sending = true;
    const note = (new FormData(f).get('note') || '').toString();
    try {
      const out = await SX.api(`/orders/${o.id}/visit-rating`, { method: 'POST', body: { rating: n, tags: [...picked], note } });
      const all = St().liveOrders || [];
      const i = all.findIndex(x => x.id === o.id);
      if (i >= 0) { all[i] = out; SX.save && SX.save(); }
      SX.closeModal();
      say(P('Thank you'));
      paint();
    } catch (e) {
      const el = f.querySelector('.lv-err');
      if (el) { el.textContent = e.message || 'Could not send that'; el.hidden = false; }
    } finally { sending = false; }
  };
}

// ---------------------------------------------------------------- the card
function card(o) {
  const who = whoFor(o);
  return `<div class="card wide lv37" data-oid="${E(o.id)}">
    <div class="lv37-hd">
      <div class="grow"><b>${E(P('How was the visit?'))}</b>
        <small>${who ? E(who) + ' ' + E(P('collected your sample')) : E(P('collected your sample'))} · ${E(P('Tap a star'))}</small></div>
    </div>
    <div class="lv37-stars">${[1,2,3,4,5].map(n =>
      `<button class="lv37-s" data-rate="${E(o.id)}:${n}" aria-label="${n}">★</button>`).join('')}</div>
  </div>`;
}

const SHOW_ON = ['dash', 'orders'];
const onPage = () => SHOW_ON.includes(document.body.dataset.page || '');

function paint() {
  if (!onPage()) { document.querySelectorAll('.lv37').forEach(e => e.remove()); return; }
  const rows = pending();
  const host = document.getElementById('page');
  const have = new Set([...document.querySelectorAll('.lv37')].map(e => e.dataset.oid));
  document.querySelectorAll('.lv37').forEach(e => { if (!rows.some(o => o.id === e.dataset.oid)) e.remove(); });
  if (!host) return;
  rows.forEach(o => {
    if (have.has(o.id)) return;
    const slot = document.createElement('div');
    slot.innerHTML = card(o);
    const node = slot.firstElementChild;
    if (!node) return;
    // Below a technician who is still on their way, above everything else: an unanswered question about a
    // visit that has just happened is more use to the family than the step counter.
    const live = document.querySelector('.lv36');
    if (live) live.after(node); else host.prepend(node);
    node.querySelectorAll('[data-rate]').forEach(b => b.onclick = () => {
      const [id, n] = b.dataset.rate.split(':');
      const ord = (St().liveOrders || []).find(x => x.id === id);
      if (ord) sheet(ord, +n);
    });
  });
}

// Orders arrive from layer 36's fetch and from the main script's own poll; repainting on a short timer costs
// nothing and means the card appears the moment the technician taps Collected.
setInterval(() => { try { paint(); } catch (e) {} }, 4000);
setTimeout(() => { try { paint(); } catch (e) {} }, 1200);
document.addEventListener('visibilitychange', () => { if (!document.hidden) setTimeout(paint, 300); });
}
