# Urban Health — security incident and data-breach runbook

Who uses this: whoever is on call for urbanhealth.in. Keep it short enough to follow at 2 a.m.

## The clocks that start the moment we know

| Who | What | Deadline |
|---|---|---|
| CERT-In (incident@cert-in.org.in) | Report the incident (CERT-In Directions, 28 April 2022) | **6 hours** from noticing it |
| Data Protection Board of India | Report a personal-data breach (DPDP Act 2023, s.8(6); DPDP Rules) | Without delay; detailed report **within 72 hours** |
| Every affected person | Tell them what happened, what data, what we are doing, what they should do | Without delay |

Write down the time we first noticed. Every deadline counts from then.

## 1. First hour — contain

1. **Open an incident log** (a doc only the team can see). Write: time noticed, who noticed, what was seen. Add every action with its time from here on.
2. **Stop the leak, keep the evidence.** Prefer switching things off over deleting anything.
   - Suspicious account or token: disable the account (admin → users → disable). Sessions end at once.
   - A leaked secret (API key, `SECRET_KEY`, database password): rotate it in Secret Manager, then restart:
     `gcloud compute ssh urbanhealth --zone asia-south1-a --command "sudo systemctl restart urbanhealth"`.
     **Never rotate `DATA_KEY`** — health records are encrypted with it and would become unreadable. If `DATA_KEY` itself leaked, escalate to the founder before doing anything.
   - Attack in progress: block the address in Caddy, or take the site to maintenance by stopping the app.
3. **Preserve evidence.** Snapshot the VM disk and export the Cloud SQL database before changing anything else:
   `gcloud compute disks snapshot <disk> --zone asia-south1-a` and `gcloud sql export sql <instance> gs://<bucket>/incident-<date>.sql`.
   Save `journalctl -u urbanhealth --since "<time>"` and the `security_events` table for the period.

## 2. Within 6 hours — report to CERT-In

Email incident@cert-in.org.in with the incident reporting form (cert-in.org.in → Incident reporting). Include:
time noticed, systems affected, type of incident, what we have done so far, and a contact who answers the phone.
Partial information is fine; send it on time and update later.

## 3. Within 72 hours — understand and report the breach

1. **Scope.** Which people, which data (health records, contacts, identity details), which time window. Use:
   - `access_logs` — who opened which records;
   - `security_events` — sign-ins, wrong passwords, lockouts, contact changes (kept 400 days);
   - `error_events` and the system journal (kept 400 days).
2. **Report to the Data Protection Board**: nature and extent, timing, likely impact, what we did, what we will do.
3. **Tell affected people** in plain language (in-app notice + email/SMS), in their language. Include what they
   should do: change password, check Who opened my records, watch for calls pretending to be us.

## 4. Afterwards

- Fix the root cause; add a test that would have caught it.
- Write a one-page review: what happened, why, what we changed. No blame.
- Rotate any credential that might have been seen, except `DATA_KEY`.
- Update this runbook if any step was wrong or missing.

## Where things are

- App and logs: VM `urbanhealth` (asia-south1-a), `journalctl -u urbanhealth`
- Database: Cloud SQL (Mumbai). Files: Cloud Storage bucket (Mumbai), encrypted.
- Secrets: Secret Manager, project `central-weft-511003-c1`.
- Admin view of errors, security events and screen use: `GET /api/v2/ops/summary` (admins only).
