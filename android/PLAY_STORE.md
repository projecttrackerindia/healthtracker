# Publishing on Google Play

Both apps (Urban Health for families, Urban Health Partner for labs and pharmacies) are Trusted Web Activities built by
`.github/workflows/android-twa.yml`. Play needs an **Android App Bundle (.aab)**; the workflow builds both bundles alongside the APKs (artifact `urbanhealth-android-apks`).

## One-time setup (owner, ~1 hour)
1. Google Play Console account as an **organisation** (company PAN, D-U-N-S number). Health apps from individual
   accounts get more scrutiny and are asked for 20 testers × 14 days of closed testing first.
2. Create both apps. Package names must match `android/app/build.gradle` (`in.urbanhealth.app`, `in.urbanhealth.partner`).
3. **Play App Signing**: upload the existing upload key's certificate (the keystore in the GitHub secret). Add Play's
   app-signing SHA-256 to `ANDROID_CERT_SHA256` (comma-separated, read by server.py for `/.well-known/assetlinks.json`) next to ours, or the app opens with a
   browser bar.
4. Fill in the sections below, upload the .aab to **Internal testing**, then **Closed testing**, then **Production**.

## Store listing — Urban Health
- **Short description (80):** Your family's reports, medicines and home tests, explained simply and kept safe.
- **Full description:**
  Urban Health keeps your family's health in one place. Add a lab report or prescription with a photo and see the
  values explained in plain words. Get reminders for medicines and checkups, book home blood tests from accredited labs,
  order medicines from registered pharmacies, and keep a Medical ID with blood group, allergies and emergency contacts
  ready for an emergency.
  • Reports read and explained (with your permission), shown on a 3D body
  • Medicine reminders for each family member, in English, Tamil or Telugu
  • Home sample collection and medicine delivery from verified partners
  • SOS with your location to your emergency contacts
  • Your data stays in India, encrypted, and you can download or delete it any time
  Urban Health does not diagnose or treat. Always follow your doctor's advice.
- **Category:** Medical. **Contact:** support@urbanhealth.in. **Privacy policy:** https://urbanhealth.in/privacy

## Health apps declaration
- Features: medical records / personal health records; medication reminders; lab test booking; e-pharmacy (orders are
  dispensed by licensed pharmacies against a prescription checked by a registered pharmacist).
- Not a medical device; no diagnosis. Schedule X and NDPS medicines are never sold.

## Data safety (answers match what the app does today)
| Data | Collected | Shared | Why | Optional |
|---|---|---|---|---|
| Name, email, phone | Yes | With the lab/pharmacy fulfilling an order | Account, orders | No |
| Health info (records, readings, medicines) | Yes | With the lab/pharmacy on that order only; never sold | App functionality | Yes |
| Photos and files (reports, prescriptions) | Yes | Pharmacist sees a prescription you attach to an order | App functionality | Yes |
| Precise location | Yes | Emergency contacts during SOS; technician/rider on the day of a visit | SOS, address pin | Yes |
| Payment info | No — Razorpay collects it inside its own checkout | — | — | — |
| App activity (screens opened, counts only) | Yes | No | Analytics, no person attached | No |
- Encrypted in transit: **Yes**. Users can request deletion: **Yes** (Settings → Privacy → Delete, and
  https://urbanhealth.in/privacy for people without the app). Data is not used for advertising.
- AI reading is a processor acting on our behalf (not "sharing" under Play's definition); it runs only after the person
  allows "AI reads my reports" and is never used to train models.

## Content rating
IARC questionnaire: no violence, no user-to-user chat with strangers (partner messages are order-scoped), no gambling.
Expected rating: **Everyone / 3+**. Target audience: 18+ (accounts are for adults; children are added by a guardian).

## Partner app
Same steps; listing says it is for registered labs, pharmacies and their staff, sign-in by invitation only. Data safety:
staff name, phone, email, registration certificate, location during home visits (shown to the family on that order).
