# Urban Health for Android

Two apps from one project, both Trusted Web Activities (the live web app running full-screen in Chrome):

| Flavour  | Package                  | Opens                              | APK on the website                    |
|----------|--------------------------|------------------------------------|---------------------------------------|
| user     | `in.urbanhealth.app`     | https://urbanhealth.in/app         | /download/urbanhealth.apk             |
| partner  | `in.urbanhealth.partner` | https://urbanhealth.in/partner     | /download/urbanhealth-partner.apk     |

Why Chrome and not a WebView: Google sign-in is blocked inside WebViews. In Chrome, sign-in, web push notifications
(shown as the app's own notifications), camera and location all work exactly as on the website, and every web
release reaches the apps without a new APK.

The browser bar is hidden only when `https://urbanhealth.in/.well-known/assetlinks.json` lists the package and the
signing key's SHA-256 (served by `server.py`, `ANDROID_CERT_SHA256` overrides it, comma-separated). If the bar shows,
that file is the first thing to check.

(`mobile/` holds an older Capacitor WebView shell with a Health Connect plugin; it is not what the website offers.)

## Build

Needs JDK 17+, Gradle 8.13+, Android SDK platform 36.

    cd android
    echo "sdk.dir=$ANDROID_HOME" > local.properties
    cp /safe/place/keystore.properties .      # never committed
    gradle assembleRelease
    cp app/build/outputs/apk/user/release/app-user-release.apk       ../site/downloads/urbanhealth.apk
    cp app/build/outputs/apk/partner/release/app-partner-release.apk ../site/downloads/urbanhealth-partner.apk

Raise `versionCode` (and `versionName`) in `app/build.gradle` for every new APK, or phones refuse the update.

## The signing key

`urbanhealth-release.jks` plus `keystore.properties` (passwords). Kept outside git. **Every update must be signed with
the same key**: a different key means phones refuse the update and the browser bar reappears. Keep two copies somewhere
safe (a password manager and Secret Manager).

    keytool -list -v -keystore urbanhealth-release.jks     # shows the SHA-256 for assetlinks.json

## Play Store later

Upload an `.aab` (`gradle bundleRelease`). With Play App Signing, Google re-signs the app, so add the "App signing key
certificate" SHA-256 from the Play Console to `ANDROID_CERT_SHA256` next to this one.
