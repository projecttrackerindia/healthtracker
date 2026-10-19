# TheHealthTracker · Android

The live web app in a native shell (Capacitor), plus what a website cannot do on a phone:

* **Health Connect sync** — steps, sleep, heart rate, weight, blood pressure, glucose, SpO₂ from any watch or app that
  writes to Health Connect (Samsung Health, Google Fit, Noise, boAt, Fitbit, Garmin …). Read-only; the person grants each
  permission in the Health Connect screen. Plugin: `android/app/src/main/java/com/thehealthtracker/app/HealthSyncPlugin.kt`.
* **Native notifications** through Firebase Cloud Messaging once `android/app/google-services.json` is present
  (the server sends to FCM when `FCM_SERVICE_ACCOUNT_JSON` is set; web push keeps working for browsers).
* Camera, microphone and location permissions for report scans, video consults and nearby places.

The WebView loads `https://thehealthtracker.com/app`, so every web release reaches phones without a store update.
Set `APP_URL` at build time to point a build at staging.

## Build

GitHub Actions (`.github/workflows/android.yml`) builds a debug APK on every push that touches `mobile/`; download it
from the workflow run's artifacts and install it on a phone (allow "install from this source").

Locally, with Android Studio installed:

    cd mobile && npm ci && npx cap sync android && npx cap open android

## Play Store

1. Create an upload keystore once: `keytool -genkeypair -v -keystore release.keystore -alias tht -keyalg RSA -keysize 2048 -validity 10000`
2. Add repository secrets `ANDROID_KEYSTORE_BASE64` (base64 of the file), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`;
   the workflow then also produces a signed `.aab` for the Play Console.
3. Add `GOOGLE_SERVICES_JSON` (base64 of `google-services.json` from a Firebase project) for native push.
4. Health Connect apps need the "Health Connect" data-type declaration in the Play Console and a privacy policy link
   (https://thehealthtracker.com/privacy — the app already points Health Connect's rationale screen at it).
