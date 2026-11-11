/* GeoPick — one place picker for families, partners and admin.
   Full-screen map (Google in its normal colours when the key works, OpenStreetMap otherwise), a fixed pin with a
   callout, a search bar with suggestions (Google Places when enabled, our /api/v2/geo/search otherwise),
   "Use current location", and a card with the place name and a Confirm button.

   GeoPick.open({start:{lat,lng}, callout:'…', hint:'…', heading:'SELECT LOCATION', confirm:'Confirm location',
                 must:false, gps:true, serve:'lab'|'pharmacy'|'', onConfirm(pos, geo)})
   pos = {lat, lng, acc, moved}   acc: GPS accuracy in metres, 0 when placed by hand; moved: metres from the GPS fix
   geo = {title, area, city, state, pin, road, serve}                                                              */
(function () {
  "use strict";
  const H = { "x-tht": "1" };
  const get = async (u) => { const r = await fetch(u, { credentials: "same-origin", headers: H }); if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const km = (a, b) => { const R = 6371, dl = (b.lat - a.lat) * Math.PI / 180, dg = (b.lng - a.lng) * Math.PI / 180, x = Math.sin(dl / 2) ** 2 + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dg / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };

  // ---- Google Maps, loaded once, with the Places library; any key error falls back to OpenStreetMap for a day ----
  let G = null;
  const badKey = () => { try { return Date.now() - (+localStorage.getItem("uh-gm-bad") || 0) < 864e5; } catch (_) { return false; } };
  window.gm_authFailure = function () { G = false; try { localStorage.setItem("uh-gm-bad", String(Date.now())); } catch (_) {} document.querySelectorAll("[data-gp-map]").forEach((el) => el.__redo && el.__redo()); };
  async function google() {
    if (G !== null) return G;
    if (window.google && google.maps && google.maps.Map) return (G = google.maps);
    if (badKey()) return (G = false);
    try {
      const c = await get("/api/v1/config"), k = c.maps && c.maps.provider === "google" && c.maps.key;
      if (!k) return (G = false);
      await new Promise((res) => { window.__gpcb = res; const s = document.createElement("script"); s.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(k) + "&callback=__gpcb&loading=async&v=weekly"; s.async = true; s.onerror = () => res(); document.head.appendChild(s); setTimeout(res, 8000); });
      G = window.google && google.maps && google.maps.Map ? google.maps : false;
    } catch (_) { G = false; }
    return G;
  }

  // ---- the map: Google or a small OpenStreetMap tile viewer with drag and pinch-free zoom buttons ----
  async function mount(el, c, on, noG) {
    const g = noG ? false : await google();
    el.dataset.gpMap = 1;
    const api = { set() {}, get: () => c };
    el.__redo = () => { el.innerHTML = ""; mount(el, c, on, true).then((m) => { api.set = m.set; }); };
    if (g) {
      const m = new g.Map(el, { center: c, zoom: 17, disableDefaultUI: true, gestureHandling: "greedy", clickableIcons: false });
      m.addListener("dragstart", () => on.drag && on.drag());
      m.addListener("idle", () => { const p = m.getCenter(); c = { lat: p.lat(), lng: p.lng() }; on.move(c); });
      api.set = (p) => { m.panTo(p); if (m.getZoom() < 16) m.setZoom(17); };
      return api;
    }
    let Z = 17; const T = 256;
    const px = (lat, lng) => { const s = T * 2 ** Z, x = (lng + 180) / 360 * s, r = lat * Math.PI / 180, y = (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * s; return [x, y]; };
    const ll = (x, y) => { const s = T * 2 ** Z, lng = x / s * 360 - 180, n = Math.PI - 2 * Math.PI * y / s; return { lat: 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))), lng }; };
    let [cx, cy] = px(c.lat, c.lng), drag = null, tm = null;
    el.style.overflow = "hidden"; el.style.touchAction = "none"; el.style.background = "#EEF1F5";
    const draw = () => {
      const w = el.clientWidth || 360, h = el.clientHeight || 500, x0 = cx - w / 2, y0 = cy - h / 2, tx0 = Math.floor(x0 / T), ty0 = Math.floor(y0 / T); let s = "";
      for (let tx = tx0; tx * T < x0 + w; tx++) for (let ty = ty0; ty * T < y0 + h; ty++) s += `<img alt="" draggable="false" src="https://tile.openstreetmap.org/${Z}/${tx}/${ty}.png" style="position:absolute;left:${tx * T - x0}px;top:${ty * T - y0}px;width:${T}px;height:${T}px;user-select:none;pointer-events:none">`;
      el.innerHTML = s + '<div class="gp-zoom"><button type="button" data-z="1">+</button><button type="button" data-z="-1">−</button></div><span class="gp-osm">© OpenStreetMap</span>';
      el.querySelectorAll("[data-z]").forEach((b) => { b.onpointerdown = (e) => e.stopPropagation(); b.onclick = () => { const p = ll(cx, cy); Z = Math.max(12, Math.min(19, Z + +b.dataset.z)); [cx, cy] = px(p.lat, p.lng); draw(); }; });
    };
    const done = () => { clearTimeout(tm); tm = setTimeout(() => { c = ll(cx, cy); on.move(c); }, 300); };
    el.onpointerdown = (e) => { if (e.target.closest(".gp-zoom")) return; drag = [e.clientX, e.clientY]; el.setPointerCapture(e.pointerId); on.drag && on.drag(); };
    el.onpointermove = (e) => { if (!drag) return; cx -= e.clientX - drag[0]; cy -= e.clientY - drag[1]; drag = [e.clientX, e.clientY]; draw(); };
    el.onpointerup = el.onpointercancel = () => { if (drag) { drag = null; done(); } };
    draw(); setTimeout(() => on.move(c), 30);
    api.set = (p) => { [cx, cy] = px(p.lat, p.lng); draw(); done(); };
    return api;
  }

  // ---- search: the server tries Google Places (server key), then Photon, then Nominatim ----
  async function suggest(q, near) {
    const r = await get("/api/v2/geo/search?q=" + encodeURIComponent(q) + (near ? `&lat=${near.lat.toFixed(4)}&lng=${near.lng.toFixed(4)}` : ""));
    return (r.rows || []).slice(0, 6);
  }
  async function resolve(x) { return { lat: x.lat, lng: x.lng }; }

  const CSS = `.gp{position:fixed;inset:0;z-index:2000;background:#fff;display:flex;justify-content:center;font:15px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,system-ui,sans-serif;color:#1D1D1F}
.gp *{box-sizing:border-box}.gp-w{position:relative;width:100%;max-width:560px;height:100%;overflow:hidden;background:#EEF1F5}
.gp-map,.gp-pinbox{position:absolute;left:0;right:0;top:0;bottom:calc(var(--gp-ch,200px) - 22px)}.gp-map{z-index:0}.gp-pinbox{pointer-events:none;z-index:2}
.gp-bar{position:absolute;left:12px;right:12px;top:max(12px,env(safe-area-inset-top));display:flex;gap:8px;z-index:4}
.gp-rb{width:46px;height:46px;flex:none;border-radius:23px;border:0;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.16);display:grid;place-items:center;cursor:pointer;color:#1D1D1F}
.gp-sw{position:relative;flex:1;min-width:0}.gp-sw svg{position:absolute;left:15px;top:14px}
.gp-q{display:block;width:100%;height:46px;border-radius:23px;border:0;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.16);padding:0 40px 0 42px;font:inherit;font-size:16px;outline:0;color:#1D1D1F}
.gp-qx{position:absolute;right:8px;top:9px;width:28px;height:28px;border-radius:14px;border:0;background:#E5E5EA;color:#6E6E73;display:none;cursor:pointer}
.gp-res{position:absolute;left:12px;right:12px;top:calc(max(12px,env(safe-area-inset-top)) + 54px);background:#fff;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.2);z-index:5;max-height:min(60vh,420px);overflow:auto;display:none}
.gp-res button{display:flex;gap:12px;align-items:flex-start;width:100%;text-align:left;border:0;background:none;padding:12px 16px;border-top:1px solid #F0F0F2;font:inherit;cursor:pointer;color:#1D1D1F}.gp-res button:first-child{border-top:0}
.gp-res button:hover{background:#F5F5F7}.gp-res b{display:block;font-weight:600}.gp-res small{display:block;color:#86868B;font-size:13px;margin-top:1px}.gp-res .gp-ic{flex:none;width:30px;height:30px;border-radius:15px;background:#F2F2F7;display:grid;place-items:center;margin-top:1px}
.gp-empty{padding:14px 16px;color:#86868B;font-size:14px}
.gp-pin{position:absolute;left:50%;top:50%;transform:translate(-50%,-100%);display:flex;flex-direction:column;align-items:center;line-height:0;transition:transform .15s}.gp-pin.up{transform:translate(-50%,calc(-100% - 12px))}
.gp-tip{background:#1D1D1F;color:#fff;border-radius:10px;padding:8px 12px;font-size:13px;line-height:1.3;text-align:center;margin-bottom:9px;white-space:nowrap;position:relative;transition:opacity .15s}.gp-pin.up .gp-tip{opacity:0}
.gp-tip:after{content:"";position:absolute;left:50%;bottom:-5px;width:10px;height:10px;background:#1D1D1F;transform:translateX(-50%) rotate(45deg)}
.gp-sh{position:absolute;left:50%;top:50%;width:14px;height:5px;border-radius:50%;background:rgba(0,0,0,.35);transform:translate(-50%,-2px)}
.gp-me{position:absolute;left:50%;transform:translateX(-50%);bottom:calc(var(--gp-ch,200px) + 12px);z-index:3;border:1px solid #0071E3;color:#0071E3;background:#fff;border-radius:20px;padding:9px 16px;font:inherit;font-weight:600;font-size:14px;box-shadow:0 2px 12px rgba(0,0,0,.14);cursor:pointer;white-space:nowrap}
.gp-card{position:absolute;left:0;right:0;bottom:0;background:#fff;border-radius:22px 22px 0 0;box-shadow:0 -6px 24px rgba(0,0,0,.12);padding:18px 18px max(18px,env(safe-area-inset-bottom));z-index:3}
.gp-k{font-size:12px;font-weight:600;letter-spacing:.4px;color:#86868B}.gp-t{margin:2px 0 0;font-size:20px;font-weight:700;letter-spacing:-.3px;display:flex;gap:8px;align-items:center}
.gp-s{margin:3px 0 0;color:#6E6E73;font-size:14px}.gp-v{margin-top:9px;font-size:13.5px}.gp-warn{margin-top:9px;font-size:13px;color:#B25000}
.gp-ok{display:block;width:100%;margin-top:14px;height:52px;border:0;border-radius:26px;background:#0071E3;color:#fff;font:inherit;font-weight:600;font-size:17px;cursor:pointer}.gp-ok:disabled{opacity:.5}
.gp-zoom{position:absolute;right:12px;bottom:34px;display:flex;flex-direction:column;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.15);overflow:hidden;z-index:1}.gp-zoom button{width:40px;height:40px;border:0;background:#fff;font-size:20px;cursor:pointer}.gp-zoom button+button{border-top:1px solid #EEE}
.gp-osm{position:absolute;left:8px;bottom:28px;font-size:10px;background:rgba(255,255,255,.75);padding:1px 4px;border-radius:4px}
@media (min-width:700px){.gp{background:rgba(0,0,0,.45);align-items:center}.gp-w{height:min(92vh,860px);border-radius:22px;box-shadow:0 30px 80px rgba(0,0,0,.35)}}`;

  const PIN = '<svg width="42" height="54" viewBox="0 0 34 46"><path d="M17 1C8 1 1 8 1 17c0 12 16 28 16 28s16-16 16-28C33 8 26 1 17 1z" fill="#FF3B30"/><circle cx="17" cy="17" r="6" fill="#fff"/></svg>';
  const LOOK = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#86868B" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>';
  const DOT = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6E6E73" stroke-width="2"><path d="M12 21s-7-6-7-12a7 7 0 0114 0c0 6-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>';

  function open(o) {
    o = o || {};
    if (!document.getElementById("gp-css")) { const st = document.createElement("style"); st.id = "gp-css"; st.textContent = CSS; document.head.appendChild(st); }
    let pos = o.start && o.start.lat ? { lat: o.start.lat, lng: o.start.lng } : null, fix = null, geo = {}, M = null, seq = 0, approx = 0;
    const d = document.createElement("div"); d.className = "gp"; d.setAttribute("role", "dialog"); d.setAttribute("aria-label", o.heading || "Select location");
    d.innerHTML = `<div class="gp-w"><div class="gp-map"></div><div class="gp-pinbox"><div class="gp-sh"></div><div class="gp-pin"><div class="gp-tip"><b>${esc(o.callout || "Your location")}</b><br><span style="opacity:.75">${esc(o.hint || "Move the map to the exact spot")}</span></div>${PIN}</div></div>
      <div class="gp-bar">${o.must ? "" : `<button type="button" class="gp-rb" data-x aria-label="Back"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M15 6l-6 6 6 6"/></svg></button>`}
       <div class="gp-sw">${LOOK}<input class="gp-q" placeholder="Search area, street, building…" autocomplete="off" enterkeyhint="search"><button type="button" class="gp-qx" aria-label="Clear">✕</button></div></div>
      <div class="gp-res"></div>
      ${o.gps === false ? "" : '<button type="button" class="gp-me">◎ Use current location</button>'}
      <div class="gp-card"><div class="gp-k">${esc(o.heading || "SELECT LOCATION")}</div><div class="gp-t">${DOT.replace('stroke="#6E6E73"', 'stroke="#FF3B30"').replace('width="16" height="16"', 'width="22" height="22"')}<span>Finding the place…</span></div><div class="gp-s">&nbsp;</div><div class="gp-v"></div><div class="gp-warn" hidden></div>
       <button type="button" class="gp-ok" disabled>${esc(o.confirm || "Confirm location")}</button></div></div>`;
    document.body.appendChild(d);
    const $ = (s) => d.querySelector(s), card = $(".gp-card");
    const fit = () => d.style.setProperty("--gp-ch", card.offsetHeight + "px");
    const close = () => { d.remove(); document.removeEventListener("keydown", key); };
    const key = (e) => { if (e.key === "Escape" && !o.must) close(); };
    document.addEventListener("keydown", key);
    const x = $("[data-x]"); if (x) x.onclick = close;

    const show = () => {
      const t = geo.title || geo.road || geo.area || "Pinned location";
      $(".gp-t span").textContent = t;
      $(".gp-s").textContent = [geo.area && geo.area !== t ? geo.area : "", geo.city, geo.pin].filter(Boolean).join(", ") || "You can fill in the PIN next";
      const s = geo.serve, k = o.serve;
      $(".gp-v").innerHTML = !k || !s ? "" : (k === "pharmacy" ? s.pharmacies : s.labs) ? `<span style="color:#1A7F37;font-weight:600">● ${k === "pharmacy" ? "Delivery" : "Home collection"} available here</span>${s.homeHours ? ` <span style="color:#86868B">· ${esc(s.homeHours)}</span>` : ""}` : `<span style="color:#B25000;font-weight:600">● Not served here yet</span> <span style="color:#86868B">— you can still save it${s.nearestLab ? "; nearest lab " + s.nearestLab.km + " km" : ""}</span>`;
      const far = fix && pos ? Math.round(km(fix, pos) * 1000) : 0, w = $(".gp-warn");
      if (approx && far < 50) { w.hidden = false; w.textContent = `This device only knows roughly where you are (within ${approx >= 1000 ? (approx / 1000).toFixed(1) + " km" : approx + " m"}). Search your building or street above, then move the map onto your door.`; }
      else if (o.maxMove && fix && !approx && far > o.maxMove) { w.hidden = false; w.textContent = `The pin is ${far} m from where your phone is. Put it on the ${o.what || "door"} itself.`; } else w.hidden = true;
      $(".gp-ok").disabled = false; fit();
    };
    const move = async (p) => {
      pos = p; const my = ++seq; $(".gp-pin").classList.remove("up"); $(".gp-t span").textContent = "Finding the place…"; $(".gp-ok").disabled = true;
      try { const g = await get(`/api/v2/geo/reverse?lat=${p.lat.toFixed(6)}&lng=${p.lng.toFixed(6)}`); if (my !== seq) return; geo = g || {}; } catch (_) { if (my !== seq) return; geo = {}; }
      show();
    };
    const drag = () => { $(".gp-pin").classList.add("up"); $(".gp-res").style.display = "none"; };

    const me = (quiet) => {
      const b = $(".gp-me"); if (!navigator.geolocation) { if (!quiet) alert("Location is not available on this device."); return; }
      if (b) b.textContent = "Locating…";
      navigator.geolocation.getCurrentPosition((p) => {
        if (b) b.textContent = "◎ Use current location";
        fix = { lat: p.coords.latitude, lng: p.coords.longitude, acc: Math.round(p.coords.accuracy) };
        // Laptops and desktops have no GPS: the browser guesses from Wi-Fi or the internet connection, often kilometres off.
        approx = fix.acc > 150 ? fix.acc : 0;
        try { sessionStorage.setItem("gp-last", JSON.stringify(fix)); } catch (_) {}
        M && M.set(fix);
        if (approx) setTimeout(() => q.focus(), 400);
      }, (e) => { if (b) b.textContent = "◎ Use current location"; if (!quiet) alert(e.code === 1 ? "Location is blocked. Allow it for this site in the browser, or search and move the map yourself." : "Couldn't get your location. Search or move the map instead."); }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 });
    };
    if ($(".gp-me")) $(".gp-me").onclick = () => me(false);

    let last = null; try { last = JSON.parse(sessionStorage.getItem("gp-last") || "null"); } catch (_) {}
    const start = pos || last || { lat: 17.385, lng: 78.4867 };
    mount($(".gp-map"), start, { move, drag }).then((m) => { M = m; });
    if (!pos && o.gps !== false) me(true);

    // search
    const q = $(".gp-q"), res = $(".gp-res"), qx = $(".gp-qx"); let tm = null, rows = [];
    const render = (txt) => {
      if (!rows.length) { res.innerHTML = `<div class="gp-empty">${txt || "No places found. Try the area or a nearby landmark, then move the map."}</div>`; res.style.display = ""; return; }
      res.innerHTML = rows.map((r, i) => `<button type="button" data-i="${i}"><span class="gp-ic">${DOT}</span><span style="min-width:0"><b>${esc(r.title || r.area)}</b><small>${esc(r.sub || [r.area, r.city, r.pin].filter(Boolean).join(", "))}</small></span></button>`).join("");
      res.style.display = "";
      res.querySelectorAll("[data-i]").forEach((b) => b.onclick = async () => { const r = rows[+b.dataset.i]; res.style.display = "none"; q.value = ""; qx.style.display = "none"; q.blur(); const p = await resolve(r); if (p) M && M.set(p); });
    };
    q.oninput = () => {
      clearTimeout(tm); const v = q.value.trim(); qx.style.display = v ? "block" : "none";
      if (v.length < 3) { res.style.display = "none"; return; }
      tm = setTimeout(async () => { try { rows = await suggest(v, pos); } catch (_) { rows = []; } if (q.value.trim() === v) render(); }, 300);
    };
    q.onkeydown = (e) => { if (e.key === "Enter" && rows[0]) { e.preventDefault(); res.querySelector("[data-i]").click(); } };
    q.onfocus = () => { if (rows.length && q.value.trim().length >= 3) res.style.display = ""; };
    qx.onclick = () => { q.value = ""; qx.style.display = "none"; res.style.display = "none"; q.focus(); };

    $(".gp-ok").onclick = () => {
      if (!pos) return;
      const moved = fix ? Math.round(km(fix, pos) * 1000) : null;
      const out = { lat: +pos.lat.toFixed(6), lng: +pos.lng.toFixed(6), acc: fix && moved != null && moved < 30 ? fix.acc : 0, moved };
      if (o.keepOpen) o.onConfirm && o.onConfirm(out, geo, close); else { close(); o.onConfirm && o.onConfirm(out, geo); }
    };
    fit();
    return { close };
  }
  window.GeoPick = { open, google };
})();
