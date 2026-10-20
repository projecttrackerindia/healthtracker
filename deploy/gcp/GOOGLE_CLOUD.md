# Running TheHealthTracker on Google Cloud (Mumbai)

Nothing here touches production. Railway keeps serving until you do the cut-over in section 6.

**What runs where**

| Today (Railway) | Google Cloud | Notes |
|---|---|---|
| Container (Nixpacks) | **Cloud Run**, `asia-south1` | `Dockerfile`; 1 instance, CPU always on |
| Postgres | **Cloud SQL for PostgreSQL 16**, `asia-south1` | daily backups, point-in-time recovery, no public IP (socket) |
| Bucket (S3) | **Cloud Storage**, `asia-south1` | same S3 code via Google's S3 interop (HMAC key) |
| Variables | **Secret Manager** + `env.yaml` | names unchanged |
| Deploy on merge | **GitHub Actions** → keyless login | `.github/workflows/gcp-deploy.yml` |
| Maps, push | Google Maps key, Firebase (FCM) | unchanged; both are Google already |

Why one instance: video-call rooms and the daily jobs run inside the app process. Two instances could put a doctor and patient in different processes. Cloud Run is therefore pinned to `min=max=1` with CPU always on and session affinity. Going to several instances later needs Redis for the rooms (Memorystore) and Cloud Scheduler for the jobs; the app does not need that yet.

---

## 0. Before you start (one-time, ~20 minutes)

1. A Google account that will own billing (use a company address, not a personal one you may lose).
2. **Install**: `gcloud` (https://cloud.google.com/sdk/docs/install), and for the data copy `postgresql-client` 16, `rclone`, and `cloud-sql-proxy`.
3. `gcloud auth login` and `gcloud auth application-default login`.
4. A billing account: console.cloud.google.com → Billing → create one (needs a card; the free trial gives about US$300 for 90 days). Note its id: `gcloud billing accounts list`.
5. Apply for the startup credits (section 9) **before** you spend anything — credits apply to the billing account, so create the billing account first.

## 1. Create everything

```bash
cd deploy/gcp
cp .env.example .env            # fill in values from Railway:  railway variables --kv
export BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX
export PROJECT_ID=thehealthtracker-prod      # must be unique worldwide; pick another if taken
./setup.sh
```

`DATA_KEY` and `SECRET_KEY` **must be copied exactly from Railway**. `DATA_KEY` decrypts every family's stored record; a different key makes all existing records unreadable. `SECRET_KEY` keeps current sign-ins valid. `setup.sh` is safe to re-run.

Edit `env.yaml` if your bucket name differs from `<project>-documents`.

At the end the script prints the two GitHub secrets and two variables to add (Settings → Secrets and variables → Actions).

## 2. First deploy (to a `*.run.app` address)

```bash
./deploy.sh
```

It builds with Cloud Build, deploys, and calls `/healthz`. Open the printed URL: the app, `/admin`, and `/partner` all work there. Passkeys and sign-in work on that address too (the app uses whichever host serves it).

The new database is empty at this point. Sign up a test account to prove it works, then continue.

## 3. Rehearse the data copy (safe, repeatable)

```bash
export RAILWAY_DATABASE_URL='postgresql://…'     # Railway → Postgres → Connect → public URL
export RAILWAY_S3_ENDPOINT=… RAILWAY_S3_BUCKET=… RAILWAY_S3_ACCESS_KEY=… RAILWAY_S3_SECRET_KEY=…
./migrate_data.sh
```

It dumps Railway Postgres, restores into Cloud SQL, copies the documents, and prints row/object counts for both sides. It only **reads** from Railway. Run it as often as you like; each run replaces the previous rehearsal.

Then test on the `*.run.app` URL with a real account: sign in, open a record with a document, run a smart reading, start a test video call.

## 4. Connect Google services

* **Maps**: `GOOGLE_MAPS_KEY` is a browser key; add your new domain to its allowed referrers (Cloud Console → APIs & Services → Credentials). No other change.
* **Push (FCM)**: create a Firebase project (console.firebase.google.com) on the same Google project, download the service-account JSON, add it as the `FCM_SERVICE_ACCOUNT_JSON` secret (add the name to `secrets.txt`).
* **DigiLocker / Razorpay / WhatsApp / MSG91** callbacks point at the domain, not the host, so they do not change once the domain moves.

## 5. Domain

Attach `thehealthtracker.com` to Cloud Run:

```bash
gcloud beta run domain-mappings create --service tht --domain thehealthtracker.com --region asia-south1
gcloud beta run domain-mappings create --service tht --domain www.thehealthtracker.com --region asia-south1
gcloud beta run domain-mappings describe --domain thehealthtracker.com --region asia-south1   # shows the DNS records to add
```

Add the records at your DNS provider (the certificate is issued automatically, usually within 15–60 minutes). If the command says domain mappings are not available in the region, use a global external Application Load Balancer with a serverless NEG instead (about US$18/month extra); the console wizard "Cloud Run → Add custom domain" covers both.

Keep `RP_ID=thehealthtracker.com` (already in `env.yaml`). Passkeys made on the Railway address will not work on the custom domain — that is how passkeys are bound — so families create them again once, and the app offers it after sign-in.

## 6. Cut-over (about 15–20 minutes of downtime)

Pick a quiet hour (early morning IST).

1. Announce nothing; just do it quickly. In Railway: scale the service to **0** (Settings → Deploy → set replicas to 0, or pause the deployment) so no new writes happen.
2. `./migrate_data.sh` once more (this is the real copy).
3. `./deploy.sh` (restarts Cloud Run on the fresh data).
4. Check: sign in, a record, a document, `/admin` numbers match Railway's last numbers.
5. Switch DNS to Cloud Run (section 5). Until DNS propagates, people on the old address see Railway's "paused" page; this is the downtime.
6. Watch `gcloud run services logs read tht --region asia-south1 --limit 100` for errors for 30 minutes.

**Rollback** (any time in the first week): point DNS back to Railway and scale it back to 1. Because Railway was only paused, its database is exactly as it was before the cut-over. Anything written on Google after the cut-over would need to be re-copied back; for a short window that is usually none or a handful of rows, so decide quickly.

Keep Railway (paused, scaled to 0 costs almost nothing) for **7 days**, then delete it.

## 7. Day-to-day

* **Deploys**: GitHub → Actions → "Deploy to Google Cloud Run" → Run workflow. After the cut-over, add `push: branches: [main]` to the workflow so merges deploy on their own.
* **Logs**: `gcloud run services logs read tht --region asia-south1 --limit 100`, or Cloud Run → Logs.
* **Database**: Cloud SQL → backups are daily with 14 kept; point-in-time recovery lets you restore to any minute in the last 7 days. Do one restore test into a *new* instance before launch.
* **Alerts** (Monitoring → Alerting): Cloud Run 5xx rate > 2% for 5 min; instance count = 0; Cloud SQL CPU > 80% for 15 min; Cloud SQL disk > 80%. Notify your email.
* **Budget**: Billing → Budgets & alerts → set a monthly budget with alerts at 50/90/100%.
* **Secrets**: change a value in `.env`, run `./setup.sh` (updates the secret), then `./deploy.sh`.

## 8. Growing later

* **High availability**: `gcloud sql instances patch tht-pg --tier=db-custom-1-3840 --availability-type=REGIONAL` (about US$90–120/month).
* **More than one app instance**: first move video-call signalling to Redis (Memorystore) and the daily jobs to Cloud Scheduler. Then raise `--max-instances`.
* **Cheaper compute**: once the daily jobs move to Cloud Scheduler, Cloud Run can drop `--no-cpu-throttling` and `--min-instances 1` (CPU is then billed only while serving requests, roughly 40–60% less at low traffic) — but a video call would then need a warm instance, so keep one instance warm.
* **Cloud Armor + CDN**: put a global load balancer in front, add Cloud CDN for `/web` and `/site` assets and a WAF policy.

## Cost (approximate, US$/month, Mumbai)

| | Lean (this setup) | With HA |
|---|---|---|
| Cloud Run (1 vCPU / 1 GiB, CPU always on — needed for the in-process jobs and calls) | 45–55 | 45–55 |
| Cloud SQL Postgres | 25–35 (g1-small, 20 GB) | 90–120 |
| Cloud Storage (50 GB) | ~1–2 | ~5 |
| Secret Manager, logging, registry | 3–8 | 8–15 |
| Load balancer (only if needed for the domain) | 0 | ~18 |
| **Total** | **≈ 75–100 (₹6.5–8.5k)** | **≈ 170–220** |

Estimates from list prices; use the Google Cloud Pricing Calculator for a quote. Credits (section 9) cover this for the first one to two years.

## 9. Startup credits

See `docs/google-startup-application.md` for the checklist and ready-to-paste answers.
