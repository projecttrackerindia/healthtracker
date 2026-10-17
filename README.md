# TheHealthTracker

thehealthtracker.com · family health companion with a personal 3D body.

Family health companion with a personal 3D body. This folder is a complete, deployable web app:

```
server.py            FastAPI server: static app (pre-compressed, cached), /healthz, /api/v1/*, /api/admin/*, /admin
api/                 database (SQLAlchemy), seed data, public API, AI analysis, payments, admin API
admin/index.html     the admin panel (single page)
web/                 the app (index.html + fingerprinted assets in web/a/)
requirements.txt     fastapi, uvicorn, sqlalchemy, psycopg, pypdf, anthropic
Procfile             start command (Railway also reads railway.json)
railway.json         health check + restart policy
tools/               build scripts that produced web/ (not needed to run or deploy)
```

## Deploy on Railway

Step-by-step with the exact variables: see **RAILWAY.md** (and `.env.example`). Brand and logo rules: **BRAND.md**; files in `web/brand/`.


1. Push this folder to a GitHub repository (the folder itself is the repository root).
2. In Railway: **New Project → Deploy from GitHub repo** and pick it. Nixpacks detects Python from `requirements.txt` and starts the app with the command in `railway.json`.
3. Open **Settings → Networking → Generate Domain**. The health check path is `/healthz`.
4. Add a **PostgreSQL** plugin to the project (Railway sets `DATABASE_URL`). Without it the server uses a SQLite file, which is
   wiped on every redeploy and not shared between replicas, so it is for trying things out only.
5. Variables (Settings → Variables):

| Variable | What it does |
| --- | --- |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | First admin login for `/admin`. Without a password, a random one is generated and printed once in the deploy logs. |
| `SECRET_KEY` | Signs admin session cookies. Any long random string; without it sessions end at each restart. |
| `ANTHROPIC_API_KEY` | Turns on AI reading of reports and prescriptions (PDF, photo or text) with Claude. Without it a rules-based reader handles PDFs and typed text; photos cannot be read. `DOKKO_AI_MODEL` overrides the model (default `claude-sonnet-5-5`). |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Live subscription payments through Razorpay Checkout. Without them billing runs in demo mode (plans activate, no money moves). |
| `DOKKO_REGION` | Default `IN`. |

Railway sets `PORT` and `RAILWAY_GIT_COMMIT_SHA` itself. The server creates the tables and seeds fictional partners, price lists,
plans, seasonal advisories and the first-aid video list on first start; edit everything in `/admin`.

Run locally:

```
pip install -r requirements.txt
uvicorn server:app --reload        # http://localhost:8000
```

## What is in the app

Six sections, each with its own tabs:

| Section | Tabs | Notes |
| --- | --- | --- |
| Home | Today, Body, Heart Lab | Today: doses, results worth discussing, next visit, findings pinned on the 3D body |
| Records & Labs | Vault, Lab results, Insights | Upload PDF/photos (kept in this browser's IndexedDB), results explained in plain language, suggested checks (always "discuss with your doctor") |
| Medicines | My medicines, Find & order, Orders | Dose tracking, ~45-item sample catalogue, prescription gating, allergy / pregnancy / age checks, demo checkout and tracker |
| Care | Appointments, Doctors, Messages, Pregnancy (opt-in), Bills | Visit booking with per-visit record sharing |
| Safety | SOS, First aid, Medical ID, Contacts | 112 / 108, hold-to-alert with location and SMS fallback, CPR metronome, lock-screen Medical ID |
| Family & Privacy | Family, Consent, Your data, Settings | Household switcher, consent switches with a history log, export JSON, delete everything |

Look and feel: glass cards with a soft dot grid, light and dark themes (follows the device, or the toggle), a Home vitals card with a dotted ECG that beats at the member's heart rate, and a floating SOS button. On phones (under 720 px) the sidebar becomes a six-icon bottom bar, the header compacts, the SOS button shrinks to a round badge and the Heart Lab shows at most three labels per side.

Rules the app follows: no diagnosis, never shows or infers fetal sex, prescription (Schedule H) items need an attached prescription, emergency words typed anywhere open SOS, pregnancy is opt-in, "discuss with your doctor" on every suggestion.

Family data stays on the device (`localStorage` key `dk6`, files in IndexedDB `dk6files`). The server sees only what a feature needs:
an anonymous household key, the basket for price quotes, orders and ratings, and (only after consent, only when the person taps
Analyse) a report or prescription, which is read and discarded.

### Website and accounts

* `/` is the public landing page (features, security, pricing, FAQ); `/signin`, `/signup` and `/reset` open the account sheet;
  the app lives at `/app` (guests can still try it without an account).
* **Sign in** with a **passkey** (WebAuthn/FIDO2; offered in the username autofill too), a **password** (optional two-step
  code) or a **one-time code** by email or SMS. Accounts are created with a verified email or mobile and a strong password,
  then a passkey is offered.
* **Password rules** (shown live, enforced by the server): 12–128 characters, upper and lower case, a number and a symbol,
  no 3 identical characters in a row, no runs like 1234/abcd/qwer, nothing from the name/email/phone, not a common password,
  and not found in known breaches (Have I Been Pwned, k-anonymity). Hashing: scrypt.
* Protections: CSRF header on every change, HttpOnly SameSite cookies, 5 wrong passwords → 15-minute lock, code limits
  (10-minute expiry, 5 tries, 45 s between sends, 6 per hour), sign-out of all devices, admin unlock/disable.
* In the app: Settings → **Account & security** (passkeys, password, two-step, signed-in devices). A signed-in account
  carries its plan, orders and AI quota to every device.

### Server features (Phase 2)

* **AI analysis** of reports and prescriptions: plain-language findings with flags, medicines with dose and frequency, tests to book,
  follow-ups and questions for the doctor. "Save values to Lab results", "Order these medicines", "Add to my medicines" and
  "Compare nearby labs" act on the result. Monthly quota by plan (Free 3, Family 30, Plus unlimited).
* **Live pharmacies** in the basket: nearby partners compared on price, discount, delivery fee, ETA, rating and "ordered before",
  with tags (Cheapest, Nearest, Fastest, Best rated, Biggest discount). Orders are tracked (placed → pharmacist check → packing →
  out → delivered) and rated with stars and tags after delivery; ratings feed the partner's score.
* **Lab finder**: price estimate per test at nearby labs, fasting needs, report time, home-collection slots and booking.
* **First-aid videos**: 25 verified videos from St John Ambulance, the American Heart Association, St Andrew's First Aid and
  St John WA, embedded from YouTube (nothing is re-hosted); admins add more.
* **Seasonal advisories** on Home by month (dengue, heat stroke, flu, air pollution …) with symptoms, prevention and when to see a doctor.
* **Nearest hospitals** on the SOS page with call and directions links.
* **Plans & billing**: Free (₹0), Family (₹39/month or ₹390/year), Plus (₹99/month or ₹990/year), invoices, Razorpay when configured.
* **Admin panel** at `/admin`: dashboard, partner onboarding (pharmacies, labs, hospitals) with verification, price lists and CSV import,
  orders and status updates, households and plans, billing, seasonal advisories, videos, team roles (owner / ops / content) and an audit log.

### Known limits of this release

* Sample data only (a fictional household), sample catalogue and demo prices; checkout and order tracking are simulated.
* Reminders work while the app is open. Push notifications when closed need a server and are not included.
* SOS uses the phone's own call and SMS apps (`tel:` / `sms:`). It cannot send messages by itself.
* Hindi and Telugu cover the navigation, SOS and emergency screens; clinical text stays in English until a clinician reviews translations. Noto Sans Devanagari and Telugu (OFL) are bundled and load only when those languages are used.
* First-aid videos are not included (need licensed content). Text steps are general guidance, not a substitute for training.
* Female muscles are the male atlas re-posed onto the female skin (arms follow the skin's relaxed pose, hands are fitted to the skin hand). The forearm muscles are slimmed to sit inside the skin; at the elbow a few muscle edges can still show through a partly transparent skin.
* Medical content (ranges, suggested checks, first aid, seasonal advisories, the AI prompt) should be reviewed by a qualified clinician before public launch.
* Partners, prices and ratings are fictional seed data until real pharmacies and labs are onboarded in `/admin`. Orders are not sent to
  any partner system yet: a partner marks progress in the admin panel, otherwise a demo clock advances the status.
* There are no user accounts: each install is an anonymous household key, so data does not follow a person to a new phone (export/import in
  Family & Privacy → My data does). Phone-OTP sign-in is the next step.
* The rules-based reader (no API key) reads typed text and PDFs with selectable text only.

## Why it is light

| What | Size over the wire | When it loads |
| --- | --- | --- |
| App shell (HTML + app code) | see `web/` listing in the build log | first visit, then cached |
| three.js | ~150 KB (Brotli) | first visit, then cached forever |
| Body model, **Light** tier | a few MB | when Home or Anatomy Lab opens |
| Body model, **HD atlas** | ~35 MB, once | only when you press **HD atlas** in Anatomy Lab |
| Female organs, heart atlas, heart physiology | 3 MB, 3 MB, 2 MB | only when that page opens |

Pages that do not need anatomy (everything except Home and the anatomy pages) never download a model.
Models live in `web/a/` with a content hash in the file name, are served `Cache-Control: immutable`, and are kept by the service worker, so repeat visits and offline use cost nothing.
Text assets are served pre-compressed (Brotli, falling back to gzip).

## Security headers

`server.py` sends a strict Content-Security-Policy (same-origin only, no third-party requests: fonts are self-hosted), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` (location allowed for SOS) and HSTS.

## Attribution (keep visible in the app)

Anatomy: Z-Anatomy (CC BY-SA 4.0, built on BodyParts3D © DBCLS) and the HuBMAP Human Reference Atlas v1.5 (CC BY 4.0). Because Z-Anatomy is share-alike, the derived model files in `web/a/` must stay under CC BY-SA 4.0.
