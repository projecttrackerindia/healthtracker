/* Urban Health — the sign-in stage shared by /app, /partner and /join.
   A heart of light that gathers, beats and parts around the cursor or finger, with the brand line and the app
   downloads. One canvas is kept for the whole visit and moved into each new screen, so stepping from "mobile" to
   "code" to "password" never restarts the animation.

   UHFX.stage(host, kind)   kind: "user" | "partner"   fills host with the stage and starts the heart
   UHFX.apps(kind)          HTML for the Android download and the iPhone note (empty inside the Android app)
   UHFX.banner(kind)        on Android browsers, a dismissible "Get the app" bar at the top of the page
   UHFX.inApp()             true when the page runs inside the Android app
   UHFX.guide(pw, fails)    one guided line for a password field: {pct, tone, text}  (see below)
*/
(function () {
  'use strict';
  if (window.UHFX) return;
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ANDROID = /Android/i.test(navigator.userAgent);
  // the Android apps launch /app?src=android and /partner?src=android; remember it for the rest of the visit
  try { if (/[?&]src=android\b/.test(location.search) || /^android-app:/.test(document.referrer)) localStorage.setItem('uh-twa', '1'); } catch (_) {}
  const inApp = () => { try { return localStorage.getItem('uh-twa') === '1'; } catch (_) { return false; } };

  const APK = { user: '/download/urbanhealth.apk', partner: '/download/urbanhealth-partner.apk' };
  const NAME = { user: 'Urban Health', partner: 'Urban Health Partner' };
  const MARK = '<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="16" fill="currentColor"/><path d="M21.5 15a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4v34a4 4 0 0 1-4 4h-3a4 4 0 0 1-4-4V37.5H13a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h8.5z" fill="#fff"/><path d="M32 32h5l3.2-8 4.6 16 3.2-8h.4" fill="none" stroke="#fff" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/><circle cx="55.2" cy="32" r="3.3" fill="#fff"/></svg>';
  const DROID = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M17.6 9.5l1.8-3.1a.4.4 0 0 0-.7-.4l-1.8 3.1a11 11 0 0 0-9.8 0L5.3 6a.4.4 0 0 0-.7.4l1.8 3.1A10.4 10.4 0 0 0 1 18h22a10.4 10.4 0 0 0-5.4-8.5zM7 15.3a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm10 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/></svg>';
  const APPLE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16.4 12.6c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.9-3.5.9s-1.8-.9-3-.8C7 7.4 5.6 8.3 4.8 9.7c-1.6 2.8-.4 6.9 1.1 9.2.8 1.1 1.7 2.3 2.9 2.3 1.2-.1 1.6-.8 3-.8s1.8.8 3 .7c1.3 0 2-1.1 2.8-2.2.9-1.3 1.2-2.5 1.3-2.6-.1 0-2.5-.9-2.5-3.7zM14.2 5.8c.6-.8 1.1-1.8 1-2.8-.9 0-2 .6-2.7 1.4-.6.7-1.1 1.7-1 2.7 1 .1 2-.5 2.7-1.3z"/></svg>';

  const COPY = {
    user: { h: "Your family's health,<br>in one secure place.", p: 'Reports explained, medicines on time, and help one tap away.' },
    partner: { h: 'Every booking, visit<br>and report. One place.', p: 'For verified labs, sample-collection technicians, pharmacies and clinics.' }
  };

  /* ---------------------------------------------------------------- styles (injected once) */
  const css = `
.ufx{position:relative;overflow:hidden;color:#F5F5F7;background:#000;isolation:isolate;font-family:inherit}
.ufx::before{content:"";position:absolute;inset:-20%;z-index:-1;background:radial-gradient(42% 38% at 50% 44%,var(--ufx-a) 0%,transparent 70%),radial-gradient(40% 40% at 70% 70%,var(--ufx-b) 0%,transparent 72%);opacity:.55;animation:ufxBreath 9s ease-in-out infinite}
.ufx.user{--ufx-a:rgba(47,91,255,.55);--ufx-b:rgba(19,181,163,.28)}
.ufx.partner{--ufx-a:rgba(14,155,140,.55);--ufx-b:rgba(47,91,255,.25)}
@keyframes ufxBreath{50%{transform:scale(1.06);opacity:.7}}
.ufx-cv{position:absolute;inset:0;z-index:0}
.ufx-cv canvas{display:block;width:100%;height:100%;touch-action:pan-y}
.ufx-copy{position:absolute;left:0;right:0;bottom:0;z-index:1;padding:0 clamp(28px,6vw,88px) clamp(32px,7vh,72px);pointer-events:none;
 background:linear-gradient(180deg,transparent,rgba(0,0,0,.55) 38%,rgba(0,0,0,.85))}
.ufx-copy a,.ufx-copy button{pointer-events:auto}
.ufx-logo{position:absolute;z-index:2;left:clamp(28px,6vw,88px);top:clamp(24px,5vh,48px);display:inline-flex;align-items:center;gap:10px;color:#fff;text-decoration:none;font-weight:600;font-size:18px;letter-spacing:-.01em}
.ufx-logo svg{width:30px;height:30px;color:#2F5BFF}.ufx.partner .ufx-logo svg{color:#0E9B8C}
.ufx-logo small{font-weight:500;color:rgba(255,255,255,.55);font-size:13px;margin-left:2px;padding-left:10px;border-left:1px solid rgba(255,255,255,.2)}
.ufx-copy h2{margin:0 0 12px;font-size:clamp(30px,3.3vw,46px);line-height:1.06;letter-spacing:-.035em;font-weight:700;color:#fff}
.ufx-copy p{margin:0 0 26px;max-width:420px;font-size:16.5px;line-height:1.5;color:rgba(235,235,245,.72)}
.ufx-apps{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.ufx-dl{display:inline-flex;align-items:center;gap:10px;height:46px;padding:0 18px 0 14px;border-radius:23px;background:rgba(255,255,255,.12);color:#fff;text-decoration:none;font-size:14.5px;font-weight:600;
 box-shadow:inset 0 0 0 1px rgba(255,255,255,.16);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);transition:background .25s,transform .25s}
.ufx-dl:hover{background:rgba(255,255,255,.2);transform:translateY(-1px)}
.ufx-dl svg{width:20px;height:20px;color:#3DDC84}
.ufx-dl span{display:flex;flex-direction:column;line-height:1.1}.ufx-dl small{font-size:11px;font-weight:500;color:rgba(255,255,255,.6)}
.ufx-ios{display:inline-flex;align-items:center;gap:8px;font-size:13.5px;color:rgba(235,235,245,.6)}.ufx-ios svg{width:16px;height:16px}
.ufx-bar{position:fixed;left:10px;right:10px;top:calc(10px + env(safe-area-inset-top));z-index:2147483000;display:flex;align-items:center;gap:12px;padding:10px 10px 10px 12px;border-radius:20px;
 background:rgba(28,28,30,.92);color:#fff;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);box-shadow:0 18px 40px -16px rgba(0,0,0,.6);animation:ufxDrop .5s cubic-bezier(.2,.8,.2,1) both;font:inherit}
@keyframes ufxDrop{from{transform:translateY(-120%);opacity:0}}
.ufx-bar i{width:38px;height:38px;flex:none;display:grid;place-items:center}.ufx-bar i svg{width:38px;height:38px;color:#2F5BFF}.ufx-bar.partner i svg{color:#0E9B8C}
.ufx-bar b{display:block;font-size:14.5px}.ufx-bar span{flex:1;font-size:12.5px;color:rgba(235,235,245,.65);line-height:1.3}
.ufx-bar a{height:34px;padding:0 16px;border-radius:17px;background:#0A84FF;color:#fff;font-weight:600;font-size:14px;display:inline-flex;align-items:center;text-decoration:none}
.ufx-bar.partner a{background:#0E9B8C}
.ufx-bar button{width:30px;height:30px;border:0;border-radius:15px;background:rgba(255,255,255,.1);color:#fff;font-size:15px;cursor:pointer}
@media (max-width:899px){
 .ufx-logo{left:22px;top:calc(18px + env(safe-area-inset-top))}
 .ufx-copy{padding:0 22px 52px;background:linear-gradient(180deg,transparent,rgba(0,0,0,.6))}
 .ufx-copy h2{font-size:clamp(25px,7vw,30px);margin-bottom:0}
 .ufx-copy p,.ufx-copy .ufx-apps{display:none}
}
@media (prefers-reduced-motion:reduce){.ufx::before{animation:none}}
`;
  function styleOnce() {
    if (document.getElementById('ufx-css')) return;
    const s = document.createElement('style'); s.id = 'ufx-css'; s.textContent = css; document.head.appendChild(s);
  }

  /* ---------------------------------------------------------------- the heart of light */
  const FX = { cv: null, ctx: null, raf: 0, P: null, W: 0, H: 0, dpr: 1, mx: -1e4, my: -1e4, t0: 0, kind: 'user', ro: null };

  function heartPoint(t) { // classic parametric heart, y up
    const s = Math.sin(t);
    return [16 * s * s * s, 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)];
  }
  function buildShape(n) {
    // 45% on the outline (crisp silhouette), 55% filling it, weighted towards the edge so it reads as volume
    const pts = [];
    const outline = Math.round(n * 0.45);
    for (let i = 0; i < outline; i++) { const p = heartPoint(Math.random() * Math.PI * 2); pts.push([p[0] + (Math.random() - .5) * .5, p[1] + (Math.random() - .5) * .5]); }
    while (pts.length < n) {
      const p = heartPoint(Math.random() * Math.PI * 2), k = Math.pow(Math.random(), .45);
      pts.push([p[0] * k, p[1] * k + (1 - k) * 2]);
    }
    return pts;
  }
  function sprite(rgb) {
    const c = document.createElement('canvas'); c.width = c.height = 32; const g = c.getContext('2d');
    const gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
    gr.addColorStop(0, `rgba(${rgb},1)`); gr.addColorStop(.25, `rgba(${rgb},.55)`); gr.addColorStop(1, `rgba(${rgb},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 32, 32); return c;
  }
  let SPR = null;
  function sprites() {
    if (SPR) return SPR;
    SPR = { blue: sprite('92,128,255'), teal: sprite('40,214,190'), white: sprite('235,240,255'), rose: sprite('255,120,150') };
    return SPR;
  }

  function init() {
    const cv = document.createElement('canvas'); const ctx = cv.getContext('2d');
    FX.cv = cv; FX.ctx = ctx;
    const small = innerWidth < 900 || (navigator.hardwareConcurrency || 4) <= 4;
    const N = small ? 900 : 1700;
    const shape = buildShape(N);
    FX.P = shape.map(([x, y], i) => {
      const a = Math.random() * Math.PI * 2, r = 30 + Math.random() * 40;
      return { hx: x, hy: y, x: Math.cos(a) * r, y: Math.sin(a) * r, vx: 0, vy: 0, ph: Math.random() * Math.PI * 2, sz: .55 + Math.random() * .9,
        delay: Math.random() * .9, c: Math.random() };
    });
    // dust that drifts through the whole stage
    FX.D = Array.from({ length: small ? 60 : 120 }, () => ({ x: Math.random(), y: Math.random(), v: .00004 + Math.random() * .00012, s: .4 + Math.random() * .9, ph: Math.random() * 6 }));
    const move = (x, y) => { const r = cv.getBoundingClientRect(); FX.mx = x - r.left; FX.my = y - r.top; };
    cv.addEventListener('pointermove', e => move(e.clientX, e.clientY), { passive: true });
    cv.addEventListener('pointerdown', e => { move(e.clientX, e.clientY); FX.burst = performance.now(); }, { passive: true });
    cv.addEventListener('pointerleave', () => { FX.mx = FX.my = -1e4; });
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); else start(); });
    FX.ro = new ResizeObserver(size);
  }
  function size() {
    const cv = FX.cv; if (!cv || !cv.isConnected) return;
    const r = cv.parentElement.getBoundingClientRect(); FX.dpr = Math.min(devicePixelRatio || 1, 2);
    FX.W = r.width; FX.H = r.height; cv.width = Math.max(1, r.width * FX.dpr); cv.height = Math.max(1, r.height * FX.dpr);
    if (RM) frame(performance.now(), true);
  }
  function beat(t) { // lub-dub every 1.25 s
    const p = (t % 1250) / 1250;
    const a = Math.exp(-Math.pow((p - .08) / .045, 2)), b = Math.exp(-Math.pow((p - .26) / .05, 2)) * .6;
    return a + b;
  }
  function frame(now, once) {
    const { ctx, P, W, H, dpr } = FX; if (!ctx || !W) return;
    const t = now - FX.t0, intro = RM ? 1 : Math.min(1, t / 1800);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    const mobile = W < 900 && H < 520;
    // the heart sits in the upper middle on desktop (copy is below it), centred on the phone banner
    const cx = W / 2, cy = mobile ? H * .44 : H * .4;
    const sc = Math.min(W, H * (mobile ? 1.3 : 1)) / (mobile ? 46 : 52);
    const b = RM ? 0 : beat(now), pulse = 1 + b * .045;
    const S = sprites(), teal = FX.kind === 'partner';
    if (!FX.placed && !once) { FX.placed = true; for (const q of P) { q.x = cx + q.x * sc * .5; q.y = cy + q.y * sc * .5; } }
    const burst = FX.burst ? Math.max(0, 1 - (now - FX.burst) / 700) : 0;
    for (let i = 0; i < P.length; i++) {
      const p = P[i];
      const e = RM ? 1 : Math.min(1, Math.max(0, (intro - p.delay * .5) / .5)), ee = 1 - Math.pow(1 - e, 3);
      // a slow orbit around each home point keeps the heart alive without losing its outline
      const wob = RM ? 0 : .35, ox = Math.cos(now * .0007 + p.ph) * wob, oy = Math.sin(now * .0009 + p.ph * 1.3) * wob;
      const tx = cx + (p.hx * pulse + ox) * sc, ty = cy - (p.hy * pulse + oy) * sc;
      if (once || RM) { p.x = tx; p.y = ty; }
      else {
        // spring towards home, weaving in from the scatter during the intro
        const k = .018 + .05 * ee;
        p.vx += (tx - p.x) * k; p.vy += (ty - p.y) * k;
        const dx = p.x - FX.mx, dy = p.y - FX.my, d2 = dx * dx + dy * dy, R = mobile ? 70 : 110;
        if (d2 < R * R) { const d = Math.sqrt(d2) || 1, f = (1 - d / R) * (2.4 + burst * 6); p.vx += dx / d * f - dy / d * f * .35; p.vy += dy / d * f + dx / d * f * .35; }
        p.vx *= .82; p.vy *= .82; p.x += p.vx; p.y += p.vy;
      }
      const tw = .55 + .45 * Math.sin(now * .002 + p.ph * 3);
      const spr = p.c < (teal ? .25 : .62) ? S.blue : p.c < .92 ? S.teal : S.white;
      const z = (p.sz * (2.2 + b * 1.4) * (mobile ? .85 : 1)) * (.8 + tw * .4);
      ctx.globalAlpha = Math.min(1, .35 + tw * .5 + b * .3) * (.2 + .8 * ee);
      ctx.drawImage(spr, p.x - z * 2, p.y - z * 2, z * 4, z * 4);
    }
    // dust
    for (const d of FX.D) {
      if (!RM && !once) { d.y -= d.v * 16; if (d.y < -.02) { d.y = 1.02; d.x = Math.random(); } }
      ctx.globalAlpha = .18 + .18 * Math.sin(now * .001 + d.ph);
      const z = d.s * 2.4; ctx.drawImage(S.white, d.x * W - z, d.y * H - z, z * 2, z * 2);
    }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  }
  function loop(now) { if (!FX.cv || !FX.cv.isConnected) { FX.raf = 0; return; } frame(now); FX.raf = requestAnimationFrame(loop); }
  function start() { if (RM || FX.raf || !FX.cv || !FX.cv.isConnected || document.hidden) return; FX.raf = requestAnimationFrame(loop); }
  function stop() { cancelAnimationFrame(FX.raf); FX.raf = 0; }

  /* ---------------------------------------------------------------- public pieces */
  function apps(kind) {
    kind = kind === 'partner' ? 'partner' : 'user';
    if (inApp()) return '';
    return `<div class="ufx-apps"><a class="ufx-dl" href="${APK[kind]}" download>${DROID}<span><small>Download for</small>Android</span></a>` +
      `<span class="ufx-ios">${APPLE}iPhone app coming soon</span></div>`;
  }
  function stage(host, kind) {
    kind = kind === 'partner' ? 'partner' : 'user';
    styleOnce();
    if (!FX.cv) { init(); FX.t0 = performance.now(); }
    FX.kind = kind;
    host.classList.add('ufx', kind);
    const c = COPY[kind];
    host.innerHTML = `<div class="ufx-cv"></div><a class="ufx-logo" href="/">${MARK}Urban Health${kind === 'partner' ? '<small>Partners</small>' : ''}</a>` +
      `<div class="ufx-copy"><h2>${c.h}</h2><p>${c.p}</p>${apps(kind)}</div>`;
    host.querySelector('.ufx-cv').appendChild(FX.cv);
    FX.ro.disconnect(); FX.ro.observe(host);
    size(); start();
  }
  function banner(kind) {
    kind = kind === 'partner' ? 'partner' : 'user';
    if (!ANDROID || inApp()) return;
    try { if (sessionStorage.getItem('uh-bar-' + kind)) return; } catch (_) {}
    styleOnce();
    if (document.querySelector('.ufx-bar')) return;
    const d = document.createElement('div'); d.className = 'ufx-bar ' + kind; d.setAttribute('role', 'region'); d.setAttribute('aria-label', 'Get the app');
    d.innerHTML = `<i>${MARK}</i><span><b>${NAME[kind]}</b>Faster, with notifications. Free.</span><a href="${APK[kind]}" download>Get</a><button aria-label="Not now">✕</button>`;
    d.querySelector('button').onclick = () => { d.remove(); try { sessionStorage.setItem('uh-bar-' + kind, '1'); } catch (_) {} };
    document.body.appendChild(d);
  }

  /* ---------------------------------------------------------------- guided password
     Instead of a checklist, one line that always says the next useful thing, and a bar that fills as it gets
     stronger. `fails` is the list of unmet rules as {k, text} in priority order; the caller keeps enforcing them. */
  function guide(pw, fails, strong) {
    if (!pw) return { pct: 0, tone: '', text: 'Use 12 or more characters. Three random words work well, like <b>mango river kite 82</b>.' };
    if (fails.length) {
      const f = fails[0];
      const left = Math.max(0, 12 - pw.length);
      const pct = Math.max(8, Math.min(70, (pw.length / 12) * 55 - (fails.length - 1) * 8));
      return { pct, tone: fails.length > 2 ? 'low' : 'mid', text: f.k === 'len' ? `Keep going: ${left} more character${left === 1 ? '' : 's'}.` : f.text };
    }
    return strong ? { pct: 100, tone: 'ok', text: 'Strong password. You’re all set.' } : { pct: 82, tone: 'ok', text: 'Good password. A few more characters make it even stronger.' };
  }
  const GCSS = `.uguide{margin:10px 2px 0}.uguide .ubar{height:4px;border-radius:2px;background:rgba(120,120,128,.18);overflow:hidden}
.uguide .ubar i{display:block;height:100%;width:0;border-radius:2px;background:#FF9F0A;transition:width .45s cubic-bezier(.2,.8,.2,1),background .3s}
.uguide[data-t=low] .ubar i{background:#FF453A}.uguide[data-t=ok] .ubar i{background:#30D158}
.uguide p{display:flex;gap:8px;align-items:flex-start;margin:8px 0 0;font-size:13.5px;line-height:1.4;color:#6E6E73}
.uguide p b{color:#1D1D1F;font-weight:600}
.uguide[data-t=ok] p{color:#1A7F37}.uguide p svg{width:16px;height:16px;flex:none;margin-top:1px}
.uguide p .ug{animation:ugIn .3s ease both}@keyframes ugIn{from{opacity:0;transform:translateY(3px)}}`;
  function paint(box, g) {
    if (!document.getElementById('ufx-g')) { const s = document.createElement('style'); s.id = 'ufx-g'; s.textContent = GCSS; document.head.appendChild(s); }
    box.classList.add('uguide'); box.dataset.t = g.tone; box.setAttribute('aria-live', 'polite');
    if (!box.querySelector('.ubar')) box.innerHTML = '<div class="ubar"><i></i></div><p></p>';
    box.querySelector('.ubar i').style.width = g.pct + '%';
    const p = box.querySelector('p'), icon = g.tone === 'ok' ? '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="8" fill="#30D158"/><path d="M4.6 8.3l2.2 2.2 4.6-4.8" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>' : '';
    const html = icon + `<span class="ug">${g.text}</span>`;
    if (p.dataset.h !== html) { p.dataset.h = html; p.innerHTML = html; }
  }
  // a passphrase that meets every rule: Word-word-word-NN!
  const WORDS = 'mango river kite amber cedar falcon harbor lotus meadow orbit pepper quartz saffron tulip velvet willow zephyr basil comet ember'.split(' ');
  function suggest() {
    const r = n => { const a = new Uint32Array(1); crypto.getRandomValues(a); return a[0] % n; };
    const w = () => WORDS[r(WORDS.length)];
    let a = w(), b = w(), c = w(); while (b === a) b = w(); while (c === a || c === b) c = w();
    return a[0].toUpperCase() + a.slice(1) + '-' + b + '-' + c + '-' + (10 + r(89)) + '!#%'[r(3)];
  }

  window.UHFX = { stage, apps, banner, inApp, guide, paint, suggest };
})();
