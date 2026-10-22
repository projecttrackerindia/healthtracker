# Launching urbanhealth.in

The app is live and correct at `https://tht-88456779070.asia-south1.run.app`. Everything below is about putting it
behind **urbanhealth.in** without losing passkeys, without Google indexing two copies of the site, and without the
domain being trivially spoofable in email.

Do the steps in the order they are written. Several of them depend on the one before, and two of them are hard to
undo once a crawler has seen them.

---

## 0. How the domain reaches the app — decided

**A Compute Engine VM, not Cloud Run.** The reasoning and the scripts are in
[`deploy/vm/README.md`](deploy/vm/README.md); the short version:

Cloud Run has no IP address, so a custom domain needs a domain mapping (not available in `asia-south1`, and
Preview-only) or a load balancer at roughly ₹1,500–2,000 a month. Meanwhile the Cloud Run service was already
pinned to `--min-instances 1 --max-instances 1 --no-cpu-throttling` — one always-on container that never
scales, because the video rooms and daily jobs live in the process. We were paying a premium for elasticity
we had switched off, on the one product that cannot take a domain.

So: one VM in `asia-south1`, Caddy for TLS, the same container image, and the domain becomes an `A` record.

A load balancer can be added later without rebuilding anything — the VM stays and the load balancer goes in
front of it. Worth doing when Cloud Armor, Cloud CDN or a second VM are actually wanted. The reserved address
and the pre-opened health-check firewall ranges are already in place for that day.

## 1. Create the mailboxes first

Nothing else should ship until these exist, because the privacy policy, the terms, `security.txt` and the partner
sign-up page all print addresses at `urbanhealth.in`, and an address that bounces is worse than no address:

`support@` · `partner@` · `privacy@` · `admin@` · `no-reply@` · `reply@` · `security@`

`security@` is new — `/.well-known/security.txt` only serves when `SECURITY_EMAIL` (or `SUPPORT_EMAIL`) is set, so
until the mailbox exists that file correctly 404s rather than publishing a dead contact.

---

## 2. Verify the domain in Google Search Console — before any DNS cutover

Add urbanhealth.in as a **Domain property** (not a URL prefix property — a domain property covers `www`, the apex
and every subdomain, and it is the one Cloud Run and Google Cloud accept as proof of ownership).

It asks for a `TXT` record at the apex. Add it in Hostinger, press verify, and **leave the record in place forever**
— removing it silently un-verifies the domain months later.

Do this first because the Google Cloud certificate step in the next section wants the domain already proven.

---

## 3. Point the DNS at the VM

Run `cd deploy/vm && ./provision.sh` first — it prints the reserved address and touches nothing that is
currently serving.

Then in Hostinger: **Domains → urbanhealth.in → DNS / Nameservers**.

| Type | Name | Value | TTL |
| --- | --- | --- | --- |
| `A` | `@` | the reserved IPv4 | 300 |
| `A` | `www` | the same IPv4 | 300 |

Delete Hostinger's parking records for `@` and `www` first, or they will fight these.

**Keep the TTL at 300 for the first week.** It makes the cutover quick and, more to the point, makes the
rollback quick: while Cloud Run is still running, moving these records back is the entire rollback procedure.
Raise the TTL once it has carried real traffic through a weekday.

Caddy requests the certificate on the first request after DNS resolves, so the site answers with a
certificate warning for a minute or two and then stops. That is Let's Encrypt working, not a fault.

## 4. CAA — say which authorities may issue a certificate for you

Without a `CAA` record, any public CA in the world may issue a certificate for urbanhealth.in. With one, only the
ones named may.

| Type | Name | Value |
| --- | --- | --- |
| `CAA` | `@` | `0 issue "pki.goog"` |
| `CAA` | `@` | `0 issue "letsencrypt.org"` |
| `CAA` | `@` | `0 iodef "mailto:security@urbanhealth.in"` |

Include `letsencrypt.org` even on the load-balancer route: it costs nothing and it keeps the Cloud Run path open
as a fallback. `iodef` is where a CA reports an attempted mis-issue.

---

## 5. Email authentication — the step that stops anyone sending as you

Without these three, a stranger can send "your lab report is ready" from `support@urbanhealth.in` and it will
land in inboxes. Getting them right is also what keeps the app's own mail out of spam.

* **SPF** — one `TXT` at `@`, listing *every* sender. The app sends through Resend and SMTP, so both belong in it,
  along with Workspace if the mailboxes are there. One record only; two SPF records is a permanent fail.
  `v=spf1 include:_spf.google.com include:amazonses.com -all` — replace the includes with the exact ones Resend
  and the mailbox provider give in their own dashboards, then end with `-all`, not `~all`.
* **DKIM** — Resend and Workspace each issue their own `CNAME` or `TXT` selector records. Add both sets.
* **DMARC** — one `TXT` at `_dmarc`:
  * launch with `v=DMARC1; p=none; rua=mailto:admin@urbanhealth.in` and read the reports for two weeks,
  * then `p=quarantine`,
  * then `p=reject` once the reports are clean.

  Going straight to `p=reject` before SPF and DKIM are verified will silently delete the app's own mail.

---

## 6. DNSSEC

Hostinger exposes a DNSSEC toggle for `.in` domains. Turn it on **after** the records above are settled and
verified working, because enabling it mid-change makes a mistake take hours to propagate rather than minutes.

---

## 7. Protection in front of the app

Already shipped, no action needed: HSTS, a content-security policy, `X-Content-Type-Options`, `Referrer-Policy`,
`Permissions-Policy`, `Cross-Origin-Opener-Policy`, `frame-ancestors 'none'`, and a two-layer rate limiter on
authentication that survives a container restart.

On the VM: Caddy is the only thing listening publicly and the app binds to `127.0.0.1`, so nothing but Caddy
can reach it even from inside the VPC. Debian's unattended security upgrades are on by default.

These two arrive with the load balancer, and are the main reason to add one:
* **Cloud Armor** — a rate-limit rule on `/api/v1/auth/*`, and the preconfigured OWASP rule sets in preview
  mode first, so a false positive does not lock out real families before the logs are read.
* **Cloud CDN** on `/s/*` and `/brand/*` only. Never on `/api/*`.

---

## 8. Environment variables at cutover

These live in `deploy/gcp/env.yaml`, which the VM reads on every service start (secrets come from Secret
Manager the same way). Most are already correct in the repo; the point of this table is that they only become
*true* once DNS resolves to the VM, so check them in the same change rather than before.

| Variable | Value | Why it matters |
| --- | --- | --- |
| `CANONICAL_HOST` | `urbanhealth.in` | Turns on the `www` → apex redirect, makes `robots.txt` serve the real rules, and puts `noindex` on every non-canonical host |
| `APP_ORIGIN` | `https://urbanhealth.in,https://www.urbanhealth.in` | Allowed passkey origins |
| `RP_ID` | `urbanhealth.in` | **Read the warning below first** |
| `SUPPORT_EMAIL` | `support@urbanhealth.in` | |
| `SECURITY_EMAIL` | `security@urbanhealth.in` | Starts serving `/.well-known/security.txt` |
| `GRIEVANCE_EMAIL` | `privacy@urbanhealth.in` | Named in the privacy policy; the DPDP Act expects a reachable grievance route |
| `LEGAL_ENTITY`, `LEGAL_ADDRESS` | the registered company name and address | Currently defaults, which are a guess |
| `APP_ENV` | `production` | |

### The passkey warning

A passkey is bound to the exact domain it was created on. Setting `RP_ID=urbanhealth.in` makes **every passkey
created on the old domain stop working** — the browser will not even offer them.

Right now that costs nothing, because there are no real users. It will never be this cheap again. Set it as part
of this cutover, not later.

The code already handles the in-between state: `RP_ID` applies only when the request arrives on that exact host,
so the Cloud Run URL keeps working with its own host as the relying party while DNS propagates.

---

## 9. Search Console, after the domain answers

1. **URL Inspection** on `https://urbanhealth.in/` → *Request indexing*.
2. **Sitemaps** → submit `sitemap.xml`. It is generated from the live routes, so it cannot drift from the site.
3. Check **Page indexing** after a few days. The Cloud Run URL should begin dropping out: it now answers
   `Disallow: /` in `robots.txt` *and* `X-Robots-Tag: noindex` on every response, which is the combination that
   actually removes a page rather than just stopping a re-crawl.
4. Add the same domain to **Bing Webmaster Tools**. It imports from Search Console in one click.

---

## 10. After the cutover — check, do not assume

```
curl -sI  https://urbanhealth.in/            | grep -i 'strict-transport\|x-robots'
curl -s   https://urbanhealth.in/robots.txt
curl -s   https://urbanhealth.in/sitemap.xml
curl -sI  https://www.urbanhealth.in/        | grep -i location      # expect 308 to the apex
curl -sI  https://tht-88456779070.asia-south1.run.app/ | grep -i x-robots   # expect noindex
curl -s   https://urbanhealth.in/api/health
```

Then, by eye: sign up with a passkey on the real domain, open the share link in a messaging app to confirm the
card renders, and run the landing page through PageSpeed Insights and the Rich Results Test.

---

## Still open

* The registered legal entity name and address for `LEGAL_ENTITY` / `LEGAL_ADDRESS`. The defaults are a
  guess, and the privacy policy prints them.
* The mailboxes in step 1. Nothing else here should ship before they exist.
* Workload Identity for GitHub Actions: run `deploy/gcp/wif.sh` once, then add the two secrets and two
  variables it prints. Until that is done, every merge builds and tests but cannot deploy.
