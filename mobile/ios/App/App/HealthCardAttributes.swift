// Shared by the app and the HealthCardWidget extension (add this file to BOTH targets in Xcode).
import ActivityKit
import Foundation

@available(iOS 16.2, *)
struct HealthCardAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var blood: String        // "O+" or ""
        var allergies: String    // "Penicillin, Sulfa" or ""
        var conditions: String   // "Hypertension" or ""
        var updated: Date
    }
    var name: String             // the person on the card
    var memberId: String
}
