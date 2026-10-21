# Launching urbanhealth.in

The app is live and correct at `https://tht-88456779070.asia-south1.run.app`. Everything below is about putting it
behind **urbanhealth.in** without losing passkeys, without Google indexing two copies of the site, and without the
domain being trivially spoofable in email.

Do the steps in the order they are written. Several of them depend on the one before, and two of them are hard to
undo once a crawler has seen them.

---

## 0. The decision that comes first: how the domain reaches Cloud Run

**Cloud Run domain mapping does not work here.** It is not available in `asia-south1`, which is the region the
service runs in, and Google lists it as Preview and not recommended for production regardless. So the choice is
between two real options.

| | **Global external Application Load Balancer** | **Firebase Hosting in front of Cloud Run** |
| --- | --- | --- |
| Works with `asia-south1` | Yes | **Confirm before relying on this.** Hosting rewrites to Cloud Run were `us-central1`-only for a long time and the region list has moved; the docs page is too large to quote from reliably, so treat it as unverified. |
| Cost | A forwarding rule is roughly **₹1,500–2,000/month** before traffic | Free tier covers a launch |
| TLS | Google-managed certificate, renews itself | Included |
| Apex domain (`urbanhealth.in` with no `www`) | Static anycast IP → a normal `A` record. This matters: DNS does not allow a `CNAME` at the apex | Handled by Firebase's own A records |
| WAF | **Cloud Armor** attaches directly — rate limiting, geo rules, OWASP rules | None |
| Contract | Covered by the Google Cloud Terms of Service | **Not** covered by Google Cloud ToS — worth a thought for a health product under the DPDP Act |

**Recommendation: the load balancer.** For a health app holding family medical records, Cloud Armor and being
inside the Google Cloud contract are worth ₹2,000 a month. Firebase Hosting is the right answer if the priority is
getting live at zero marginal cost and the region question checks out — but then Cloud Armor is not available, and
the WAF layer in step 7 has to come from somewhere else.

Everything from step 1 onward is the same either way, except the DNS values in step 3.

---

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

## 3. Point the DNS at Google

In Hostinger: **Domains → urbanhealth.in → DNS / Nameservers**.

With the load balancer, after reserving a global static IP and attaching the serverless NEG:

| Type | Name | Value | Notes |
| --- | --- | --- | --- |
| `A` | `@` | the reserved IPv4 | the apex; a `CNAME` is not legal here |
| `AAAA` | `@` | the reserved IPv6 | add it — IPv6-only mobile networks are common in India |
| `A` | `www` | the same IPv4 | the app 308-redirects `www` → apex itself |
| `AAAA` | `www` | the same IPv6 | |

Delete any Hostinger parking or redirect records for `@` and `www` first, or they will fight these.

The Google-managed certificate only starts issuing **after** the records resolve, and it can take 15–60 minutes.
Until it finishes the site answers with a certificate error; that is expected, not a fault.

---

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

Add at the edge, if the load balancer route is taken:
* **Cloud Armor** — a rate-limit rule on `/api/v1/auth/*`, and the preconfigured OWASP rule sets in preview mode
  first so a false positive does not lock out real families before the logs are read.
* **Cloud CDN** on `/s/*` and `/brand/*` only. Never on `/api/*`.

---

## 8. Environment variables at cutover

Set these on the Cloud Run service in the same change, not before — several of them break the site while the
domain is still resolving elsewhere.

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

* **`site/img/app-desktop.webp`** — the hero screenshot on the marketing page still shows the old name in its
  sidebar. It needs re-shooting against seeded demo data; the guest route renders the sign-in card on an empty
  database, so it could not be recaptured. This is the first thing a visitor sees, so it should not ship.
* Whether Firebase Hosting can rewrite to `asia-south1`, if the cheap route is preferred over the load balancer.
* The registered legal entity name and address for `LEGAL_ENTITY` / `LEGAL_ADDRESS`.
