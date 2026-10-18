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
| `DOKKO_AI_MODEL` | no | Default `claude-sonnet-5-5`. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | no | Live subscription payments (UPI, cards, net banking). Use test keys first. Without them billing is demo-only. |
| `RP_ID`, `APP_ORIGIN` | yes for passkeys | Domain the passkeys belong to, and the exact https address of the site. If empty they are taken from the request. |
| `RESEND_API_KEY` + `MAIL_FROM` | one email option | Sends sign-up, sign-in and reset codes by email. Verify the sending domain in Resend (DNS records). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` | other email option | Any SMTP service (Zoho, Gmail app password, Amazon SES). Port 465 uses SSL, others STARTTLS. |
| `MSG91_AUTH_KEY`, `MSG91_TEMPLATE_ID` | SMS option (India) | MSG91 OTP API. Requires a DLT-registered sender and OTP template with `##OTP##`. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` | SMS option | Twilio SMS (international; India needs DLT too). |
| `PWNED_CHECK` | no | `1` (default) rejects passwords found in known breaches using Have I Been Pwned's k-anonymity API. |
| `OTP_DEMO` | no | `1` shows codes on screen instead of sending them. Testing only. |
| `DOKKO_REGION` | no | `IN`. |
| `LEGAL_ENTITY`, `LEGAL_ADDRESS` | yes before launch | Shown on /privacy and /terms (registered name and address of the business). Defaults: `TheHealthTracker`, `Hyderabad, Telangana, India`. |
| `GRIEVANCE_NAME`, `GRIEVANCE_EMAIL` | yes before launch | Grievance Officer shown in the privacy policy (DPDP Act). `GRIEVANCE_EMAIL` falls back to `SUPPORT_EMAIL`, then `ADMIN_EMAIL`. |
| `SUPPORT_EMAIL` | recommended | Contact address on /terms. |
| `POLICY_UPDATED` | no | Date shown on the policy pages, e.g. `18 October 2026`. |
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
