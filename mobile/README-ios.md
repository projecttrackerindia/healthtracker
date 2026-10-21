# iPhone build notes

## Lock-screen Health Card (Live Activity)
Files: `ios/App/App/HealthCardPlugin.swift` (Capacitor plugin `HealthCard`), `ios/App/App/HealthCardAttributes.swift` (shared model),
`ios/HealthCardWidget/HealthCardWidget.swift` + `Info.plist` (the widget extension). `Info.plist` of the app already has
`NSSupportsLiveActivities` and the `urbanhealth://` URL scheme.

One-time in Xcode (cannot be scripted reliably):
1. File → New → Target → **Widget Extension**, name `HealthCardWidget`, untick "Include Configuration Intent", tick **Include Live Activity**.
   Delete the generated Swift files and add the two files from `ios/HealthCardWidget/` to that target.
2. Select `HealthCardAttributes.swift` → File inspector → **Target Membership**: tick both `App` and `HealthCardWidget`.
3. Signing: both targets use the same team; bundle id of the widget must be `<app bundle id>.HealthCardWidget`.
4. Build. The app calls `HealthCard.show(...)` whenever the Health Card banner is on in Medical ID, and `hide()` when it is off.

Behaviour: the card sits on the Lock Screen (and the Dynamic Island on supported phones) until switched off. Tap → unlock → Medical ID;
the **SOS** button → unlock → the SOS sheet. Live Activities need iOS 16.2+ and the person's "Live Activities" setting on.
