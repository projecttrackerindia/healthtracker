// Lock-screen Health Card for iPhone: a Live Activity (iOS 16.2+) that stays on the Lock Screen / Dynamic Island until the
// family switches it off in Medical ID. Tapping it (or its SOS button) opens the app through thehealthtracker://… links.
//   show({ name, memberId, blood, allergies, conditions }) → { ok }
//   hide()                                                 → { ok }
//   status()                                               → { supported, active }
import Foundation
import Capacitor
#if canImport(ActivityKit)
import ActivityKit
#endif

@objc(HealthCardPlugin)
public class HealthCardPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "HealthCardPlugin"
    public let jsName = "HealthCard"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "show", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "hide", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "status", returnType: CAPPluginReturnPromise)
    ]

    @objc func status(_ call: CAPPluginCall) {
        if #available(iOS 16.2, *) {
            let active = !Activity<HealthCardAttributes>.activities.isEmpty
            call.resolve(["supported": ActivityAuthorizationInfo().areActivitiesEnabled, "active": active])
        } else {
            call.resolve(["supported": false, "active": false])
        }
    }

    @objc func show(_ call: CAPPluginCall) {
        guard #available(iOS 16.2, *) else { call.resolve(["ok": false, "reason": "iOS 16.2 or newer"]); return }
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { call.resolve(["ok": false, "reason": "Live Activities are off in Settings"]); return }
        let state = HealthCardAttributes.ContentState(
            blood: call.getString("blood") ?? "", allergies: call.getString("allergies") ?? "",
            conditions: call.getString("conditions") ?? "", updated: Date())
        Task {
            // one card at a time: update the existing activity, or start one
            if let existing = Activity<HealthCardAttributes>.activities.first {
                await existing.update(ActivityContent(state: state, staleDate: nil))
                call.resolve(["ok": true])
                return
            }
            let attrs = HealthCardAttributes(name: call.getString("name") ?? "", memberId: call.getString("memberId") ?? "")
            do {
                _ = try Activity.request(attributes: attrs, content: ActivityContent(state: state, staleDate: nil), pushType: nil)
                call.resolve(["ok": true])
            } catch {
                call.resolve(["ok": false, "reason": error.localizedDescription])
            }
        }
    }

    @objc func hide(_ call: CAPPluginCall) {
        guard #available(iOS 16.2, *) else { call.resolve(["ok": true]); return }
        Task {
            for a in Activity<HealthCardAttributes>.activities { await a.end(nil, dismissalPolicy: .immediate) }
            call.resolve(["ok": true])
        }
    }
}
