# Deploy TheHealthTracker on Railway

1. **Repository.** Unzip, then push the `thehealthtracker` folder to a new GitHub repository (the folder is the repo root).
   ```
   cd thehealthtracker && git init && git add . && git commit -m "TheHealthTracker" && git branch -M main
   git remote add origin https://github.com/<you>/thehealthtracker.git && git push -u origin main
   ```
2. **Project.** railway.app → New Project → Deploy from GitHub repo → pick the repository. Nixpacks detects Python and uses
   the start command and `/healthz` health check from `railway.json`.
3. **Database.** In the project: New → Database → PostgreSQL. Railway exposes `DATABASE_URL` from it.
4. **Variables.** Open the web service → Variables → Raw Editor, paste the block below, fill the values, Deploy.

```
SECRET_KEY=<64 hex characters>
ADMIN_EMAIL=admin@thehealthtracker.com
ADMIN_PASSWORD=<12+ characters>
DATABASE_URL=${{Postgres.DATABASE_URL}}
RP_ID=thehealthtracker.com
APP_ORIGIN=https://thehealthtracker.com,https://www.thehealthtracker.com
RESEND_API_KEY=
MAIL_FROM=TheHealthTracker <no-reply@thehealthtracker.com>
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
> (e.g. `thehealthtracker-production.up.railway.app`) and `APP_ORIGIN` to `https://` + that host. Passkeys are bound to
> `RP_ID`: passkeys created on the Railway address will not work on thehealthtracker.com, so switch both variables to the
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
| `LEGAL_ENTITY`, `LEGAL_ADDRESS` | yes before launch | Shown on /privacy and /terms (registered name and address of the business). Defaults: `TheHealthTracker`, `Hyderabad, Telangana, India`. |
| `GRIEVANCE_NAME`, `GRIEVANCE_EMAIL` | yes before launch | Grievance Officer shown in the privacy policy (DPDP Act). `GRIEVANCE_EMAIL` falls back to `SUPPORT_EMAIL`, then `ADMIN_EMAIL`. |
| `SUPPORT_EMAIL` | recommended | Contact address on /terms. |
| `POLICY_UPDATED` | no | Date shown on the policy pages, e.g. `18 October 2026`. |
| `DATA_KEY` | yes before launch | 64 hex characters (`python -c "import secrets;print(secrets.token_hex(32))"`). Encrypts each family's health store at rest. Without it a key is derived from `SECRET_KEY`. **Never change it after launch**: stored data becomes unreadable. |
| `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | for phone notifications | Reminders and missed-dose alerts when the app is closed. Generate once: `python -c "from api.push import make_keys; print(make_keys())"` and paste `VAPID_PRIVATE_KEY`; `VAPID_SUBJECT` is `mailto:support@yourdomain`. Changing the key signs every phone out of notifications. |
| `S3_BUCKET`, `S3_ENDPOINT`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | recommended | Where families' documents (encrypted) are kept: Cloudflare R2, AWS S3 (ap-south-1, Mumbai) or Backblaze B2. Without a bucket, documents are stored encrypted in Postgres (fine for a small launch; `FILES_CAP_MB` per family, default 2048). |
| `APP_ENV` | staging only | `staging` shows a ribbon in the app and sends `noindex` headers. |
| `CANONICAL_HOST` | recommended | e.g. `thehealthtracker.com`. Sends www.… visitors to this address so the sign-in cookie is always the same. Set it only after both addresses open the site. |
| `PORT`, `RAILWAY_GIT_COMMIT_SHA` | — | Set by Railway. Do not add them. |

### After editing any page

The server sends the compressed copy of a page (`index.html.br` / `.gz`) when the browser accepts it. After changing
`web/index.html` or anything in `site/`, run `python tools/compress.py` and commit the refreshed copies.
`python tools/compress.py --check` fails if any copy is stale. The server also refuses to send a stale copy (it falls back
to the uncompressed file and prints a warning in the deploy log), so a forgotten step costs speed, not correctness.

5. **Domain.** Service → Settings → Networking → Custom Domain → `thehealthtracker.com` (and `www`). Add the CNAME record Railway
   shows at your domain registrar. HTTPS is issued automatically.
6. **Check.** `https://thehealthtracker.com/healthz` returns `{"ok":true}`. The landing page is `/`, sign-in `/signin`, sign-up `/signup`, the app `/app`, the admin panel `/admin`.
   Create your own account, add a passkey (Settings → Account & security), sign out and sign back in with it.
7. **After launch.** In `/admin`: change seed partners to real ones, verify them, review plans (Free / ₹39 / ₹99), seasonal advisories and videos.

## A staging copy (check every change before families see it)

1. In the same Railway project: **New → GitHub repo → this repository**, branch `staging`. Add a second Postgres plugin for it.
2. Variables: copy from production, then set `APP_ENV=staging`, `OTP_DEMO=1` (codes on screen; never on production), a different `SECRET_KEY` and `DATA_KEY`, and **no** Razorpay live keys. Leave `S3_BUCKET` empty or use a separate bucket.
3. Generate a domain for it (for example `staging-thehealthtracker.up.railway.app`) and set `RP_ID` / `APP_ORIGIN` to that address.
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

**Identity from Aadhaar (DigiLocker).** There is no public Aadhaar login for apps; UIDAI e-KYC is only for licensed AUA/KUAs. The sanctioned route is DigiLocker: register at <https://partners.digilocker.gov.in> (Requester, OAuth 2.0; redirect URI `https://thehealthtracker.com/api/v1/digilocker/callback`; documents: Aadhaar e-KYC) and set `DIGILOCKER_CLIENT_ID`, `DIGILOCKER_CLIENT_SECRET`. Then sign-up offers *Verify with Aadhaar via DigiLocker* instead of the mobile code (email code stays), the account name and date of birth come from Aadhaar and lock, the masked Aadhaar card (last 4, demographics, photo) is kept encrypted in Cards, and the verified badge accepts Aadhaar in place of the mobile code. Mobile numbers still need our own OTP (MSG91) — e-KYC does not return the mobile.

**ABHA / ABDM.** `api/abdm.py` implements the v3 flows (session token, public certificate, Aadhaar-OTP enrolment, login by ABHA) behind `ABDM_CLIENT_ID`, `ABDM_CLIENT_SECRET`, `ABDM_ENV=sandbox|production`. Register at <https://sandbox.abdm.gov.in>. Until then the ABHA card says linking is coming and accepts a photo.

**Family roles.** The first sign-in of a family is its admin; invitations create members or (admin only) caregivers. Caregivers can add readings, doses, visits and notes but cannot change profiles, cards, results, medicines, consents or delete the family — enforced on the server in `PUT /sync`. Family → Sign-ins & roles manages it; `GET /export` (3 a day) gives the whole record + documents as a ZIP (DPDP right to portability).

**Partner growth.** `/partner → Apply` files an application; **Admin → Applications** checks the licence, sets the location, approves (creates the store + owner sign-in) or declines. **Admin → Settlements** shows per-partner monthly totals, the platform fee (`PARTNER_FEE_PCT`, default 8), pay-outs and collections, with CSV.

**Lock-screen Medical ID.** Safety → Medical ID → *Lock-screen Medical ID* publishes `/m/<token>` (no sign-in; blood group, allergies, conditions, medicines, contacts, donor wish) with a QR to print or set as wallpaper; rotate or switch off any time; views are counted.

**Addresses.** Family → Addresses keeps home / work / other (with "use my current location"); checkout and home-collection bookings pick one, and the partner sees the full address, phone and a directions link.

**Devices tab (round 11).** Home → Devices shows where readings come from: the phone app (Health Connect on Android, Apple Health on iPhone — including Apple Watch ECG recordings, imported as strips), **Fitbit** linked from the web (`FITBIT_CLIENT_ID/SECRET`, callback `/api/v1/fitbit/callback`; register at dev.fitbit.com), Bluetooth devices in the browser, and **live ECG from a Polar H10/H9** (PMD service over Web Bluetooth; 30-second strips are saved as records with rate and RR variation, readable by the assistant). No watch maker exposes a live ECG to third-party apps; Google Fit's API is gone, which is why Fitbit is the one cloud connector.

**App downloads.** `GET /api/v1/app/android` and `/download/android` serve the APK that GitHub Actions publishes to the bucket (`releases/thehealthtracker.apk` + `android.json`) when the `S3_*` repository secrets exist; an admin can also upload one at `PUT /api/admin/app/android`. `PLAY_STORE_URL`, `APPSTORE_URL`, `TESTFLIGHT_URL` switch the site's buttons when the store listings exist. `mobile/ios` is the iOS project (HealthKit plugin, `ios.yml` builds on a macOS runner; signing needs an Apple Developer account and the `IOS_*` secrets).

**Loops that close on their own.** Paid plans end when `plan_until` passes (notice + Free plan) with one renewal nudge 5 days before; a video call nobody ended closes after 3 hours; partners get an email for every new order and visit request (`owner_email` + their sign-ins); applicants and new doctor sign-ins receive their one-time password by email; `ADMIN_ALERT_EMAIL` receives UPI claims and new applications; the admin dashboard shows a **Needs attention** row (payments to confirm, applications, doctors to verify, stores awaiting verification, visits unanswered > 24 h, orders not picked up > 4 h). All email goes through the existing transport (`RESEND_API_KEY` or `SMTP_*`); without one, nothing is sent and the admin pages carry the same information.

## Operations checklist

* `/admin` → **System** shows the clinical reviewer, which services are on (smart reading, documents, push) and the last 100 app errors reported by phones.
* `/admin` → **Dashboard** shows the last smart-reading failure with its exact error.
* Back up Postgres daily (Railway → Postgres → Backups) and test a restore once before launch.
