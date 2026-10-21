// ===================== live layer 39: SOS — make the thing you must press the thing you can see =====================
// Reported from a real alert: "it didn't send any messages, it just showed a popup to call."
//
// It was working as built, which was the problem. Email and the family's app alert go on their own; SMS and
// WhatsApp cannot, because a web page on a phone is not allowed to send a message on your behalf — sms: and
// wa.me links only open the composer. Until the server has a DLT-registered sender and a WhatsApp Business
// template, those two need one tap each.
//
// One tap is defensible. Hiding that tap in a small grey chip below the fold, next to status text that looks
// identical, is not. So the sends move up under the call buttons and get the size they deserve.
{
const P = SX.p, E = SX.E || (s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));

SX.addPhrases({
  'Tell your contacts': ['अपने संपर्कों को बताएं', 'మీ కాంటాక్ట్‌లకు చెప్పండి'],
  'Your phone sends it, so it comes from your number.': [
    'आपका फ़ोन भेजता है, इसलिए यह आपके नंबर से जाता है।',
    'మీ ఫోన్ పంపుతుంది, కాబట్టి ఇది మీ నంబర్ నుండి వెళ్తుంది.'],
  'Text everyone': ['सबको भेजें', 'అందరికీ పంపండి'],
  'Sent': ['भेजा गया', 'పంపారు'],
});

// Which channels the server drives on its own. When both SMS and WhatsApp are live this whole block stops
// appearing by itself — there is nothing left for the person to tap.
let CH = null;
SX.api('/sos/channels', { silent: true }).then(j => { CH = j; lift(); }).catch(() => { CH = {}; lift(); });
const serverSends = () => !!(CH && CH.sms && CH.whatsapp);

function lift() {
  const act = document.getElementById('lv21act');
  if (!act || serverSends() || act.querySelector('.lv39')) return;
  const rows = [...act.querySelectorAll('.lv21-c')].filter(r => r.querySelector('a[href^="https://wa.me/"], a[href^="sms:"]'));
  if (!rows.length) return;

  const people = rows.map(r => ({
    name: (r.querySelector('b') || {}).textContent || '',
    wa: (r.querySelector('a[href^="https://wa.me/"]') || {}).href || '',
    sms: (r.querySelector('a[href^="sms:"]') || {}).getAttribute('href') || '',
    // The status line already says what the server managed; don't offer a tap for something already sent.
    done: /✓\s*SMS/.test(r.textContent),
  })).filter(p => p.wa || p.sms);
  if (!people.length) return;

  // One sms: with every number is a genuine single tap for the lot, on both iOS and Android.
  const all = act.querySelector('a.lv21-chip.all');
  const many = people.filter(p => p.sms).length > 1;

  const html = `<div class="lv21-sec lv39">
    <div class="lv21-sh"><b>${P('Tell your contacts')}</b><small>${P('Your phone sends it, so it comes from your number.')}</small></div>
    ${many && all ? `<a class="lv39-all" href="${E(all.getAttribute('href'))}">${P('Text everyone')} · ${people.filter(p => p.sms).length}</a>` : ''}
    ${people.map((p, i) => `<div class="lv39-p">
        <span class="lv39-n">${E(p.name)}${p.done ? ` <i>✓ ${P('Sent')}</i>` : ''}</span>
        <span class="lv39-b">
          ${p.wa ? `<a class="lv39-go wa" href="${E(p.wa)}" target="_blank" rel="noopener" data-i="${i}">WhatsApp</a>` : ''}
          ${p.sms ? `<a class="lv39-go" href="${E(p.sms)}" data-i="${i}">SMS</a>` : ''}
        </span></div>`).join('')}
  </div>`;

  const calls = act.querySelector('.lv21-calls');
  if (calls) calls.insertAdjacentHTML('afterend', html); else act.insertAdjacentHTML('afterbegin', html);

  // The small chips stay where they are, as the record of what went out. They are no longer the only way in.
  act.querySelectorAll('.lv21-c a.lv21-chip.wa, .lv21-c a[href^="sms:"]').forEach(a => a.classList.add('lv39-dim'));
  act.querySelectorAll('.lv39-go').forEach(a => a.addEventListener('click', () => {
    a.classList.add('tapped');
    // Leaving for WhatsApp suspends the page on iOS; come back to a siren that is still going.
    setTimeout(resume, 1200);
  }));
}

// paint() replaces the sheet's innerHTML on every location fix and every status change, which drops whatever
// was added to it. Watch instead of hooking: there is no export to hook.
new MutationObserver(() => { try { lift(); } catch (e) {} })
  .observe(document.body, { childList: true, subtree: true });

const CAN_BUZZ = typeof navigator.vibrate === 'function';

// ---------------------------------------------------------------- the siren that stopped after one pass
// It starts on the press, which is a real user gesture, so the AudioContext is allowed to run. Then the phone
// locks or the person switches to WhatsApp, iOS suspends the context, and nothing ever resumed it. From the
// outside that is "the sound came once".
// The previous siren kept its AudioContext in a closure, so nothing could reach in and wake it. This one
// has the same interface — start / mute / stop / on, which is all the rest of the app calls — and keeps the
// context where a resume can find it.
let ctx = null, osc = null, gain = null, sweep = null, vib = null, muted = false;

SX.siren = {
  start() {
    muted = false;
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === 'suspended') ctx.resume();
      if (!osc) {
        osc = ctx.createOscillator();
        gain = ctx.createGain();
        osc.type = 'square';
        gain.gain.value = 0.0001;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
      }
      gain.gain.cancelScheduledValues(ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.35, ctx.currentTime + 0.15);
      let up = true;
      const step = () => {
        if (!osc || muted) return;
        const t = ctx.currentTime;
        osc.frequency.cancelScheduledValues(t);
        osc.frequency.setValueAtTime(up ? 620 : 1180, t);
        osc.frequency.linearRampToValueAtTime(up ? 1180 : 620, t + 0.55);
        up = !up;
      };
      step();
      clearInterval(sweep);
      sweep = setInterval(step, 550);
    } catch (e) {}
    try {
      if (CAN_BUZZ) {
        navigator.vibrate([500, 200, 500, 200, 500]);
        clearInterval(vib);
        vib = setInterval(() => navigator.vibrate([500, 200, 500, 200, 500]), 2000);
      }
    } catch (e) {}
    try { if (window.Capacitor && Capacitor.Plugins && Capacitor.Plugins.Haptics) Capacitor.Plugins.Haptics.vibrate({ duration: 600 }); } catch (e) {}
    document.body.classList.add('lv29-siren');
  },
  mute() {
    muted = true;
    try { if (gain && ctx) gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.1); } catch (e) {}
    clearInterval(sweep); sweep = null;
    setTimeout(() => { try { osc && osc.stop(); } catch (e) {} osc = null; }, 150);
  },
  stop() {
    this.mute();
    clearInterval(vib); vib = null;
    try { navigator.vibrate && navigator.vibrate(0); } catch (e) {}
    document.body.classList.remove('lv29-siren');
  },
  on: () => !!osc && !muted,
};

function resume() {
  // Only when it should still be sounding: muted means the person chose silence, and taking that back
  // because they tapped the screen would be its own kind of broken.
  if (muted || !osc) return;
  try {
    if (ctx && ctx.state === 'suspended') ctx.resume();
    if (!sweep) SX.siren.start();
  } catch (e) {}
}
document.addEventListener('visibilitychange', () => { if (!document.hidden) resume(); });
addEventListener('focus', resume);
addEventListener('pageshow', resume);
// A touch is the one thing iOS always accepts as permission to make noise again.
['touchend', 'click'].forEach(ev => document.addEventListener(ev, resume, { passive: true, capture: true }));

// ---------------------------------------------------------------- a promise this phone cannot keep
// "A siren sounds and your phone buzzes until you tap I'm safe." navigator.vibrate does not exist on iOS
// Safari, so on an iPhone the buzzing half has never once happened.
function honestSiren() {
  if (CAN_BUZZ) return;
  document.querySelectorAll('.card small.mute').forEach(el => {
    if (el.dataset.lv39 || !/buzzes/i.test(el.textContent)) return;
    el.dataset.lv39 = '1';
    el.textContent = el.textContent.replace(
      /A siren sounds and your phone buzzes until you tap/i,
      'A siren sounds until you tap');
  });
}
new MutationObserver(() => { try { honestSiren(); } catch (e) {} })
  .observe(document.body, { childList: true, subtree: true });
setTimeout(honestSiren, 600);
}
