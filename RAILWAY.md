# Deploy Urban Health on Railway

1. **Repository.** Unzip, then push the `urbanhealth` folder to a new GitHub repository (the folder is the repo root).
   ```
   cd urbanhealth && git init && git add . && git commit -m "Urban Health" && git branch -M main
   git remote add origin https://github.com/<you>/urbanhealth.git && git push -u origin main
   ```
2. **Project.** railway.app → New Project → Deploy from GitHub repo → pick the repository. Nixpacks detects Python and uses
   the start command and `/healthz` health check from `railway.json`.
3. **Database.** In the project: New → Database → PostgreSQL. Railway exposes `DATABASE_URL` from it.
4. **Variables.** Open the web service → Variables → Raw Editor, paste the block below, fill the values, Deploy.

```
SECRET_KEY=<64 hex characters>
ADMIN_EMAIL=admin@urbanhealth.in
ADMIN_PASSWORD=<12+ characters>
DATABASE_URL=${{Postgres.DATABASE_URL}}
RP_ID=urbanhealth.in
APP_ORIGIN=https://urbanhealth.in,https://www.urbanhealth.in
RESEND_API_KEY=
MAIL_FROM=Urban Health <no-reply@urbanhealth.in>
MSG91_AUTH_KEY=
MSG91_TEMPLATE_ID=
ANTHROPIC_API_KEY=
DOKKO_AI_MODEL=claude-sonnet-5-5
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
DOKKO_REGION=IN
PWNED_CHECK=1
OTP_DEMO=0
```

> **First deploy on the `*.up.railway.app` address, before your domain is connected:** set `RP_ID` to that host
> (e.g. `urbanhealth-production.up.railway.app`) and `APP_ORIGIN` to `https://` + that host. Passkeys are bound to
> `RP_ID`: passkeys created on the Railway address will not work on urbanhealth.in, so switch both variables to the
> real domain before inviting users. If no email/SMS provider is set yet, you can set `OTP_DEMO=1` **for your own testing
> only** — codes then appear on screen and anyone could create accounts; set it back to `0` before launch.

| Variable | Required | Notes |
| --- | --- | --- |
| `SECRET_KEY` | yes | Signs admin sessions. Generate: `python -c "import secrets;print(secrets.token_hex(32))"`. Changing it signs everyone out. |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | yes | First admin, created on first start. If the password is empty a random one is generated and printed once in the deploy logs. Setting a new `ADMIN_PASSWORD` later resets that admin's password on the next restart. |
| `DATABASE_URL` | yes for production | `${{Postgres.DATABASE_URL}}` references the plugin (use the plugin's real name if you renamed it). Without it the app uses SQLite, which is wiped on every redeploy. |
| `ANTHROPIC_API_KEY` | yes for photos | Smart reading of reports, prescriptions, photos and cards. Without it a basic reader handles PDFs with text and typed text. After setting it, open `/admin` → Dashboard → **Test connection** to confirm the server can reach the model; the exact error is shown there, never to users. |
| `DOKKO_AI_MODEL` | no | Default `claude-sonnet-5-5`. If the key cannot use it, the server falls back to the next available model automatically and logs `[ai] using model …`. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | before selling plans | Live subscription payments (UPI, cards, net banking). **In production nothing but a verified Razorpay payment can activate a paid plan**: without these keys every family stays on Free and the plan page says "Opening soon". Demo activation only happens when `APP_ENV` is not `production`. |
| `RP_ID`, `APP_ORIGIN` | yes for passkeys | Domain the passkeys belong to, and the exact https address of the site. If empty they are taken from the request. |
| `RESEND_API_KEY` + `MAIL_FROM` | one email option | Sends sign-up, sign-in and reset codes by email. Verify the sending domain in Resend (DNS records). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` | other email option | Any SMTP service (Zoho, Gmail app password, Amazon SES). Port 465 uses SSL, others STARTTLS. |
| `MSG91_AUTH_KEY`, `MSG91_TEMPLATE_ID` | yes, for verified mobiles | MSG91 OTP API. Requires a DLT-registered sender and OTP template with `##OTP##`. Sign-up verifies the email first and then the mobile in the same flow; without an SMS provider the mobile stays "verification pending" and the account badge is not shown. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` | SMS option | Twilio SMS (international; India needs DLT too). |
| `PWNED_CHECK` | no | `1` (default) rejects passwords found in known breaches using Have I Been Pwned's k-anonymity API. |
| `OTP_DEMO` | no | `1` shows codes on screen instead of sending them. Testing only. |
| `DOKKO_REGION` | no | `IN`. |
| `LEGAL_ENTITY`, `LEGAL_ADDRESS` | yes before launch | Shown on /privacy and /terms (registered name and address of the business). Defaults: `Urban Health`, `Hyderabad, Telangana, India`. |
| `GRIEVANCE_NAME`, `GRIEVANCE_EMAIL` | yes before launch | Grievance Officer shown in the privacy policy (DPDP Act). `GRIEVANCE_EMAIL` falls back to `SUPPORT_EMAIL`, then `ADMIN_EMAIL`. |
| `SUPPORT_EMAIL` | recommended | Contact address on /terms. |
| `POLICY_UPDATED` | no | Date shown on the policy pages, e.g. `18 October 2026`. |
| `DATA_KEY` | yes before launch | 64 hex characters (`python -c "import secrets;print(secrets.token_hex(32))"`). Encrypts each family's health store at rest. Without it a key is derived from `SECRET_KEY`. **Never change it after launch**: stored data becomes unreadable. |
| `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | for phone notifications | Reminders and missed-dose alerts when the app is closed. Generate once: `python -c "from api.push import make_keys; print(make_keys())"` and paste `VAPID_PRIVATE_KEY`; `VAPID_SUBJECT` is `mailto:support@yourdomain`. Changing the key signs every phone out of notifications. |
| `S3_BUCKET`, `S3_ENDPOINT`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | recommended | Where families' documents (encrypted) are kept: Cloudflare R2, AWS S3 (ap-south-1, Mumbai) or Backblaze B2. Without a bucket, documents are stored encrypted in Postgres (fine for a small launch; `FILES_CAP_MB` per family, default 2048). |
| `APP_ENV` | staging only | `staging` shows a ribbon in the app and sends `noindex` headers. |
| `CANONICAL_HOST` | recommended | e.g. `urbanhealth.in`. Sends www.… visitors to this address so the sign-in cookie is always the same. Set it only after both addresses open the site. |
| `PORT`, `RAILWAY_GIT_COMMIT_SHA` | — | Set by Railway. Do not add them. |

### Round 16 (part 1) — merged late (2026-10-20)

* Rebased onto the provider-agnostic AI code: per-family and service-wide **daily token budgets** (`ai_budget`, 429/503 with the basic reader as fallback), token accounting on every AiJob, admin **AI spend** and device-speed beacon, GST/referral columns on sellers and orders. Conflicts resolved in favour of `AI.available()` / `provider_order()`.

## Round 28 — Hindi and Telugu (2026-10-20)

* 347 hand-written core phrases (`tools/i18n/core.py`: shell, Home, sign-in, SOS, Medical ID, medicines, sharing, backups, buttons) ship inside the page; the long tail comes from `/api/v1/i18n` (repo `site/i18n/phrases.json`, or the bucket's `i18n/phrases.json` when present — `python tools/i18n/translate.py --upload` with `GEMINI_API_KEY` + `S3_*` fills it with Gemini and goes live without a release). Cached on the device for offline.
* Language card on Settings (English / हिन्दी / తెలుగు); switching loads the table first. Medical guidance stays English until reviewed.
* Service worker `dk-r28`.

## Round 27 — medicine interactions (2026-10-20)

* `live27`: ~40 drug classes (matched inside names and generics, brands included: Telma, Ecosprin, Thyronorm, Dolo…) and ~50 flagged pairs (blood thinners + NSAIDs, ARB + potassium, statin + macrolide, nitrate + sildenafil, levothyroxine + calcium/iron, SSRI + tramadol, benzo + opioid, two paracetamols…) with stop/warn levels and plain-language advice. Checked on the device from the names alone.
* Where it shows: a **Checks on this list** card on Medicines; a toast when a medicine is added (catalogue or hand-typed); the finder's existing warnings (`SX.medWarn`) now include the pairs. `SX.medInteract(m, name)`, `SX.medPairs(m)`.
* Service worker `dk-r27`.

## Round 26 — backups the family can see (2026-10-20)

* **Backed up** card (Home + My data): last record sync, the vault's document count, when the last copy was emailed and where the next one goes. "Email me a copy now" (2/day) and "Download everything".
* On the 1st of every month the morning job emails the record ZIP (documents left out, ≤12 MB) to every verified address of the family (`api/backup.py`, `households.backup_at/backup_to`, dedupe per month). `export.build_zip(db, h, include_files)` is shared with `/export`. `messaging.send_mail_attachment` (SMTP + Resend). Duplicate `send_mail` removed.
* Service worker `dk-r26`.

## Round 25 — doctor share link, day-counted insights (2026-10-20)

* **Share with a doctor** (Home): a link to the one-page summary that expires by itself (48 h / 7 days), opens on any phone with no app, prints, counts views, can be ended from Home. `api/summary.py`: `POST/GET/DELETE /api/v1/summary/share`, public `/ds/<token>` (HTML sealed at rest, scripts/handlers stripped, noindex, strict CSP). The old "For the doctor" card is replaced; the print path stays.
* Insights: a new morning rule counts **days**, not readings — "blood pressure 140/90 or above on 3 of the 4 days with a reading this week", fasting sugar > 130 (marked fasting, or unmarked before 10:00), SpO₂ < 94, resting HR > 100 — one notice per week per pattern. The 3-a-day nudge cap is now per day, not per run.
* Service worker `dk-r25`.

## Round 24 — medicine refills (2026-10-20)

* Stock counts (`left`, already decremented per ticked dose) now drive a countdown: `days left = left ÷ doses per day` (weekday-only doses count 1/7). Medicines page: a **Running low** card (≤7 days: left, days, run-out date, Reorder → the finder); Home: a **Refill soon** card at ≤3 days.
* Reminders job: once a day at 09:00 IST a "Refill soon" push for anything at ≤3 days (deduped per member/day; to the person's own phone when they have an account), link `/app#refill=<id>` opens the finder on that medicine. The phone app also schedules a 09:00 local notification for the same list.
* Service worker `dk-r24`.

## Round 23 — lab trends (2026-10-20)

* Lab results page: a **Trends** card — one tile per test with ≥2 results (latest value, change vs previous, sparkline with the healthy band), tapping opens the full chart (SVG, no library): values over the years with the range band, colour-coded points, year chips, the list of every result, "Discuss with your doctor". `SX.labTrendChart(m,key)` for other pages.
* Demo fixes found on the way: the sample family now keeps every section's *structure* (notes.seen, rem.off…) so the bell no longer crashes; "You" has a complete health card so the mandatory first-step form does not open in the demo; the demo banner no longer shares its class with `<body>` (it had painted the whole page white in light mode).
* Service worker `dk-r23`.

## Round 22 — the phone design system, light first (2026-10-20)

* `tools/live/live22.{js,css}` (p22): light theme by default, dark only when chosen (`tht.theme`, set before first paint); Plus Jakarta Sans display type; one 24-px stroke icon set (`SX.ico`) replacing emoji in the tab bar, quick actions and Devices; app bar (avatar ring · centred title · glass bell · pulsing SOS), scrolling pill sub-tabs that never clip; floating dark tab bar with labels; Home top block (greeting, family strip to switch members, 2×2 stat tiles — steps/sleep/heart rate/BP — and a "this week" strip), Home cards ordered and duplicates hidden on phones; "+" quick-add sheet; assistant orb hero in every state; Medical ID, SOS, sign-in and More-sheet polish.
* Service worker `dk-r22`.

## Round 21 — SOS that acts (2026-10-20)

* One press: 3-second countdown (Cancel / Send now) → the phone calls the chosen number (112 / 108 / a contact; the Android app dials by itself through the `Sos` plugin, CALL_PHONE) → `POST /api/v1/sos/start` creates an alert with a public **live page** `/sos/<token>` (map that follows the person, Medical ID, call/directions buttons) → the server emails contacts with an address, pushes + WhatsApps the family's own phones (via inbox.notify), free-text SMS when Twilio exists → the sheet offers one-tap WhatsApp/SMS for the rest, nearest hospitals with directions, "I'm safe" ends the alert. Location keeps updating every 30 s while the alert is open; the first fix re-sends to everyone told "not available yet".
* Safety page set-up card: who to call first, allow location (and the call permission) ahead of time, email on contacts. Emergency contacts gained an email field.
* `messaging.send_mail` / `send_text_sms`; `SosAlert` table. Service worker `dk-r21`.

## Round 20 — mobile codes through Firebase Phone Authentication (2026-10-20)

* `MAIL`/SMS channels: `messaging.sms_mode()` = msg91 | twilio | **firebase** (`FIREBASE_WEB_API_KEY` + `FIREBASE_PROJECT_ID` + `FIREBASE_APP_ID`). With Firebase, a start answer carries `{firebase:true, phone}`; the browser runs `THT.phone.send/token` (Firebase JS, invisible reCAPTCHA) and verifies with `{flow, firebaseToken}`; the server checks the token with `accounts:lookup` and matches the number (`auth.verify_code`). Unknown numbers get the same answer as known ones.
* `/auth/config` → `firebase` web config. CSP allows gstatic / identitytoolkit / recaptcha.
* Fixed: the in-app two-step verify sent `{step}` instead of `{flow}`.
* Fitbit card announces the 30 Oct 2026 shutdown; `docs/wearables.md` covers the Google Health API.
* Service worker `dk-r20`.

## Round 19 — watches and devices (2026-10-20)

* Bluetooth inside the phone apps: `@capacitor-community/bluetooth-le` wrapped as `navigator.bluetooth` (layer 19), so "Read from a device" (BP monitors, oximeters, scales, thermometers, HR straps) and the Polar H10 live ECG work in the Android/iOS WebView, not only in Chrome. Android manifest gains `BLUETOOTH_SCAN` (neverForLocation) and `BLUETOOTH_CONNECT`.
* Withings and Oura clouds beside Fitbit (`api/wearables.py`, `/api/v1/wear/*`); Withings brings ScanWatch ECG strips with their AFib classification. Each switches on when its developer keys exist (`deploy/gcp/secrets.txt`). See `docs/wearables.md` for the full map of which watch takes which road.
* Service worker `dk-r19`.

## After editing any page

The server sends the compressed copy of a page (`index.html.br` / `.gz`) when the browser accepts it. After changing
`web/index.html` or anything in `site/`, run `python tools/compress.py` and commit the refreshed copies.
`python tools/compress.py --check` fails if any copy is stale. The server also refuses to send a stale copy (it falls back
to the uncompressed file and prints a warning in the deploy log), so a forgotten step costs speed, not correctness.

5. **Domain.** Service → Settings → Networking → Custom Domain → `urbanhealth.in` (and `www`). Add the CNAME record Railway
   shows at your domain registrar. HTTPS is issued automatically.
6. **Check.** `https://urbanhealth.in/healthz` returns `{"ok":true}`. The landing page is `/`, sign-in `/signin`, sign-up `/signup`, the app `/app`, the admin panel `/admin`.
   Create your own account, add a passkey (Settings → Account & security), sign out and sign back in with it.
7. **After launch.** In `/admin`: change seed partners to real ones, verify them, review plans (Free / ₹39 / ₹99), seasonal advisories and videos.

## A staging copy (check every change before families see it)

1. In the same Railway project: **New → GitHub repo → this repository**, branch `staging`. Add a second Postgres plugin for it.
2. Variables: copy from production, then set `APP_ENV=staging`, `OTP_DEMO=1` (codes on screen; never on production), a different `SECRET_KEY` and `DATA_KEY`, and **no** Razorpay live keys. Leave `S3_BUCKET` empty or use a separate bucket.
3. Generate a domain for it (for example `staging-urbanhealth.up.railway.app`) and set `RP_ID` / `APP_ORIGIN` to that address.
4. Workflow: merge pull requests into `staging` first, click through, then into `main`. The orange STAGING ribbon tells you which one you are looking at.

## Identity and the health assistant (round 5)

* **One identity.** Sign-up needs a full name as on Aadhaar, an email and a mobile; both contacts are verified in the sign-up flow. The account name, the health card, Medical ID, doctor summary and shares all read the same member record. Identity details (name, date of birth, sex, blood group) change at most once a week, on the server (`/auth/profile`, HTTP 423) and in the app.
* **Health assistant.** `/api/v1/ai/ask` answers questions about a person's own records from a structured summary the app builds (readings, results with dates, medicines, trackers) — never documents. `/api/v1/ai/insight` prepares a daily insight per person, cached for the day. Monthly caps per plan: questions 20 / 300 / unlimited, insights 10 / 200 / unlimited. Users consent once (recorded in the consent log).
* **Device readings.** The app reads Bluetooth devices that use the standard health profiles (blood pressure, pulse oximeter, weight scale, thermometer, heart rate) in Chrome/Edge on Android, Windows and Mac. Apple Health and Health Connect need the phone app (next milestone).

## Where every byte lives (round 6)

* **Family record** (profiles, readings, results, medicines, cards, care plans, chat with the assistant): one AES-GCM-encrypted JSON per family in Postgres (`household_state`). **Every previous version is kept for 30 days** in `household_state_history`; an admin can list and restore them (`GET /api/v1/admin/households/{id}/history`, `POST .../restore/{history_id}`). A bad sync from one phone can always be undone.
* **Documents** (reports, prescriptions, card scans — including anything attached in the assistant chat): encrypted with `DATA_KEY` and stored in the S3 bucket (`S3_*`), with the index in Postgres (`stored_files`). Uploads queue on the device while offline and backfill on sign-in.
* **Accounts, orders, bookings, share links, push subscriptions, AI usage, client errors**: ordinary Postgres tables.
* Nothing health-related is kept only in the browser once the person is signed in; the browser copy is a cache.

## Nearby places and location

`/api/v1/geo/where` (reverse geocoding) and `/api/v1/places` (hospitals, clinics, labs, pharmacies, blood banks) use OpenStreetMap's Nominatim and Overpass services from the server, cached per ~1 km cell, at most one call a second, with a real User-Agent, per their usage policy. Partner stores from the admin panel are merged in and marked `partner`. Map tiles come from tile.openstreetmap.org (allowed in the CSP). For heavier traffic later, set `NOMINATIM_URL` / `OVERPASS_URL` to a paid or self-hosted mirror; nothing else changes.

## Partner portal (round 7)

`/partner` is where labs, pharmacies and hospitals work. An admin creates the store in `/admin → Partners`, verifies it, and creates a portal sign-in from the store's edit drawer (one-time password, shown once; the partner sets their own on first sign-in).

* **Labs**: bookings → confirm → sample collected → in the lab → upload the report (PDF) → the family gets a push and the report appears in their Lab records with **Analyse**. The report is stored encrypted in the family's document store (S3), never on the portal.
* **Pharmacies**: orders → check (the shared prescription opens from the order; nothing else in the family's vault is reachable) → packed → out → delivered. Prescription-only items without a prescription are flagged red.
* **Hospitals**: visit requests → confirm a slot / offer another time / decline; confirmed visits land in the family's Appointments and Today.
* **Everyone**: messages with families who have an order, booking or visit with them (attachments from the family's vault open from the thread); price list / stock; store profile (hours, phone, collection or delivery terms). Name, address and licence are changed only by admin.
* **Families** see all of it through `/api/v1/inbox`, polled every minute and on focus, merged into the notification centre, Lab results, Orders and Appointments. In production nothing advances an order except the partner or an admin.

## Production hygiene (round 9)

* `OTP_DEMO` is ignored when `APP_ENV=production`: one-time codes are never shown on screen in production, whatever the variable says.
* `DATA_KEY` can be set after launch: records encrypted before it existed stay readable (the SECRET_KEY-derived key is tried after the current one) and are re-encrypted with the new key the next time they are saved. `DATA_KEY_PREV` allows a planned rotation the same way.
* `/admin → Dashboard → Test storage` writes, reads and deletes one object with the live credentials and shows the exact error if the bucket is not reachable. The app backs off failed uploads (30 s, 1 min, 2 min … up to an hour) instead of retrying every few seconds.
* On Railway the service references the bucket's credentials (`${{bucket.ENDPOINT}}`, `${{bucket.ACCESS_KEY_ID}}`, …) rather than copying them; a credential reset needs no edit.

## Round 10: doctors, the acting assistant, the Android app, payments, identity

**Video consults.** A hospital's admin creates a *doctor* sign-in (name + medical council registration number) under the store; an admin ticks **Verified** after checking the NMC / state register. Verified doctors see **Video consults** in the partner portal, press *Start* on a confirmed video visit, and the family gets a push + in-app prompt to join. Media is peer to peer (WebRTC); the server only relays the signalling over `/ws/call/{appointment}`. Live captions (browser speech recognition) are shared both ways; at the end the family chooses whether to keep the transcript, and the health assistant writes a plain-words visit summary. The doctor's e-prescription is signed with the registration number, written as a PDF into the family's encrypted documents (`erx_<id>`), and shows in Medicines ("Add to my medicines", "Order these").
Variables: none required (Google STUN is used). For calls across strict mobile networks set a TURN relay: `TURN_URL=turn:host:3478,turns:host:5349`, `TURN_USER`, `TURN_PASS` (Metered, Twilio or a coturn box).

**Proactive assistant.** Every morning 08:00–09:00 IST the server reads each family's record once and writes at most three nudges (repeat tests for out-of-range results, vaccines due, policy renewals, pregnancy milestones, care-plan review, drifting BP/sugar, a child turning 18) and, on Mondays, the weekly report (trends vs the previous four weeks, BP control, adherence, pregnancy weight gain vs IOM ranges, anomalies). Assistant answers can carry up to two *commands* (book a lab, request a visit, set a reminder, add a reading, open a page) that the app shows as buttons. Medicine safety check: `POST /ai/medcheck` (interactions, duplicates, allergy clashes, timing) under the insight quota.

**Android app.** `mobile/` is a Capacitor project that loads the live site and adds Health Connect (steps, sleep, heart rate, weight, BP, sugar, SpO₂ → the person's readings), native push (FCM) and the back button. GitHub Actions `android.yml` builds a debug APK on every push to `mobile/**`; a signed release AAB when `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` secrets exist. Push needs a Firebase project: put `google-services.json` in the `GOOGLE_SERVICES_JSON` secret and the service-account JSON in the Railway variable `FCM_SERVICE_ACCOUNT_JSON`.

**Payments by UPI (until Razorpay).** Plan upgrades and orders show a QR / one-tap UPI link for one of our accounts (`api/data/upi.json`, override with `UPI_ACCOUNTS` JSON) with the exact amount and a reference (THT00001…). The person enters the UTR; **Admin → UPI payments** matches it against the bank statement and confirms — only then does the plan switch (invoice issued) or the order show as paid. `UPI_PAY=0` switches the route off. Razorpay keys, when added, take over automatically.

**Identity from Aadhaar (DigiLocker).** There is no public Aadhaar login for apps; UIDAI e-KYC is only for licensed AUA/KUAs. The sanctioned route is DigiLocker: register at <https://partners.digilocker.gov.in> (Requester, OAuth 2.0; redirect URI `https://urbanhealth.in/api/v1/digilocker/callback`; documents: Aadhaar e-KYC) and set `DIGILOCKER_CLIENT_ID`, `DIGILOCKER_CLIENT_SECRET`. Then sign-up offers *Verify with Aadhaar via DigiLocker* instead of the mobile code (email code stays), the account name and date of birth come from Aadhaar and lock, the masked Aadhaar card (last 4, demographics, photo) is kept encrypted in Cards, and the verified badge accepts Aadhaar in place of the mobile code. Mobile numbers still need our own OTP (MSG91) — e-KYC does not return the mobile.

**ABHA / ABDM.** `api/abdm.py` implements the v3 flows (session token, public certificate, Aadhaar-OTP enrolment, login by ABHA) behind `ABDM_CLIENT_ID`, `ABDM_CLIENT_SECRET`, `ABDM_ENV=sandbox|production`. Register at <https://sandbox.abdm.gov.in>. Until then the ABHA card says linking is coming and accepts a photo.

**Family roles.** The first sign-in of a family is its admin; invitations create members or (admin only) caregivers. Caregivers can add readings, doses, visits and notes but cannot change profiles, cards, results, medicines, consents or delete the family — enforced on the server in `PUT /sync`. Family → Sign-ins & roles manages it; `GET /export` (3 a day) gives the whole record + documents as a ZIP (DPDP right to portability).

**Partner growth.** `/partner → Apply` files an application; **Admin → Applications** checks the licence, sets the location, approves (creates the store + owner sign-in) or declines. **Admin → Settlements** shows per-partner monthly totals, the platform fee (`PARTNER_FEE_PCT`, default 8), pay-outs and collections, with CSV.

**Lock-screen Medical ID.** Safety → Medical ID → *Lock-screen Medical ID* publishes `/m/<token>` (no sign-in; blood group, allergies, conditions, medicines, contacts, donor wish) with a QR to print or set as wallpaper; rotate or switch off any time; views are counted.

**Addresses.** Family → Addresses keeps home / work / other (with "use my current location"); checkout and home-collection bookings pick one, and the partner sees the full address, phone and a directions link.

**Devices tab (round 11).** Home → Devices shows where readings come from: the phone app (Health Connect on Android, Apple Health on iPhone — including Apple Watch ECG recordings, imported as strips), **Fitbit** linked from the web (`FITBIT_CLIENT_ID/SECRET`, callback `/api/v1/fitbit/callback`; register at dev.fitbit.com), Bluetooth devices in the browser, and **live ECG from a Polar H10/H9** (PMD service over Web Bluetooth; 30-second strips are saved as records with rate and RR variation, readable by the assistant). No watch maker exposes a live ECG to third-party apps; Google Fit's API is gone, which is why Fitbit is the one cloud connector.

**App downloads.** `GET /api/v1/app/android` and `/download/android` serve the APK that GitHub Actions publishes to the bucket (`releases/urbanhealth.apk` + `android.json`) when the `S3_*` repository secrets exist; an admin can also upload one at `PUT /api/admin/app/android`. `PLAY_STORE_URL`, `APPSTORE_URL`, `TESTFLIGHT_URL` switch the site's buttons when the store listings exist. `mobile/ios` is the iOS project (HealthKit plugin, `ios.yml` builds on a macOS runner; signing needs an Apple Developer account and the `IOS_*` secrets).

**Loops that close on their own.** Paid plans end when `plan_until` passes (notice + Free plan) with one renewal nudge 5 days before; a video call nobody ended closes after 3 hours; partners get an email for every new order and visit request (`owner_email` + their sign-ins); applicants and new doctor sign-ins receive their one-time password by email; `ADMIN_ALERT_EMAIL` receives UPI claims and new applications; the admin dashboard shows a **Needs attention** row (payments to confirm, applications, doctors to verify, stores awaiting verification, visits unanswered > 24 h, orders not picked up > 4 h). All email goes through the existing transport (`RESEND_API_KEY` or `SMTP_*`); without one, nothing is sent and the admin pages carry the same information.

**Round 12.** *Shop*: `api/shop.py` seeds a system store (`s_tht_shop`) and the **Hospital Bag · Complete** package (placeholder price ₹2,999 / MRP ₹3,999, stock 50 — edit in Admin → Shop, upload a photo); families buy it from the birth plan with a saved address and UPI QR or cash on delivery; orders are kind `shop` and are fulfilled from Admin → Orders. *Blood network*: donors opt in from Medical ID (`PUT /donor`, consent + rough location); only hospitals, blood banks (new store kind `bloodbank`) and verified doctors raise requests from the partner portal; compatible, eligible donors within the radius get a push; offer → accept → live position every 20 s → arrived → donated (updates the donor's eligibility). Organs are never requested (THOTA 1994) — only the NOTTO pledge. *Medical ID* is an ID card first (contacts tap-to-call, blood group, allergies, pledge badges) with details folded below.

**Round 13.** *Phone shell*: at ≤720px the app has a bottom tab bar (Home · Records · Medicines · Care · More), a one-row app bar, sub-tabs that scroll, sheet-style modals, denser cards and the 3D body only on the Body tab. *Google Maps*: set `GOOGLE_MAPS_KEY` (browser key restricted to urbanhealth.in; Maps JavaScript + Places + Directions enabled) and every map switches to Google with road routes and ETAs on blood journeys and Places autocomplete on addresses; without it OpenStreetMap stays. *APK*: every Android build also attaches the APK to the `android-latest` GitHub release; Admin → System shows the publish state and lets you upload an APK by hand; `ANDROID_RELEASE_PUBLIC=1` uses the GitHub asset as the site's link when the repo is public.

**Round 14.** *Deep links*: the app's address is `/app/<person>/<profile>/<page>` with opaque hashed ids (never names or raw ids); reload, back/forward and sharing a link land on the same page and profile. *Idle sign-out*: sessions end after 30 minutes without a request (`SESSION_IDLE_MINUTES`); the app warns a minute before and signs out, landing on `/signin?idle=1`. *Care that fits the person*: cycle and pregnancy only for women of the right age, growth & vaccines only for under-18s, and Care shows "nothing to manage" until a report, a doctor's e-prescription note (offered as a suggestion) or the person sets up a plan. *Phone*: greeting + collapsing title, swipe between sub-tabs, pull to refresh, tab bar hides while scrolling down, haptics.

**Round 15.** *App-like start*: on phones and in the Android/iOS shells the full-page logo splash shows for ~1.6 s and then the full-screen Sign in / Create account (password, mobile one-time code, or create an account verified by code or Aadhaar through DigiLocker). *Health score* on Today, *consented visit summary* to the doctor's panel on video calls, *WhatsApp notices* (`WA_TOKEN`, `WA_PHONE_ID`, optional `WA_TEMPLATE_NOTICE`/`WA_TEMPLATE_LANG`; off until set), partner price-list CSV import, stale-while-revalidate caching in the service worker.

**Signed-out lock (round 16a).** Nothing of a family's record is painted while nobody is signed in — on the website, in the installed web app and in the native shells. An expired or idle session shows the full-screen sign-in with the record hidden; a device that has ever seen an account stays locked offline too. The only way to see sample data is to ask for the demo (the "See a demo with a sample family" link on the sign-in screen, or `/app?demo=1` from the website): a fictional family in memory only, never saved to the device, and the server refuses every write from a `demo-…` key (403) except `/hello` and `/beacon`; housekeeping deletes demo households after an hour.

**Passkeys and the domain.** Passkeys are bound to the domain the app is opened on. `RP_ID` names the canonical domain; when the app is opened on any other host that serves it (the `*.up.railway.app` address before the custom domain is attached, a staging host), that host is used as the relying party automatically — otherwise every passkey call fails with a browser SecurityError. A passkey made on one domain does not work on another, so attach the custom domain (Railway → service → Settings → Networking → Custom domain) before asking families to create passkeys, and keep `RP_ID=urbanhealth.in`. The in-app sign-in offers "Sign in with a passkey" and the automatic (autofill) prompt; after a sign-in on a device with a platform authenticator the app offers to create one (once per 30 days if declined).

**Round 17 — phone shell v2.** One app bar (person avatar · page title · bell · account); the greeting lives in Today. The **Health Card banner** (blood group · name · allergies/conditions · SOS) is pinned under the bar on every screen and can only be switched off in Safety → Medical ID; while it is on, the floating SOS bubble is hidden. Sub-tabs live in the bar as one strip (never repeated below the 3D stage). The assistant is full-height with the input docked above the keyboard and the tab bar stepping aside while typing. Body and Heart Lab show the viewer first with tools in a bottom row; heart labels are on demand ("Labels"). Bottom bar is a floating, icon-only pill. Pull-to-refresh is gone (it fired on ordinary iOS scrolls). In the Android app the Health Card is also an **ongoing notification** (`@capacitor/local-notifications`, id 7001) with an SOS action, removed when the banner is switched off; iOS gets the equivalent (Live Activity) with the App Store build.

**AI providers (round 18).** `GEMINI_API_KEY` (Gemini, `GEMINI_MODEL` default gemini-3.8-flash (gemini-2.5-flash was retired for new projects in Oct 2026)) and/or `ANTHROPIC_API_KEY`; `AI_PROVIDER=auto|gemini|anthropic` picks the first choice, the other is the automatic fallback. Same JSON contracts, same token accounting, no vendor named in the UI. **Email via Google Workspace**: `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=<mailbox>`, `SMTP_PASS=<App Password>`, `MAIL_FROM` the same mailbox (≈2,000 mails/day cap per mailbox); `MAIL_TRANSPORT=smtp` makes SMTP win when a Resend key is also present (`auto` prefers Resend).

## Operations checklist

* `/admin` → **System** shows the clinical reviewer, which services are on (smart reading, documents, push) and the last 100 app errors reported by phones.
* `/admin` → **Dashboard** shows the last smart-reading failure with its exact error.
* Back up Postgres daily (Railway → Postgres → Backups) and test a restore once before launch.

## Round 29 — the phone list (20 Oct 2026)

Twelve things Prasanna hit on an iPhone, all in one layer (`tools/live/live29.{js,css}`, patched by `tools/live/p29.py`) plus the
server side:

* **No zoom.** `maximum-scale=1, user-scalable=no`, `touch-action:manipulation`, double-tap and pinch suppressed everywhere
  except the three 3D stages and the map picker. Every input is ≥16px so iOS never zooms a form.
* **Tab bar.** `#mtab` is pinned to `calc(100vw - 24px)`; the labels keep their short form when the nav is rebuilt.
* **Assistant.** A new mark (`SX.assistMark`, an SVG orb with a running ECG trace) replaces the CSS circle; under the keyboard
  the hero folds away and the ask bar rides on `visualViewport`.
* **3D body.** On a portrait phone the camera takes a wider field (33°) and a 5% view offset, so the head clears the search
  bar, which is now a compact pill.
* **Heart Lab** leaves Home. `SX.heartOn(member)` looks at conditions, the regular doctor, medicines (through the layer-27
  classes) and two or more high BP readings; when it fires, the tab joins **Care**. Settings has Automatic / Always / Never.
* **Devices.** No Android download on an iPhone — an "Install on this iPhone" card (Share → Add to Home Screen) instead.
* **One location.** `SX.loc` is the single source: `get/where/set/gps/resolve`. `SX.mapPick()` is a Rapido/Uber-style picker —
  the map moves under a fixed pin, with search, "locate me", and (for addresses) door, landmark and PIN. It backs
  `SX.act.locset`, the Today and Book location card (`SX.locCard`), and the address book.
* **Google Maps.** `api/places.py` now calls the Geocoding API and Places API (New) when `GOOGLE_MAPS_SERVER_KEY` is set, and
  falls back to Nominatim/Overpass otherwise (`src` in the response says which answered). The browser key stays
  `GOOGLE_MAPS_KEY` in `env.yaml`.
* **Money** never wraps (`.sx-lo1>b`, `.sx-tot b`, tabular numerals).
* **SOS** acts on the press: no countdown, the call no longer blocks the alert, the last known fix goes out immediately, and a
  Web Audio siren + vibration run until "I'm safe". `GET /api/v1/sos/channels` tells the app which channels leave without a
  tap; the fan-out now also sends WhatsApp (Meta Cloud API, `WA_TEMPLATE_SOS`) and SMS through an MSG91 DLT flow
  (`MSG91_SOS_FLOW_ID`) when Twilio is absent.
* **Card vault** has prev/next arrows, a counter, dots and swipe.
* **Translations.** `SX.i18nDom` walks the DOM (text nodes, placeholders, aria-labels, titles) so strings outside `P()` are
  translated too; dates follow the language; the table is fetched `no-store` with a `__v` version. Anything still untranslated
  is posted to `POST /api/v1/i18n/missing`, stored in the new `phrases` table, translated in the background with Gemini and
  served to every device by `GET /api/v1/i18n` — the app's coverage now grows by itself.

## Round 30 — free for every family until 31 March 2027 (21 Oct 2026)

Growth before revenue: nothing in the app is sold to families for now, and the money comes from lab bookings, medicine
orders and the shop instead. The subscription machinery is untouched — plans, invoices, Razorpay, UPI and settlements
all still work — and switched off behind one check.

* `api/launch.py` is the whole switch: `FREE_UNTIL` (default `2027-03-31`, IST; empty ends the period). `free_now()`,
  `plan_of(household)` → `plus` while it runs, `state()` → `{free, until, label}` for the app and the site.
* Quotas read `plan_of()`, not the stored plan, so every family gets the top tier: unlimited smart readings, questions
  and insights. The only guard left is a per-family daily token allowance (`AI_DAY_TOKENS_LAUNCH`, 400,000) and the
  service-wide cap — abuse guards, not plan gates.
* `/api/v1/plans` prices every plan at ₹0 while the period runs and carries `launch` plus `listMonth`/`listYear` (the
  future prices, kept on file). `/subscribe` and the UPI plan flow refuse politely; order payments are unaffected.
* No plan lapses and no renewal notice goes out during the period (`housekeeping`).
* The app's Plan page becomes one card (live layer 30): what is included, how we earn, what happens after the date, and
  a day counter. The old page — prices, subscribe buttons, invoices — returns on its own when `FREE_UNTIL` passes.
* The site's three price cards become one "Free for every family until 31 March 2027" band, with the date read from the
  API; if the period is ever switched off, the script rebuilds the price cards from `/api/v1/plans`.
* To end the launch period: set `FREE_UNTIL: ""` in `deploy/gcp/env.yaml` and redeploy. Nothing else changes.

## Round 31 — the shop comes first, and ten documents a day (21 Oct 2026)

**Ten documents a day.** `AI_DAY_DOCS` (default 10) caps how many documents one family can have read by the AI between
midnights IST — counted on `report`, `prescription`, `card` and `policy` jobs only, so questions and insights keep their
own limits. The eleventh falls back to the basic reader with a plain message ("that is 10 documents read today"), the
same graceful path the monthly cap and the token budget already used; nothing errors and nothing is lost. `/hello` and
every analyse response carry `today` and `dayCap`.

**The shop in front.** Three engines existed and none of them ended anywhere a family could buy:

| Engine | Where it ended before | Where it ends now |
|---|---|---|
| `suggestions()` — checks due by age, sex, BMI, conditions and flagged results | a paragraph on Insights | **Due for <name>** at the top of Book a test, each row with a Book button |
| `/labs/quotes` — per-test prices at nearby labs | a sheet reachable only from a buried action | the page every booking route opens, with the lab preselected |
| the refill engine (round 24) | `Reorder` dropped a word into a 45-item search | matches the catalogue, adds to the basket and opens it |

* Tabs: **Tests & records** = `Book a test · My reports · Vault · Insights`; **Medicines** = `Order · My medicines · Orders`.
* New page `labshop` (live layer 31): due-for-you, eight packages, searchable catalogue with a multi-select basket, the
  "reports come back into the vault" promise, and the map of labs near you (`SX.placesHTML`, folded in from `nearlabs`).
* `p31.py` exports what the layer needs from the main script: `SX.suggestions`, `SX.medCatalog`, `SX.placesHTML`,
  `SX.labOpen(codes, lab)`. It also stops the price sheet printing "≈ ₹0" when no lab has quoted yet.
* Prices on the page are the *typical* market price from the test catalogue, never an invented floor; the real number
  comes from the lab quotes in the sheet.
* The morning "repeat this test" nudge now lands on Book a test instead of a list of addresses.
* Signing out goes to `/signin` (the sign-in sheet, with "Create an account") instead of the marketing page.

---

## Round 32 — one place for location, a heart that looks like a heart, chat first, and labs you can book

Four faults, all reported from a phone, all fixed in live layers 32–34. The service worker is at `dk-r34`.

### A. Location is asked once, for everything (`tools/live/live32.*`)

Location was being requested separately by SOS, labs, medicines and the map, so a family saw the browser prompt four
times and a refusal in one place said nothing to the others. There is now **one door**:

```
SX.needLoc(module)  →  first run: SX.locSheet()  →  per-module opt-in  →  fresh or saved fix
SX.geo(ask)         →  wrapped, so every existing caller goes through the same door
```

* The consent sheet names all six modules — **SOS, labs, medicines, care, alerts, live tracking** — all selected by
  default, each one the person may deselect. **SOS is locked on** (`req:true`, and `perm()` forces `mod.sos`): an
  emergency with no location is not a feature we will ship.
* Declining is a real answer: `Maybe later` keeps the app working and offers to pick the spot on a map instead.
* The header carries a status chip (`SX.locChip`) and Settings has a card listing which modules may use the fix, so it
  can be changed later without hunting through the browser's own settings.
* Live tracking (`SX.sosWatch`) uses `watchPosition` and only while an SOS is open.

### B. The heart (`tools/live/live33.*`)

The model was lit with flat lights and shaded like plastic. It now renders in a small studio:

* `studioEnv()` builds four emissive softboxes — key, crimson rim, cool rim, warm bounce — and bakes them through
  `PMREMGenerator.fromScene`, so every material gets real image-based lighting. Tone mapping is ACES Filmic.
* `noiseMaps()` generates a fractal-noise **normal map and roughness map** in a canvas at load. Without surface relief
  no amount of lighting stops a mesh reading as a balloon; this is the single biggest change.
* Myocardium is muscle-coloured rather than pink, the great vessels are cream and slate rather than lavender, and the
  specular is matte — the earlier version had blobby highlights that looked like latex.
* `myo.sheen` is a **Colour** in the three build we ship and a number in later ones; the code type-checks before
  assigning, because assigning the wrong one throws inside the renderer and the canvas goes blank.
* `p33.py` exports `gfx()` from the heart module so layers can reach the renderer; the export must be **outside** that
  module's IIFE — put it inside and `HL` never initialises, and the Heart Lab dies with
  `Cannot access 'HL' before initialization`.
* Today's metric tiles gained 7-day sparklines; the heart stage gained vitals cards, drawn only for rows that have a value.

**Still honest about this one:** the geometry underneath is procedural, so it reads as a good medical illustration, not
as a photograph. Getting to photoreal needs a real anatomical asset (a scanned/licensed heart mesh with its own texture
maps), which is a piece of work on its own.

### C. The assistant leads with the conversation (`tools/live/live33.js`, part b)

The mark was the size of the screen and the chat was an afterthought. On the assistant page the body now takes
`lv33-chat`, the mark shrinks into a slim top bar (`#lv33bar`, with **New chat**), and the suggestion chips move up
against the composer. Empty state keeps the larger mark; the moment a conversation starts, the chat owns the screen.

### D. Places you can actually use (`tools/live/live34.*`)

Three separate faults in one screen, all reproduced in the Playwright harness:

| Reported | Cause | Fix |
|---|---|---|
| "UI is shaking" | `SX.act.mapsel` called `render()`, which rebuilt the Google map under the finger on every tap | selection is now an in-place class toggle plus `SX.gmapPan(p)` on the kept `LASTMAP` instance; observers also pause while the page is scrolling (`SX.busyScroll`) |
| "Call & direction button is not professional" | three buttons in a flex row with no min-width collapsed into vertical letters | one primary **Book** on the row; Call / Directions / Map live in the sheet, `flex:1 1 0` with `nowrap` and a smaller type size under 400px |
| "There is no booking option" | `/labs/quotes` only knows **partner** stores, and in production there are none — so the sheet showed prices and no labs | `SX.labSheetHook` appends **Labs near you** from `/places?kind=lab`; picking one opens a test picker, sends the list on WhatsApp, offers a call, and saves it as a **planned test** that shows on Book a test |

Tapping a place opens `SX.placeSheet` — name, distance, rating, open/closed, address, hours, partner badge — rather
than selecting a pin silently.

### The scope trap worth remembering

Live layers run in a **different scope from the main script**. `typeof PLACES`, `typeof labSheet`, `typeof plSel` are
all `undefined` inside a layer, and because the lookups are wrapped in `try/catch` they fail *silently* — the feature
just does nothing. Anything a layer needs must be exported by the patch script first:

```python
one("SX.act.mapsel=…;", "SX.act.mapsel=…;\nSX.placesData=()=>PLACES;SX.setPlSel=v=>{plSel=v};", "mapsel")
one('const labCTA=…', 'SX.labQuotes=()=>LABS;\nSX.labSheetHook=f=>{…};\nconst labCTA=…', "lab sheet hook")
```

Two hours of this round went into that one lesson. Check `typeof` from inside the layer before assuming a name is reachable.

### Harness notes

`r32.py` and `r34.py` in the scratchpad. Two things that cost time:

* **Block the service worker** (`service_workers="block"` on the context) or `pg.route` fixtures never reach the page —
  the SW answers from cache and the test silently exercises the real endpoint.
* Playwright's glob `?` is not a literal; route API paths with `re.compile(r"/api/v1/places")`.

### Cost note (raised during this round, not yet acted on)

`deploy.sh` runs `--no-cpu-throttling --min-instances 1 --max-instances 1`, which is Cloud Run's **instance-based**
billing: a full vCPU and 1 GiB held 24×7, about **$47/month**, plus Cloud SQL on top. It is set that way because
`api/reminders.py`, `api/proactive.py` and `api/i18n.py` each start a `while True` daemon thread, which CPU throttling
would freeze, and `--max-instances 1` stops two containers sending every reminder twice.

Moving those three loops to **Cloud Scheduler** calling `/tasks/*` endpoints would let us drop `--no-cpu-throttling`
(idle billing falls from $0.000018 to $0.0000025 per vCPU-second, roughly **$10–14/month**) and raise max-instances
above one, which today is the whole capacity of the product.

---

## Round 33 — scalability and speed

Prompted by a comparison with Project Tracker (`projecttrackerindia/project-tracker`), which is ASP.NET Core 9 +
React 19 on an always-warm `e2-medium` VM. The conclusion of that comparison matters: **the framework was not the
problem.** Everything below is a configuration or query fault in our own code.

### A measurement warning, recorded so nobody repeats it

The first load test was run with `curl` loops from Cloud Shell and reported p95 of 15–30 s. A control run against
`https://www.google.com/generate_204` from the same shell reported `err=3/20, p95=15038ms`. **Cloud Shell cannot
generate load** — it is a small shared VM and the numbers were measuring the test client. Always run a control
against a known-good third-party endpoint before believing a latency number. The benchmarks below are from
`scratchpad/bench.py` against a local uvicorn, which has no such ceiling.

### Measured, before → after

| | before | after |
|---|---|---|
| `/app` for a client without brotli | **1,647,226 B** | **523,210 B** (−68%) |
| `/app` throughput, c=10 local | 134 rps | **253 rps** (+89%) |
| `/app` reopened with the same ETag | 521,375 B | **0 B — 304** |
| `/api/v1/i18n` | 33,706 B | **8,899 B** (−74%) |

### What changed

**1. The model call no longer freezes the container.** `/ai/analyze` is `async def` and called the Anthropic SDK
synchronously *on the event loop*, with no timeout — so it inherited the SDK default of **600 s**. One slow document
stopped every other request in the container, `/healthz` included, and Cloud Run then recycled the instance
mid-request. The reading now runs through `run_in_threadpool`, and the client is built with `timeout=AI_TIMEOUT`
(60 s, `AI_TIMEOUT_S`) and `max_retries=1`.

**2. The connection pool is sized.** `api/db.py` passed only `pool_pre_ping`, so SQLAlchemy's defaults applied:
5 + 10 overflow, `pool_timeout=30`. FastAPI's threadpool is 40 wide, so 25 concurrent requests blocked for 30 s
inside `SessionLocal()` and then raised. Now `pool_size=20, max_overflow=15, pool_timeout=10, pool_recycle=1800`
(all overridable by env). `pool_recycle` matters because the Cloud SQL proxy drops idle connections.

**3. Compression, which did not exist.** No middleware at all: every JSON response went out raw. Worse,
`web/index.html.br` existed but **`web/index.html.gz` did not**, so any browser that does not advertise brotli
downloaded the full 1.57 MB. `tools/compress.py` only refreshed variants that already existed, so the gap was
invisible. Now: `.br` and `.gz` are treated as a pair and the missing twins were generated, and
`GZipMiddleware(minimum_size=1024)` is installed as the safety net. The middleware skips anything that already
carries `Content-Encoding`, so the pre-built static variants are untouched and cost no runtime CPU — which matters:
compressing the 1.57 MB shell on the fly measured **660 ms per request** on one vCPU.

**4. Conditional requests.** The shell is served `no-cache`, i.e. *revalidate* — but starlette only honours
`If-None-Match` inside `StaticFiles`, which this app does not mount. Every reopen was a full resend. `_conditional()`
now returns a 304. Note the subtlety: `FileResponse` sets its ETag during `__call__`, not `__init__`, so the response
must be constructed with `stat_result=os.stat(path)` or the header is not there yet to compare.

**5. Listing files no longer loads them.** `GET /files` did `select(StoredFile)` where `blob` is a `LargeBinary`,
pulling every document's bytes into a 1 GiB container to report names and sizes. Now it selects five columns.

**6. Two N+1s on the hottest paths.** `/hello` (every app launch) did `len(h.orders)`, materialising every order row
to produce one integer → `func.count`. `/orders` lazy-loaded `Order.store` per row, up to 51 queries →
`joinedload`.

**7. Two missing indexes.** `ReminderSent.t` is range-deleted **every 60 seconds** and had no index; `Phrase` is
scanned on `(done, tries, created)` on every `/i18n` call. Both added — and because `create_all()` never adds an
index to a table that already exists, `ensure_indexes()` issues `CREATE INDEX IF NOT EXISTS` at boot, next to
`ensure_columns()`.

**8. The places rate limiter stopped holding a mutex across a sleep.** `_get()` slept inside `with _LOCK`,
serialising every caller at one per second *and* parking each one in the threadpool while it waited — 40 of those
and static file serving stops too. The slot is now reserved under the lock and the sleep happens outside it.

**9. The S3 client is cached and bounded.** `_s3()` built a new boto3 client per call (botocore reads its service
model off disk each time) and set no timeouts. Now cached, `connect_timeout=5`, `read_timeout=30`, 2 attempts.

### Known and not yet fixed

- **`--max-instances 1` is load-bearing, not only a cost setting.** `api/consult.py` keeps WebRTC peers in process
  memory (`ROOMS`), and `reminders.py` / `i18n.py` have no cross-process leader election. Raising it today would
  break video calls and double-send every reminder. Horizontal scaling needs the daemon loops moved to Cloud
  Scheduler behind a locked endpoint, and signalling moved to Redis or Cloud Run session affinity.
- Six other `async def` handlers still do blocking S3 or CSV work on the loop (`more.py:40`, `partner.py:203`,
  `partner.py:347`, `admin.py:427`, `shop.py:156`, `consult.py:402`). Lower traffic than `/ai/analyze`, and now
  bounded by the S3 timeouts, but they should move to the threadpool.
- `auth.py` `_HITS` is an unbounded in-memory rate-limit dict with no eviction, in a container that never restarts.
- `sos.fan_out` sends to up to 12 contacts serially (email, SMS, WhatsApp each) — worst case minutes, on the
  emergency path. Belongs in `BackgroundTasks`.

### Still open from the hosting comparison

Project Tracker runs on one `e2-medium` VM (2 vCPU / 4 GB) with docker-compose and Caddy, with Cloud SQL
`db-f1-micro` — about **$35/month, always warm**. We are on Cloud Run with `--min-instances 1 --max-instances 1
--no-cpu-throttling` plus `db-g1-small` — about **$82/month, and it still cold-starts**. Moving to the same one-VM
pattern would be cheaper and warmer, and would give the three daemon threads a natural home. Not done in this round.

---

## Round 35 — the shake, the theme, and buttons that stay in line

All four reported from a phone, with two screen recordings. Two of them were my own earlier fixes aimed at the
wrong place, which is worth recording.

### The shake was a feedback loop, not a map bug

Frame-by-frame, the map-pick footer alternates for the whole eight seconds:

```
"Finding the address… 13.07767, 80.23876"        ← 2 lines
"65/27, near Dowlath Towers, Kilpauk, Chennai…"  ← 3 lines
"Finding the address… 13.07767, 80.23876"        ← 2 lines
```

`reverse()` set `info=null; show()` before every lookup, which blanked the label to a **two-line** placeholder;
the resolved address is **three** lines. The sheet changed height → the map above it was resized to fit →
Google Maps fires `idle` on a resize → `idle` called `moved()` → another geocode → blank again. Forever.

Both halves are fixed:

* the label never blanks — the previous address stays on screen with a `busy` class, and CSS clamps the block to
  a fixed two-line / one-line shape so the sheet cannot change height at all;
* `idle` ignores a centre that has not moved more than **15 m** from the last resolved point, so a resize is no
  longer mistaken for a pan.

Verified: the sheet holds **one height (189 px) across 6 seconds, 0 changes, 0 geocodes** while idle.

Round 34 fixed `SX.act.mapsel` re-rendering the *places list*. That was a real fault, but it was not this one.
When a user says "the map is shaking", check which surface — the picker and the list are different code.

### Dark mode had been switched off for everybody

Two places wrote `data-theme="light"` whenever the stored value was not exactly `"dark"`:

```js
r.dataset.theme = saved==='dark' ? 'dark' : 'light';
new MutationObserver(()=>{ … else { r.dataset.theme='light'; ls('tht.theme','light') } })
```

Every dark rule is guarded by `:root:not([data-theme="light"])`, so an explicit `light` **overrides the phone**.
A device set to dark got the light app, and the *System* button in Settings did nothing because the observer put
the attribute straight back one tick later. Now `light` and `dark` are the only values ever written and *System*
removes the attribute, which is what lets `prefers-color-scheme` through. Dark mode renders correctly across
Today, Book a test, the assistant, the quote sheet and Settings.

`tests/test_round22.py` asserted the old light-first behaviour; it now asserts the new one, with the reason.

### Buttons that folded into vertical letters

"Details" rendered as `De tail s`. Round 34 fixed this inside the places sheet only. It is now one global rule —
`.btn, .chip { white-space:nowrap; flex-shrink:0 }` with `min-width:0` on the flex rows that hold them, so the
label beside a button is what gives way.

### Everything else in this round

* **The test picker** rebuilt the sheet's entire `innerHTML` on every tap, so the list scrolled back to the top
  each time a test was chosen. Now the row's class is toggled in place and only the count and total are rewritten.
* **The floating + button** sat on top of open sheets. It is hidden whenever a modal is open (`body.lv35-modal`).
* **The stage controls** (`Expand workspace`, `Full screen`) were a centred, wrapping, absolutely-positioned row,
  so on a short stage they rode up over the speciality chips. One line, bottom-anchored, scrollable, on their own
  surface.
* **The assistant in chat mode** gets a real column layout: `100dvh`-based height so an open keyboard does not
  strand the composer halfway up the screen, chips on their own line, page padding that clears the tab bar.
* **The medicine basket** drops its own "Use my location" button once the family has already granted location
  for medicines in round 32's consent sheet, and gains the same non-partner fallback the labs got: pharmacies
  from Google, with the basket sent on WhatsApp.

### Dead code worth knowing about

`SX.labCatalogue` was added to `tools/live/live31.js` during round 32, but layer 31 was already baked into
`web/index.html` by then, so the edit never reached the build. `pickTests` falls back to fetching `/labs/tests`,
which is why nobody noticed. **Editing a `live<N>.js` whose layer is already applied changes nothing** — the
chain is only re-run for layers that have not been committed yet. New behaviour goes in a new layer.

---

## Phase 0 — the scheduled work and the call rooms leave the web process

Groundwork for the multi-role platform. Nothing user-visible; everything after it was impossible without it.

### Why `--max-instances 1` was load-bearing

Two separate things pinned the service to a single container, and both are fixed here.

**1. Three daemon threads.** `api/reminders.py` (every 60 s), `api/proactive.py` (every 600 s) and the
`api/i18n.py` translator ran as `while True` threads inside the API process. CPU throttling freezes a thread
between requests, so `--no-cpu-throttling` was required; and a second container would have sent every reminder
twice, so `--max-instances 1` was too.

`api/tasks.py` gives each one an endpoint for Cloud Scheduler to call:

```
POST /api/v1/tasks/reminders    every minute
POST /api/v1/tasks/proactive    every ten minutes
POST /api/v1/tasks/i18n         every quarter hour
GET  /api/v1/tasks/health       when each last ran
```

* **Authentication fails closed.** No `TASKS_TOKEN` configured → 503, never an open endpoint. The token is read
  **per call, not at import**, which also stops test import order deciding whether auth works.
* **A database lease decides who runs a tick.** One conditional `UPDATE … WHERE until < now` — the database
  picks the winner, so no Redis and no leader election. The lease is released at the end so a minute-by-minute
  task is not blocked by its own safety margin, and an expired lease is taken over, so a container that dies
  mid-tick cannot block reminders forever.
* **`IN_PROCESS_LOOPS` switches the old threads off** (default on). Both on would double every reminder; the
  flag makes the switch-over reversible. All three modules honour it, and a test asserts that they do.
* `proactive` gained a callable `tick()`; the morning pass keeps its own `ReminderSent` guard, so calling the
  endpoint more often than planned cannot send a family two morning notices.

**2. The video call rooms.** `ROOMS` held live `WebSocket` objects in process memory. A socket belongs to one
process, so two peers on one call landing on two containers simply could not see each other.

Presence and relay now go through the database (`rtc_peers`, `rtc_relay`):

* a peer in **this** process still gets the direct in-memory path — no latency added to the common case;
* a peer on **another** container gets the message written to `rtc_relay`, and a per-socket pump polls every
  400 ms and delivers it;
* presence is a row with a 25-second TTL, heartbeated every 10 s, so a container that vanishes does not leave a
  call looking connected;
* undelivered messages older than 120 s are swept.

Polling a table is the right size for this: signalling is a few dozen small messages while a call is set up,
and once the peers are connected WebRTC is direct and the channel goes quiet. That volume does not justify
Redis. If group calls or very high volume ever arrive, this is the seam where Redis would go in.

### Still to do before raising `--max-instances`

* `api/auth.py` `_HITS` is an in-memory rate-limit dict — per container, so the limit multiplies by the
  instance count. It needs to move to the database or accept being per-instance deliberately.
* The deploy flags themselves: drop `--no-cpu-throttling`, raise `--max-instances`, create the three Cloud
  Scheduler jobs, set `TASKS_TOKEN`, then set `IN_PROCESS_LOOPS=0` — **in that order**, so there is never a
  window with nothing running the reminders.

### Regulatory findings that changed the design

Researched before building the clinical modules, and three of them contradicted the architecture as first
written:

* **Teleprescribing is not keyed to Schedule H.** The Telemedicine Practice Guidelines 2020 use their own
  lists — Prohibited (Schedule X, NDPS: never), List O (OTC: any mode), List A (**video first consultation
  only**), List B (**follow-ups only**). The engine keys on *list × consultation mode × first-or-follow-up*.
* **A pharmacist may not substitute.** Rule 65(11-A) is absolute. There is no substitution flow to build.
  Rule 65 also requires the dispensing details to be written **back onto the prescription**, no repeat
  dispensing without the prescriber's authorisation, an automatic prescription register entry, and a separate
  Schedule H1 register kept three years.
* **AI may not counsel the patient.** TPG §5.4 — AI/ML platforms may not counsel or prescribe. An intake agent
  may gather history for the doctor; it may not tell the patient what their symptoms mean.
* **Doorstep delivery is narrow.** The MoHFW s.26B notification of 26 March 2020 is the only clear route:
  Form 20/21 holder, Schedule H only (no H1/X/NDPS), **same revenue district**, prescription within 30 days for
  chronic and 7 for acute. Fulfilment must be district-local, and the catalogue needs a delivery fence separate
  from the prescribing fence.
* **Emergency sharing is lawful without consent** — DPDP s.7(f) covers a medical emergency threatening the life
  of the person or any other individual, provided it stays purpose-bound.
* **No 108/112 API exists**, and those numbers may never be presented as ours. Integration is a state-level
  agreement; the SOS button invokes the device dialler.

---

## Lab, slice 1 — the booking gains a person

The first vertical slice of the platform. Chosen because the lab flow already half-existed, and what it was
missing is exactly the thing the whole platform turns on: a named human doing the job, whose phone drives the
state and whose position the family can watch.

### What was already there, and what was a lie

`Store`, `PartnerUser`, `Order` and the partner console already existed, with a lab state machine
`placed → confirmed → collected → processing → ready`. So this slice **extended** that rather than building a
`ServiceRequest` table beside it, which is a change from what the architecture document first proposed —
having read the code, overloading `Order` is less code, no migration, and works with the existing console from
day one. The discipline that matters is the transition map and the stamped timeline, not the table's name.

One thing had to go. `confirmed` was labelled **"Phlebotomist assigned"** on the family's screen, when no
phlebotomist had been assigned and no such record existed. The label was a promise the product could not keep.
Assignment is now a state of its own with a named person behind it.

### The states

```
placed → confirmed → assigned → en_route → arrived → collected → processing → ready
```

`confirmed → collected` is still legal: a family that walks into the lab never had anyone travelling to them.

### The technician app

A new surface at **`/tech`**, with its own name (*Collect*), icon, teal palette and manifest, so it installs on
a phone as a separate app — while being the same codebase, the same auth cookie and the same deploy. This is
the "one codebase, six apps" idea from the architecture, proven on the first role rather than asserted.

Designed for someone between houses: 17px body text floor, 56px tap-target floor, one decision per screen,
and the two secondary actions (Call, Directions) given equal width so neither can collapse. Four taps —
**Start**, **I've arrived**, **Collected the sample** — and nothing else.

* `POST /api/partner/tech/jobs/{id}/start|arrived|collected` are **idempotent**: a technician whose tap times
  out and taps again gets a tap, not an error.
* A technician sees **only their own jobs**, and the job in hand stays pinned to the top of the list — a list
  that reorders itself when somebody taps Start is how the wrong job gets opened.
* `job_json` is deliberately narrow: the family's first name, address, landmark, phone and the tests. Not the
  household, not their records, not last month's bookings.

### Position sharing

`TrackPing` rows are written **only** while a job is `en_route` or `arrived`. A ping outside that window is
accepted and discarded, so a phone left running cannot keep broadcasting someone. The trail is swept 24 hours
after the job. The technician's screen says *"Sharing your location with this family until the sample is
collected"* while it is happening — a position trail belongs to an employee, and they should be able to see
that it is on without reading terms.

`GET /api/v1/orders/{id}/track` is the family's side, scoped to their own booking, and it degrades honestly:
live map → "last seen N seconds ago" → no map, call them. A stationary pin pretending to be live reads as
broken and is worse than an honest gap.

### A bug found only by running the UI

The sign-in form called `render()` **before** reading its own fields, so the inputs were rebuilt empty and the
login posted `{"email":"","password":""}`. The tests passed; curl worked; only a screenshot run against the
real page caught it. Every technician would have seen "Wrong email or password" with the right password typed.

Worth remembering: an API test proves the endpoint. It does not prove the screen.

9 new tests covering assignment, the four taps, cross-lab and cross-technician isolation, the ping window and
the family's view; full suite 182 passing.


### Follow-up: the technician app is Urban Health, in the partner colour

The first cut invented a teal palette and drew its own test-tube glyph. `BRAND.md` already answers both:

| Audience | Colour |
| --- | --- |
| Users (families) | Signal Blue |
| **Partners** (doctors, hospitals, pharmacies, **labs**) | **Care Teal `#0B8A7C`** |
| Admin | Graphite |

So the technician app now uses the real partner mark from `web/brand/svg/partner-mark.svg`, Care Teal, the
family app's greys, radii, shadow and type stack, and the `partner-icon` PNGs in its manifest. It reads as
Urban Health in the partner colour rather than as a different product, which is what a technician glancing
down should see.

The rule this sets for the five roles still to come: **a role gets an accent, not a look.** One design system,
one set of structural tokens, one type stack; only the accent and the mark change, and which accent is not a
free choice — it is in the brand guide.

---

## Lab, slice 2 — the family watches them come

The other half. A technician's phone is now sending its position; this is what the family sees. The card shows
on Today and on Orders, because someone waiting at the door should not have to go and find the right screen.

### What it says, and why each line is true

| What we know | What the family sees |
| --- | --- |
| Technician pinging | "Ravi Kumar is on the way · 922 m away · Today 7–9 AM", live map, Call |
| Pings stopped | "Last seen 2 min ago" — the map stays, the claim does not |
| En route, never shared | "Not sharing their location right now — call them if you need to." |
| Assigned, not started | "Ravi Kumar is assigned · They will set off closer to your slot." |
| Arrived | "Ravi Kumar has arrived" — the pulse stops; nothing is moving any more |

**Distance, not an invented ETA.** We have the technician's position and the family's address, so straight-line
distance is something we can stand behind. "8 minutes" would need a routing call we are not making, and a wrong
number on a doorstep is worse than no number. The Routes API slots in later behind the same line.

**No map without a maps key.** `SX.gmapHTML` still returns a container when no key is configured, which paints
as an empty grey box — worse than no map, because it reads as something that failed to load.

**Repaint, never re-render.** Re-rendering the page would rebuild the Google map on every tick, which is
exactly the fault that made the places list shake in round 34. The card swaps its own text and dots and pans
the existing map instance.

### Three things that cost time, worth writing down

**The scope trap, again.** The layer used bare `S.liveOrders`. `S` is the main script's state and is not in
layer scope, so it fails *silently* — the card simply never appeared. `SX.S` is the handle. This is the second
round in a row this has bitten; it is now asserted in a test.

**`#page` is a grid.** The card was prepended and *was* the first child of `#page`, and still rendered at
774px down the screen — because the page lays its cards out on a grid. Being first in the DOM is not being
first on screen. `order:-1; grid-row:1` fixed it. Somebody arriving at the family's door outranks the step
counter.

**The fetch throttle was longer than the poll.** The first fetch happens before the family has signed in, so
it pins an empty result; with a 20-second throttle against a 10-second loop, the card did not appear until
long after the technician set off. The throttle is now shorter than the interval, so every tick really
refetches.

### A real fault the test seeding exposed

`_status()` derived the family's step from the **timeline alone**, ignoring `o.status`. Any path that moves the
status without appending a timeline entry — an admin fixing something, a migration, a partner integration —
showed the family a step behind reality. It now takes whichever of the two is further along.

10 new tests; full suite 192 passing.

## Lab slice 3 — the lab runs its own collection team (2026-10-21)

Slices 1 and 2 built the technician app and the family's live card. Both were unreachable: **no `PartnerUser`
with role `tech` could be created anywhere in the system.** Admin's role list was `owner | staff | doctor`, and
the partner console had no roster screen at all. `GET /partner/techs` would have returned an empty list forever.

- **The lab owner runs the roster, not our admin desk.** A lab with a dozen phlebotomists and ordinary turnover
  cannot wait on us for every hire, and it is the lab that employs them, pays them and answers for them at a
  family's door. We gate the store; the store gates its staff. Doctors stay with admin, because a medical
  council registration is ours to verify. Admin can also create technicians (`role: "tech"`, labs only).
- **Sign in with the mobile number.** A phlebotomist between houses remembers their phone, not an address the
  lab invented for them. `find_user()` resolves an identifier without an `@` against the phone; the number is
  kept unique among active sign-ins at creation, so it cannot match two people. `+91`, a leading zero and
  spaces all normalise to the last ten digits.
- **A technician with no email of their own** is keyed by a reserved `@tech.invalid` address (RFC 2606, so it
  can never reach anybody). It is an internal column value, never displayed and never mailed.
- **The one-time password opens nothing.** It was handed across a counter and is written on a slip. Until the
  technician replaces it, `/api/partner/tech/*` returns 403 — behind there are families' addresses and phone
  numbers. The Collect app shows a "Choose your password" screen as the way out of that 403.
- **`POST /orders/{oid}/status` now refuses `assigned`.** Clicking "Assign a technician" used to move the
  booking with nobody attached — the same lie as the old "Phlebotomist assigned" status line. Assignment
  happens one way, through the picker, which requires a person. `porder()` drops `assigned` from `next` and
  adds `agent` and `canAssign` instead.
- **Turning someone off** stops the sign-in but is refused while they are out on a collection: a half-done job
  still needs finishing. Reassign it first.

New: `POST /partner/techs`, `POST /partner/techs/{uid}/reset`, `POST /partner/techs/{uid}/active`; the
"Collection team" view and the inline assign picker in the partner console; the password screen in `/tech`.
18 new tests, suite at **210**.

Verified in a browser end to end: owner adds Ravi Kumar, the one-time password is shown once, the technician
signs in at `/tech` with `9876512001`, is forced to choose a password, and sees the job with the family's
address, Call and Directions.

## Lab slice 4 — how was the visit? (2026-10-21)

The last thing the user described in the lab loop: "lab technician will get review and I'll send amount and
will track reviews." This is the review half.

**It is a separate judgement from the store rating, deliberately.** A family has a clear and immediate opinion
about the person who stood at their door with a needle, and it is not the opinion they will have two days
later about a PDF. Under one star, a gentle phlebotomist at a slow lab and a rushed one at a fast lab score
identically, and neither lab learns anything it can act on. So `Order` gained `visit_rating / visit_tags /
visit_note` beside the existing `rating`, and `PartnerUser` gained `rating / rating_n` of its own.

- **Asked the moment the sample is in the bag**, not when the report lands — by then the family is rating the
  report and calling it the visit. `canRateVisit` is true once `done_at` is set and an agent is attached.
- **The tag list follows the stars.** Five stars asks what went well; two asks what went wrong. Asking "what
  went well?" under two stars is not listening. Only tags we offered are stored, so they can be counted.
- **Once only**, so the running mean stays honest; one bad morning does not define somebody and a long good
  record is not erased.
- A booking with nobody on it — a family who walked into the lab — is never asked.
- The roster shows **★ 4.8 · 12 visits** per technician; the Collect app shows a technician their own.

New: `GET /api/v1/visit-tags`, `POST /api/v1/orders/{oid}/visit-rating`; live layer 37 (`dk-r37`).
11 new tests, suite at **221**.

Also added to `ensure_columns()`: the slice-1 columns on `orders` (`agent_id`, `accepted_at`, `started_at`,
`arrived_at`, `done_at`). They were only ever created by `create_all()`, which does not touch an existing
table — fine on this database because the table was created after the model gained them, but not something to
leave resting on luck.

### Verified in a browser
Card appears on Today reading "How was the visit? · Ravi Kumar collected your sample · Tap a star". Two stars
switches the tag list to Late / Rushed / Several attempts / Careless with hygiene / Hard to reach; five
switches it back. Submitting posts `{"rating":5,"tags":["On time"],"note":"..."}` to
`/api/v1/orders/{id}/visit-rating`, the sheet closes and the card goes. In demo mode the write is swallowed,
which is correct — the demo banner says nothing is saved.

## Lab slice 5 — settlements that can actually be settled (2026-10-21)

The other half of "I'll send amount". A monthly settlement computation already existed in `api/network.py`
and the direction logic in it was right. Three things were missing.

**Nothing recorded that a payout had happened.** The figures were recomputed from the orders on every page
load, so a month settled in March looked identical to one nobody had touched, and next month's view showed
the same number again. A new `Payout` table holds one row per store per month: the figures as they stood at
the moment of settling, who settled it, when, and against which bank reference. Frozen on purpose — a refund
or a rate change next week must not quietly rewrite what was paid. A bank reference is asked for because a
payout nobody can trace is a payout that gets made twice. Unsettling is possible and is logged, with a
confirmation that says why it is dangerous.

**The commission was global.** `PARTNER_FEE_PCT` applied to everyone. Real contracts differ, so the rate now
lives on the store (`Store.commission_pct`, nullable) and the env var is only the fallback. Nullable rather
than defaulting to zero, because a launch partner on 0% is a real contract and "0" and "unset" cannot be the
same value. Admin sets it by clicking the percentage in the settlements table.

**The partner could not see any of it.** A lab that cannot see what it earned will telephone every week, and
will be right to. `GET /api/partner/earnings` gives the owner their own statement, six months by default,
from *the same computation the admin side settles against* — two computations would eventually disagree and
the partner would be the one who noticed. Owner only: money is the owner's business, not the front desk's.

The two directions stay two columns rather than one netted figure, because they are two different transfers:
we send them what we hold from online payments, they send us the fee on the cash they took at the door. Most
of this will be cash to begin with, so a ledger modelling only one direction would be wrong in the common
case.

New: `POST /api/admin/settlements/{month}/{store}`, `DELETE` the same, `POST /api/admin/stores/{sid}/commission`,
`GET /api/partner/earnings`; Earnings view in the partner console; Mark settled / undo / rate in the admin
console; four more CSV columns. 17 new tests, suite at **238**.

### Verified in a browser
Partner: October ₹5,050 over 4 completed, ₹1,750 of it cash → we owe ₹3,036, they owe ₹140, 8%.
Admin: same row, **Mark settled** → drawer saying "Pay ₹2,896 to Lucid Diagnostics" → reference recorded →
row becomes a green ₹2,896 with the UTR under it and an undo.

### Still blocked on a decision
Paying for a booking at checkout needs a Razorpay merchant account (KYC) for Urban Health. The plumbing
in `api/payments.py` is already written and used for subscriptions; nothing can be exercised end to end until
that account exists. The ledger above does not depend on it.

## Rate limiting that holds across containers (2026-10-21)

The last thing pinning the service to `--max-instances 1`, besides the loops Phase 0 already moved out.

`limit()` was a dict in each process. That was exactly right while one container served everything and wrong
the moment two did: eight sign-in attempts per container is eight times eight across eight containers. The
dict also grew one key per attacking address and never dropped it — a slow leak with an attacker holding the
tap.

**Two layers now, and both earn their place.** The in-process deque is first because it is free, and because
it is the only thing still standing when the database is unreachable; a limiter that raises 500 on a database
blip takes sign-in down with it, which is a worse outage than the one it was guarding against. The shared
counter in `rate_hits` is second, and is what makes the budget one budget.

**The window is kept as the hit times, not a count and a start time**, so it slides the way the deque did. A
fixed window lets a burst through at twice the rate as it rolls over, which on a sign-in endpoint is the
exact thing one is guarding against. On Postgres the read-modify-write is taken `FOR UPDATE`, or two
containers both read 7 and both write 8. Rows older than a day are swept every fifteen minutes by whichever
request notices.

**Sign-in counts failures, not attempts.** `guard` / `fail` / `clear` replace the two hand-rolled `FAILS`
dicts in `admin.py` and `partner.py`. Somebody who keeps signing in correctly is not an attacker, and a
fat-fingered morning should not lock out the afternoon.

One test-harness consequence, worth knowing: `conftest.py` now clears both layers between tests. Left alone,
a full run spends the signup budget around the ninth test that signs anybody up, and everything after it gets
a 429 from a limiter working exactly as intended — which is how this was found.

12 new tests, suite at **250**.

### Phase 0 switch-over, in this order
1. Create the three Cloud Scheduler jobs and set `TASKS_TOKEN` (see the docstring in `api/tasks.py`).
2. Confirm `GET /api/v1/tasks/health` shows all three running.
3. Set `IN_PROCESS_LOOPS=0`.
4. Only then drop `--no-cpu-throttling` and raise `--max-instances`. The limiter above is what makes step 4
   safe; it was the remaining per-container state.

## Pharmacy slice 1 — "Pharmacist checking" becomes true (2026-10-21)

The family's medicine status line has read **"Pharmacist checking"** since the first version of this app.
No pharmacist was named, registered or recorded anywhere. Exactly the shape of the lab's old "Phlebotomist
assigned", and exactly the same fix: make it true or stop saying it.

- **A registered pharmacist is a role the pharmacy creates itself** (`role="pharmacist"`), like the lab's
  technicians. The roster code is now one role-aware implementation rather than two that would drift:
  `SELF_ROLES` says which store kinds may create which role and what each one needs.
- **The State Pharmacy Council registration number is required.** Not paperwork — dispensing a prescription
  without a registered pharmacist *is* the offence, and the number is what puts a named, answerable person
  behind every order that goes out. A pharmacy owner who is themselves the registered pharmacist records
  their own number once, through `POST /partner/my-registration`.
- **Packing is gated.** `POST /orders/{oid}/status` refuses `packing` on any medicine order that has a
  prescription-only line and no sign-off. A counter assistant (`role="staff"`) cannot sign one off; nor can
  anybody still on the one-time password they were handed across a counter.
- **What is recorded** is who checked it, when, and the three things that make a prescription checkable
  afterwards: the prescriber, their registration number, and its date — plus a free note for anything queried.
- **No substitution, by construction.** Rule 65(11-A) forbids it outright, so the check screen offers no way
  to change what was ordered. If a medicine cannot be supplied the choice is to part-supply and message the
  family, or to refuse.
- **Refusing says why.** "Cancelled" with no reason simply sends the family to the next pharmacy with the
  same prescription; the reason is shown to them verbatim.

New: `GET /partner/pharmacists`, `POST /partner/orders/{oid}/verify`, `POST /partner/orders/{oid}/refuse`,
`POST /partner/my-registration`; a Pharmacists roster and an inline check form in the partner console; admin
may create the role too. 16 new tests, suite at **266**.

`tests/test_round7.py` needed updating: it walked a prescription order straight to packed. The fixture now
chooses a password and records a registration first, with the reason written into the test.

### Verified in a browser
Order row shows **"prescription not checked — a registered pharmacist must check it before this can be
packed."** Adding Priya Nair with AP/12345 puts her on the roster. The owner clicking **Check prescription**
is asked for their own registration number first, then gets the form, which names the prescription-only line
and says plainly that substitution is not an option. After signing off the row reads *"Checked by Apollo
Owner AP/99887 · prescriber Dr A Sharma TSMC/55512 · dated 2026-10-19"* and Packed is available.

## Pharmacy slice 2 — the pick list (2026-10-21)

The batching half. A pharmacist with fifteen orders open does not walk the shelves fifteen times, so the list
comes back **gathered by medicine**, each line carrying the orders it is made of: eighty-five strips off one
shelf, split into packets at the counter.

- **Prescription lines sort first**, so they are picked while the paperwork is still in hand.
- **An unchecked order stays on the list, marked waiting**, rather than quietly left out — a picker who
  cannot see why an order is missing will assume the list is wrong. The quantity it contributes is shown as
  *held* on its line, so the shelf count is still right if the check comes through.
- **A packed order leaves the list.** `PICKABLE` is `checking` only; a list that does not shrink as you work
  it is one nobody trusts by the third batch of the morning.
- **One bad order does not sink the batch.** Each is put through the same single-order rules; the ones that
  fail come back named with the reason, and the rest are packed. Rolling everything back because of one
  unchecked prescription means doing the batch again by hand.
- Packing twice is a tap, not an error. Another pharmacy's order is refused by id.
- The view prints: the stylesheet drops the sidebar and controls, because this is a sheet somebody carries
  down an aisle.

New: `GET /partner/picklist`, `POST /partner/batch/pack`; the Pick list view. 13 new tests, suite at **278**.

### Verified in a browser
Five orders → 4 ready, 1 waiting, 4 lines: Metformin 6, Amoxicillin 3 (1 held), Paracetamol 10, ORS 6
(2 held). **Mark picked as packed** → 0 ready, 2 lines, and only Vikram's unchecked order left on the sheet.

## Pharmacy slice 3 — the prescription record, both ways (2026-10-21)

Two halves of the same record, now that a named registered pharmacist signs every prescription off.

**The family is told who checked it.** `order_json` carries `checkedBy` — name, registration number and
when — and live layer 38 puts a green line under the order: *"✓ Checked by Priya Nair · Pharmacist
AP/12345"*. A pharmacy council registration is a public professional credential, and showing it is most of
what separates a pharmacy from a website that posts medicines through a letterbox. The family is **not**
shown the prescriber's details back: they wrote it, it is theirs, and what is new to them is who at the
pharmacy checked it.

`_checked_by()` takes the pharmacist off the order's own session via `object_session`. `order_json` runs in
a loop over a family's orders, so opening a connection per row turns a list of twelve into twelve
round-trips.

**The pharmacist is told how old it is.** Doorstep delivery under MoHFW s.26B (26 March 2020) asks for a
prescription no older than 30 days for a repeat of a chronic medicine and 7 for an acute course. Entering
the date now shows the age inline before they sign: green under a week, plain up to thirty days, amber past
that with the rule quoted.

**It is a note, never a refusal.** The registered pharmacist is the professional, and software substituting
its own judgement for theirs is precisely what TPG §5.4 forbids. We state the fact; they decide. The
thresholds come from `GET /partner/rx-rules` rather than being written into the console's JavaScript, so
there is one place they live.

New: `GET /partner/rx-rules`, `checkedBy` on the family's order, `rxAgeDays` on the partner's; live layer 38
(`dk-r38`). 10 new tests, suite at **289**.

## Doctor slice 1 — the OP queue (2026-10-21)

Video consults, prescriptions and visit requests already existed. The queue did not, and it is the part of
Indian outpatient care that actually happens: walk-ins, a number, and a room full of people watching a board.

- **The number restarts at 1 for each doctor each day**, because that is how every OP counter in the country
  already works and so is the number people will call out and look for.
- **One queue, not two.** A family with a confirmed appointment joins the same list when they arrive. One
  list the counter can see beats two it has to reconcile in its head.
- **Most of a morning's queue is not on the app**, so `POST /partner/queue/add` gives a number to somebody
  who simply walked in. No household is attached, nothing is sent to a phone; the number goes on a slip.
- **The estimate only speaks when the day supports it.** `pace()` is the median of this doctor's last eight
  finished consultations today, and under three it returns nothing — the screen says "pace not known yet"
  rather than inventing a figure. A confident wrong "10 minutes" is why people stop watching the board and
  crowd the door. Same reasoning as straight-line distance instead of an invented ETA on the lab side.
- **`POST /partner/queue/next` finishes the person in the room and calls the next**, in one tap, because
  that is the whole job at a counter and should not be two.
- The family is pushed when their number is called, and told how to get back in if they were passed over.
- A doctor signing in sees their own queue without picking, and cannot reach into another doctor's.

New: `api/queue.py` — family `POST/GET /api/v1/queue`, `/queue/{id}`, `/queue/{id}/leave`; counter
`GET /partner/doctors`, `GET /partner/queue`, `POST /partner/queue/{id}/move`, `/queue/next`, `/queue/add`.
`GET /api/v1/doctors` now carries each doctor's live queue so a family can decide whether to set off.
20 new tests, suite at **309**.

### Two faults the browser run found, which the tests could not
- The counter opened on the **alphabetically first** doctor — an empty queue, while a room full of people
  sat one dropdown away. It now opens on whoever has somebody in the room, then whoever has most waiting.
- By eleven o'clock the finished rows are most of the list and the live ones are below the fold. The day's
  history folds behind a "Show the 12 already finished today" line.

Also guarded `loadQueue`/`loadDoctors` against the counter navigating away mid-request: the 20-second
refresh was writing into an element that no longer existed.

## Doctor slice 2 — the screen on the waiting-room wall (2026-10-21)

The visible half of the queue. `/counter?t=<token>` is a board a clinic opens once on a television and then
leaves alone.

- **No sign-in.** The token lives in the URL. A television that wants an email and a password every morning
  is a television that gets switched off in week two. The owner makes the link in Store profile; replacing
  it blanks any screen still on the old one, which is how a clinic takes back a link that walked out of the
  building.
- **Numbers and doctors, never patients' names.** A waiting room is a public place and a shareable link is
  shareable. A name on a wall beside a specialty says more about somebody than they agreed to. The test
  asserts the response body contains neither the name nor the phone.
- **Dark unconditionally, not by preference.** A television reports whatever its browser shipped with, which
  is nearly always light, so honouring `prefers-color-scheme` would mean the wall display almost never looks
  like one. A waiting-room board should read like an airport board, and a wall of white light is unkind to
  people who are already unwell.
- **One doctor fills the screen** — `:has(.room:only-child)` grows the number to 34vh, because a small
  clinic is the common case and the number is the whole point.
- **The only thing that moves is the number being called**, so the movement means something.
- **A frozen screen admits it.** After three failed polls the footer says how long ago it last changed and
  to ask at the counter. A board that silently stops is worse than none: people stand up at the wrong number.

New: `counter/index.html`, `/counter`, `GET /api/v1/board/{token}`, `GET|POST /partner/board-token`,
`Store.board_token`. 13 new tests, suite at **322**.

### Verified in a browser
Owner sets the link in Store profile → opening it on a 1920×1080 page shows **Dr Rao · General medicine · 5
· WITH THE DOCTOR · NEXT 6 7 8**, dark, with the clock and a live dot. The first run came out in light mode
and with the card floating in a third of the screen; both are fixed above.

## /api/health finally says what is running (2026-10-21)

`VERSION` read `RAILWAY_GIT_COMMIT_SHA`, which nothing on Cloud Run sets, so the health endpoint has
reported `"dev"` for every deploy since the move. Several deploys today were therefore verified by reading
a service-worker cache name out of a terminal — and when Cloud Shell was unreachable, not verified at all.

`deploy.sh` now stamps `APP_VERSION` (the short commit) and `APP_BUILT` into `env.yaml` **before** the
build, so the value names exactly what was built rather than whatever HEAD had become by the time the build
finished. `/api/health` returns both, plus `sw` — the service-worker cache name read from the file we
actually ship, which is what decides whether a family's phone picks up new front-end code.

One public URL now answers "did that land?":

    curl -s https://urbanhealth.in/api/health

4 new tests, suite at **326**.

## Doctor slice 3 — the prescription drafts itself from what the doctor said (2026-10-21)

The transcript was sitting there while the doctor retyped, from memory, the medicines they had named out
loud twelve minutes earlier. `POST /partner/consults/{aid}/rx-draft` fills the form in from this consult's
own captions. It saves nothing; the doctor still signs with `PUT .../rx` exactly as before.

**Extraction, not completion.** TPG §5.4 is explicit that software must not prescribe, so every instruction
to the model is about *not* helping: include a medicine only if the doctor said it, leave every field they
did not say empty, never infer a strength or a duration, never change a heard number. An empty duration the
doctor fills in is correct. A plausible "5 days" nobody said is a fabricated prescription with a real
registration number at the bottom of it.

- Each drafted row carries **`heard`** — the doctor's own sentence about that medicine, quoted back, so the
  check takes a glance rather than a replay.
- A strength that sounded ambiguous is flagged `unclear` rather than silently corrected; flags for
  medicines that did not make the form are dropped, because a warning you cannot act on is noise.
- `_parse_draft` keeps only values the form can hold: a frequency of "as the doctor advised" becomes empty,
  not a blank nobody notices on a signed PDF.

### A back door this closed
`RxItem.frequency` defaulted to `"od"`. Any client that left it out produced a signed prescription saying
**once a day** that nobody had said — the same fabrication, arriving by the back door while the draft
endpoint refused it at the front. The default is gone and the save now refuses an item without a frequency
from the known set; the form's dropdown starts on "— how often —" instead of pre-selecting a dose.

13 new tests, suite at **339**.

## SOS — the sends you can actually see (2026-10-21)

Reported from a real alert on an iPhone: *"it didn't send any messages, it just showed a popup to call."*

It was working as built, which was the problem.

**Why nothing was texted.** `fan_out()` drives every channel the server can drive. `messaging.alert_sms_ready()`
and `whatsapp.ready()` both return false in production, so SMS and WhatsApp are skipped; email and the
family's app alert went. The code for both is written and tested — it is waiting on credentials, nothing
else:

- **SMS** — `MSG91_AUTH_KEY` + `MSG91_SOS_FLOW_ID` (a DLT-registered transactional template), or Twilio.
- **WhatsApp** — `WA_TOKEN`, `WA_PHONE_ID`, and an approved utility template in `WA_TEMPLATE_SOS`.

A web page on a phone cannot send an SMS or a WhatsApp on somebody's behalf; `sms:` and `wa.me` only open
the composer. So "no tap" is reachable only from the server.

**What was ours to fix.** One tap is defensible; hiding that tap in a small grey chip below the fold, beside
status text that looks identical, is not. Layer 39 lifts the sends to directly under the call buttons:
"Text everyone · 2" as a full-width bar (one `sms:` with every number is a real single tap on both
platforms), then 52px-tall WhatsApp and SMS buttons per contact — pressed with a shaking hand, possibly
somebody else's. The old chips stay, dimmed, as the record of what went out. The whole block **removes
itself** once `/sos/channels` reports both channels live, so configuring the accounts needs no code change.

**The siren that sounded once.** It kept its `AudioContext` in a closure, so when iOS suspended the context
— phone locked, or the person switched to WhatsApp — nothing could reach in and resume it. Layer 39 replaces
`SX.siren` with the same interface (`start/mute/stop/on`) over a context it can wake on `visibilitychange`,
`focus`, `pageshow` and the next touch. A muted siren stays muted: taking that choice back because somebody
tapped the screen would be its own kind of broken.

**A promise the phone could not keep.** The panel said "a siren sounds and your phone buzzes until you tap
I'm safe". `navigator.vibrate` does not exist on iOS Safari, so on an iPhone the buzzing half was never
true. It now says what the device can do. (iOS also silences Web Audio when the ring/silent switch is off —
only the Capacitor build can override that.)

10 new tests, suite at **349**. `test_rx_transparency` pinned `dk-r38` exactly; loosened, since every later
layer bumps it.
