# Watches, rings and Bluetooth devices → Urban Health

How a reading gets from a device on someone's body into their record, and which route each brand takes.

## The four roads

| Road | Covers | Needs | Status |
|---|---|---|---|
| **Health Connect** (Android) / **Apple Health** (iPhone) via the phone app's `HealthSync` plugin | Any watch whose own app shares with the phone's health store: Samsung Galaxy Watch, Pixel Watch, Garmin, Amazfit/Zepp, Mi/Xiaomi (Mi Fitness), Noise, boAt, Fire-Boltt, Huawei, Fossil, Withings, Oura, Fitbit | The Urban Health app installed; the watch's app set to share with Health Connect | **Live.** Steps, sleep, heart rate, weight, BP, sugar, SpO₂; Apple Watch ECG on iPhone |
| **Bluetooth LE, standard health profiles** (Web Bluetooth in Chrome; native plugin in the phone app) | BP monitors (Omron, Dr Trust, Beurer), pulse oximeters, weighing scales, thermometers, chest/wrist heart-rate straps; **Polar H10/H9 live ECG** | Nothing — tap "Read from a device" | **Live.** Round 19 added the native bridge so it works inside the Android and iOS apps, not only in Chrome |
| **Watch clouds** (OAuth): Fitbit (**closes 30 Oct 2026**, see below), **Withings**, **Oura** | People without the phone app, or devices that only sync to their maker's cloud. Withings also returns ScanWatch **ECG recordings with the AFib classification** | One developer app per service (keys below) | Code live; each switches on when its keys are set |
| Not available to any third party | Google Fit REST API (retired 2025), Garmin Health API and Samsung Health (partner programmes), Apple Watch outside the iPhone, proprietary watch Bluetooth (watches do not expose steps/ECG over GATT) | — | Use road 1 |

**ECG**: watches never stream ECG to another app. Apple Watch recordings arrive through Apple Health (iPhone app), Withings ScanWatch recordings through the Withings cloud, and live single-lead ECG comes from a Polar H10 chest strap over Bluetooth. Health Connect has no ECG record type.

## Fitbit → Google Health API (deadline 30 October 2026)

Google turns the Fitbit Web API off on **30 October 2026** (support ended 30 September). Its replacement is the **Google Health API** (developers.google.com/health): Google OAuth, scopes under `https://www.googleapis.com/auth/googlehealth…`, identity at `GET https://health.googleapis.com/v4/users/me/identity`, covering Fitbit and Pixel Watch data (parity with Health Connect promised for Q4 2026–Q1 2027). Every Google Health scope is **Restricted**, so the OAuth consent screen must pass Google's privacy-and-security review before anyone outside the project can link — budget a few weeks and the CASA security assessment. Users must re-consent (tokens do not carry over) and link Google Health to their Google Account first.

Practical position for Urban Health: Fitbit owners on Android are already covered by road 1 (the Fitbit app writes to Health Connect). `api/fitbit.py` keeps working until the 30th; the Devices tab says so. The Google Health port is a separate round once the consent-screen verification is under way.

## Developer keys (one-time, 10 minutes each)

| Service | Where | Callback URL | Secrets |
|---|---|---|---|
| Fitbit | https://dev.fitbit.com/apps → Register (Server application; "Personal" only reads your own account) | `https://<host>/api/v1/fitbit/callback` | `FITBIT_CLIENT_ID`, `FITBIT_CLIENT_SECRET` |
| Withings | https://developer.withings.com → Create app (Public cloud) | `https://<host>/api/v1/wear/withings/callback` | `WITHINGS_CLIENT_ID`, `WITHINGS_CLIENT_SECRET` |
| Oura | https://cloud.ouraring.com/oauth/applications | `https://<host>/api/v1/wear/oura/callback` | `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET` |

Put the values in `deploy/gcp/.env`, then `./setup.sh && ./deploy.sh`. Until the keys exist each card on the Devices tab says linking opens once developer access is approved; nothing else changes. Fitbit's and Withings' review for a public app takes a few days; Oura is immediate.

## Phone app (Bluetooth)

`@capacitor-community/bluetooth-le` is wrapped as `navigator.bluetooth` (layer 19) so the same reader and ECG code runs in the WebView. Android asks for Nearby devices (`BLUETOOTH_SCAN` neverForLocation + `BLUETOOTH_CONNECT`); iOS uses `NSBluetoothAlwaysUsageDescription`. The plugin's own device picker replaces Chrome's.

## API

* `GET  /api/v1/wear/status` → providers (enabled or not) and this family's links
* `POST /api/v1/wear/{withings|oura}/start?member=` → consent URL (503 while keys are missing)
* `GET  /api/v1/wear/{p}/callback` → stores sealed tokens, returns to `/app#wear=<p>:done`
* `POST /api/v1/wear/{p}/sync {member, days}` → readings in the HealthSync shape (`steps, sleep, heartRate, bloodPressure, spo2, weight, ecg`)
* `DELETE /api/v1/wear/{p}/{member}`

Demo keys are refused on every write, so the sample family can never link an account.
