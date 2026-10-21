/* Urban Health · browser auth helper (landing page + app). No dependencies.
   THT.api(path, body)            → JSON (throws Error with .status and server message)
   THT.passkey.supported()        → bool
   THT.passkey.conditional()      → Promise<bool>  (autofill UI available)
   THT.passkey.register(name)     → registers a passkey for the signed-in user
   THT.passkey.signin({id, conditional, signal}) → signs in, returns {user}
   THT.pw.rules(pw, ctx)          → [{k, label, ok}] same rules the server enforces
   THT.pw.score(pw, ctx)          → {score 0..4, label, bits}
*/
(function () {
  const H = { 'content-type': 'application/json', 'x-tht': '1' };
  async function api(path, body, method) {
    const r = await fetch('/api/v1/auth' + path, { method: method || (body === undefined ? 'GET' : 'POST'), headers: H, credentials: 'same-origin', body: body === undefined ? undefined : JSON.stringify(body) });
    let j = {}; try { j = await r.json() } catch (e) { }
    if (!r.ok) { const m = j && j.detail; const e = new Error(typeof m === 'string' ? m : Array.isArray(m) ? (m[0] && m[0].msg) || 'Check the form' : 'Something went wrong (' + r.status + ')'); e.status = r.status; throw e }
    return j;
  }
  // ---- base64url ↔ ArrayBuffer
  const b2u = b => { const s = String.fromCharCode(...new Uint8Array(b)); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '') };
  const u2b = s => { s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; const b = atob(s), a = new Uint8Array(b.length); for (let i = 0; i < b.length; i++)a[i] = b.charCodeAt(i); return a.buffer };
  const toCreate = o => window.PublicKeyCredential && PublicKeyCredential.parseCreationOptionsFromJSON ? PublicKeyCredential.parseCreationOptionsFromJSON(o) :
    Object.assign({}, o, { challenge: u2b(o.challenge), user: Object.assign({}, o.user, { id: u2b(o.user.id) }), excludeCredentials: (o.excludeCredentials || []).map(c => Object.assign({}, c, { id: u2b(c.id) })) });
  const toGet = o => window.PublicKeyCredential && PublicKeyCredential.parseRequestOptionsFromJSON ? PublicKeyCredential.parseRequestOptionsFromJSON(o) :
    Object.assign({}, o, { challenge: u2b(o.challenge), allowCredentials: (o.allowCredentials || []).map(c => Object.assign({}, c, { id: u2b(c.id) })) });
  const credJSON = c => {
    if (c.toJSON) try { return c.toJSON() } catch (e) { }
    const r = c.response, o = { id: c.id, rawId: b2u(c.rawId), type: c.type, clientExtensionResults: c.getClientExtensionResults ? c.getClientExtensionResults() : {}, authenticatorAttachment: c.authenticatorAttachment || undefined, response: { clientDataJSON: b2u(r.clientDataJSON) } };
    if (r.attestationObject) { o.response.attestationObject = b2u(r.attestationObject); if (r.getTransports) o.response.transports = r.getTransports() }
    if (r.authenticatorData) { o.response.authenticatorData = b2u(r.authenticatorData); o.response.signature = b2u(r.signature); if (r.userHandle) o.response.userHandle = b2u(r.userHandle) }
    return o;
  };
  const friendly = e => {
    if (!e) return 'Passkey failed';
    if (e.name === 'NotAllowedError') return 'The passkey request was cancelled or timed out.';
    if (e.name === 'InvalidStateError') return 'This device already has a passkey for your account.';
    if (e.name === 'SecurityError') return 'Passkeys need a secure (https) address on this site.';
    if (e.name === 'AbortError') return 'aborted';
    return e.message || String(e);
  };
  const passkey = {
    supported: () => !!(window.PublicKeyCredential && navigator.credentials && navigator.credentials.create),
    conditional: async () => { try { return !!(window.PublicKeyCredential && PublicKeyCredential.isConditionalMediationAvailable && await PublicKeyCredential.isConditionalMediationAvailable()) } catch (e) { return false } },
    platform: async () => { try { return !!(window.PublicKeyCredential && await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()) } catch (e) { return false } },
    async register(name) {
      const { flow, options } = await api('/passkey/register/options', {});
      let c; try { c = await navigator.credentials.create({ publicKey: toCreate(options) }) } catch (e) { throw new Error(friendly(e)) }
      return api('/passkey/register/verify', { flow, credential: credJSON(c), name: name || '' });
    },
    async signin({ id = '', conditional = false, signal } = {}) {
      const { flow, options, known } = await api('/passkey/login/options', { id });
      if (known === false && !conditional) { const e = new Error('No passkey is set up for this account yet. Sign in with your password or a one-time code once, and the app will offer to set up Face ID or fingerprint sign-in.'); e.code = 'nopasskey'; throw e }
      let c; try { c = await navigator.credentials.get(Object.assign({ publicKey: toGet(options) }, conditional ? { mediation: 'conditional' } : {}, signal ? { signal } : {})) } catch (e) { throw new Error(friendly(e)) }
      if (!c) throw new Error('No passkey chosen');
      return api('/passkey/login/verify', { flow, credential: credJSON(c) });
    }
  };
  // ---- password rules: keep in sync with api/passwords.py
  const COMMON = 'password passw0rd password1 password123 p@ssw0rd 123456 12345678 123456789 qwerty qwerty123 iloveyou admin admin123 welcome welcome123 letmein monkey dragon sunshine princess football cricket abc123 india india123 hyderabad krishna sairam health healthy doctor changeme secret test123 urbanhealth healthtracker'.split(' ');
  const SEQ = ['abcdefghijklmnopqrstuvwxyz', '0123456789', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
  function hasRun(low) { for (const s of SEQ) for (let i = 0; i + 4 <= s.length; i++) { const t = s.slice(i, i + 4); if (low.includes(t) || low.includes([...t].reverse().join(''))) return true } return false }
  function personal(pw, ctx = {}) {
    const low = pw.toLowerCase(), bits = ((ctx.name || '') + ' ' + (ctx.email || '').split('@')[0]).toLowerCase().split(/[\s@._+-]+/).filter(b => b.length >= 3), d = (ctx.phone || '').replace(/\D/g, '');
    return bits.some(b => low.includes(b)) || (d.length >= 6 && pw.includes(d.slice(-6)));
  }
  function rules(pw, ctx) {
    const low = pw.toLowerCase(), core = low.replace(/[\d!@#$%^&*]+$/, '');
    return [
      { k: 'len', label: '12 or more characters', ok: pw.length >= 12 && pw.length <= 128 },
      { k: 'up', label: 'An upper-case letter (A–Z)', ok: /[A-Z]/.test(pw) },
      { k: 'lo', label: 'A lower-case letter (a–z)', ok: /[a-z]/.test(pw) },
      { k: 'num', label: 'A number (0–9)', ok: /\d/.test(pw) },
      { k: 'sym', label: 'A symbol such as ! @ # $ %', ok: /[^A-Za-z0-9]/.test(pw) },
      { k: 'rep', label: 'No 3 identical characters in a row', ok: !!pw && !/(.)\1\1/.test(pw) },
      { k: 'seq', label: 'No runs like 1234, abcd or qwer', ok: !!pw && !hasRun(low) },
      { k: 'per', label: 'Not your name, email or phone', ok: !!pw && !personal(pw, ctx) },
      { k: 'com', label: 'Not a common password', ok: !!pw && !COMMON.includes(low) && !COMMON.includes(core) }
    ];
  }
  function score(pw, ctx) {
    if (!pw) return { score: 0, label: '', bits: 0 };
    let pool = 0; if (/[a-z]/.test(pw)) pool += 26; if (/[A-Z]/.test(pw)) pool += 26; if (/\d/.test(pw)) pool += 10; if (/[^A-Za-z0-9]/.test(pw)) pool += 33;
    let bits = pw.length * Math.log2(Math.max(pool, 1));
    const fails = rules(pw, ctx).filter(r => !r.ok).length; bits -= fails * 12; if (/(.)\1/.test(pw)) bits -= 4;
    const s = bits < 40 ? 0 : bits < 55 ? 1 : bits < 70 ? 2 : bits < 90 ? 3 : 4;
    const capped = fails ? Math.min(s, 1) : Math.max(s, 2);
    return { score: capped, bits: Math.max(0, Math.round(bits)), label: ['Very weak', 'Weak', 'Good', 'Strong', 'Excellent'][capped] };
  }
  function generate() { // 4 words-ish + digits + symbol, meets every rule
    const A = 'amber,basil,cedar,delta,ember,fable,glade,harbor,indigo,jasper,kestrel,lumen,meadow,nectar,orbit,pebble,quartz,raven,saffron,tundra,umber,velvet,willow,zephyr'.split(','), S = '!@#$%&*?';
    const rnd = n => { const a = new Uint32Array(1); crypto.getRandomValues(a); return a[0] % n };
    const cap = w => w[0].toUpperCase() + w.slice(1);
    let p; do { p = cap(A[rnd(A.length)]) + S[rnd(S.length)] + A[rnd(A.length)] + (10 + rnd(89)) + S[rnd(S.length)] + cap(A[rnd(A.length)]) } while (rules(p, {}).some(r => !r.ok));
    return p;
  }
  // ---- mobile codes through Firebase Phone Authentication (when the server says so in /auth/config → firebase).
  //      The SMS is sent and checked by Google; the browser then hands the server an ID token in place of the 6-digit code.
  //      Flow: a start call answers {firebase:true, phone} → THT.phone.send(phone) → person types the SMS code → THT.phone.token(code) → verify with {firebaseToken}.
  const FB_V = '10.14.1';
  let fbReady = null, fbConfirm = null, fbVerifier = null;
  const script = src => new Promise((res, rej) => { const sc = document.createElement('script'); sc.src = src; sc.onload = res; sc.onerror = () => rej(new Error('Could not load the sign-in library')); document.head.append(sc) });
  async function fbLoad() {
    if (fbReady) return fbReady;
    fbReady = (async () => {
      const cfg = (await api('/config')).firebase;
      if (!cfg || !cfg.apiKey) throw new Error('Mobile codes are not available right now. Use your email or password.');
      if (!window.firebase) { await script('https://www.gstatic.com/firebasejs/' + FB_V + '/firebase-app-compat.js'); await script('https://www.gstatic.com/firebasejs/' + FB_V + '/firebase-auth-compat.js') }
      if (!firebase.apps.length) firebase.initializeApp(cfg);
      try { firebase.auth().useDeviceLanguage() } catch (e) { }
      return firebase.auth();
    })().catch(e => { fbReady = null; throw e });
    return fbReady;
  }
  const phone = {
    async send(number) {
      const auth = await fbLoad();
      let host = document.getElementById('tht-recaptcha');
      if (!host) { host = document.createElement('div'); host.id = 'tht-recaptcha'; host.style.cssText = 'position:fixed;left:-9999px;bottom:0'; document.body.append(host) }
      if (fbVerifier) { try { fbVerifier.clear() } catch (e) { } fbVerifier = null; host.innerHTML = '' }
      fbVerifier = new firebase.auth.RecaptchaVerifier(host, { size: 'invisible' });
      try { fbConfirm = await auth.signInWithPhoneNumber(number, fbVerifier) }
      catch (e) {
        const c = e && e.code || '';
        throw new Error(c === 'auth/too-many-requests' ? 'Too many codes asked for this number. Try again later.' : c === 'auth/invalid-phone-number' ? 'Check the mobile number.' : c === 'auth/quota-exceeded' ? 'SMS codes are busy right now; try email or your password.' : (e && e.message) || 'Could not send the SMS code');
      }
      return true;
    },
    async token(code) {
      if (!fbConfirm) throw new Error('Ask for the code again.');
      let res;
      try { res = await fbConfirm.confirm(String(code || '').replace(/\D/g, '')) }
      catch (e) { const c = e && e.code || ''; throw new Error(c === 'auth/invalid-verification-code' ? 'That code is not right.' : c === 'auth/code-expired' ? 'The code has expired. Ask for a new one.' : (e && e.message) || 'That code is not right.') }
      const t = await res.user.getIdToken();
      try { await firebase.auth().signOut() } catch (e) { }   // nothing stays signed in on Google's side; the server owns the session
      fbConfirm = null;
      return t;
    },
    pending: () => !!fbConfirm
  };
  window.THT = { api, passkey, phone, pw: { rules, score, generate } };
})();
