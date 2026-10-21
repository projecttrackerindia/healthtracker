# Google for Startups Cloud Program — application kit

Apply **before** you spend on Google Cloud: credits attach to the billing account, and some tiers only accept companies that have not yet spent much.

Programme names, tiers and amounts change. Treat the numbers below as what the programme has offered recently and confirm on the current page: https://cloud.google.com/startup (Google for Startups Cloud Program).

## What is usually offered

| Tier | Typical credits | Who it is for |
|---|---|---|
| Start | about US$2,000 (1 year) | very early companies, no investor needed |
| Scale | up to about US$100,000–200,000 (1–2 years) | companies backed by a VC, accelerator or incubator that is a Google partner |
| AI | up to about US$350,000 | AI-focused companies at seed/Series A |

Also usually included: Google Cloud Skills Boost training, a Google for Startups community, and some support credits.

## Fastest route in India

1. **Register the company** (Pvt Ltd / LLP) and get **DPIIT recognition** on startupindia.gov.in — free, and it unlocks several partner benefits.
2. **Get an investor or accelerator reference** if you can: the Scale tier is easiest through a partner such as T-Hub (Hyderabad), IIIT-H CIE, NASSCOM 10,000 Startups, Google for Startups Accelerator India, or a VC in Google's network. They submit a referral/organisation code you enter on the form.
3. Fill the form with the answers below.
4. Create the Google Cloud billing account (needed for credits to land), then link it when asked.

## Information to have ready

* Legal company name, CIN/LLPIN, incorporation date, registered address
* Website: https://urbanhealth.in (a public landing page is required — it exists)
* Company email on your own domain (not Gmail) and the founders' LinkedIn profiles
* Funding stage and investors (if any), team size
* Google Cloud billing account id and project id (after `deploy/gcp/setup.sh`)
* Estimated monthly cloud spend (see "Spend plan" below)
* Referring partner / referral code (if any)

## Ready-to-paste answers (edit the placeholders in [brackets])

**One-line description**
Urban Health is a family health record for India: reports, prescriptions, medicines, vaccines, pregnancy and emergency information for every family member in one secure place, with doctor video visits, lab and pharmacy ordering, and SOS.

**What problem do you solve?**
Indian families keep health records as paper, WhatsApp photos and scattered PDFs. Reports get lost, medicines are missed, and in an emergency nobody can find allergies or blood groups. Urban Health keeps one encrypted record per family member, reads uploaded reports and prescriptions into structured data, reminds people about medicines, vaccines and follow-up tests, and gives doctors a consented summary during video visits.

**Stage and traction**
[Live in production at urbanhealth.in since [month year]. Families: [number]. Partners onboarded: [number of labs / pharmacies / hospitals / doctors]. Paid plans: [yes/no].]

**Business model**
Family subscription plans; partner commissions on lab and pharmacy orders; consultation fees for verified doctors; a hospital-bag merchandise package.

**How will you use Google Cloud?**
Cloud Run for the application, Cloud SQL for PostgreSQL for family records (Mumbai region, for data residency under the DPDP Act), Cloud Storage for uploaded documents, Secret Manager and Cloud Logging/Monitoring for operations. We already use Google Maps Platform (nearby labs, blood-donor tracking, delivery addresses) and plan Firebase Cloud Messaging for push notifications and Google Cloud AI services for document understanding where it improves accuracy.

**Why Google Cloud?**
Mumbai and Delhi regions for Indian data residency, Cloud Run's simple operations for a small team, and our existing use of Maps, Firebase and Android (our Android app is built with Capacitor and distributed through Google Play).

**Security and compliance posture** (you can say this today; it is in the product)
Per-family encryption of stored records, optional two-step sign-in and passkeys, 30-minute idle sign-out, consent ledger, one-click data export and deletion (DPDP), no records shown when signed out, audit trail for admin actions. [Add: DPDP counsel review / ISO plans, if any.]

**Spend plan (credits runway)**
Year 1 estimate: about US$900–1,200 on the lean setup (Cloud Run, Cloud SQL, Cloud Storage), rising to about US$2,000–2,500 with high availability and a CDN once traffic grows.

## After approval

1. Credits appear under Billing → Credits within a few days.
2. Set a **budget alert** at 50/90/100% of expected spend, and an alert when credits drop below 20%.
3. Note the expiry date; plan the renewal or the move to paid billing a month earlier.
4. Ask the programme about the **Google for Startups Accelerator: India** and any AI credits once you have traction.

## Do not

* Do not put the card of a personal account on a company billing account.
* Do not claim traction, funding or compliance you do not have; programme managers check, and a rejected application can delay a later one.
