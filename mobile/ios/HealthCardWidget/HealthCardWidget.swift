// Lock Screen / Dynamic Island view of the Health Card. Widget extension target "HealthCardWidget" (see README-ios.md).
import ActivityKit
import SwiftUI
import WidgetKit

@available(iOS 16.2, *)
struct HealthCardWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: HealthCardAttributes.self) { ctx in
            // Lock Screen banner
            HStack(spacing: 12) {
                Text(ctx.state.blood.isEmpty ? "ID" : ctx.state.blood)
                    .font(.system(size: 17, weight: .heavy, design: .rounded))
                    .foregroundColor(Color(red: 0.90, green: 0.28, blue: 0.30))
                    .frame(minWidth: 46, minHeight: 34)
                    .background(Color(red: 0.90, green: 0.28, blue: 0.30).opacity(0.16))
                    .cornerRadius(10)
                VStack(alignment: .leading, spacing: 2) {
                    Text(ctx.attributes.name).font(.system(size: 15, weight: .bold)).lineLimit(1)
                    Text(line(ctx.state)).font(.system(size: 12.5)).foregroundColor(.secondary).lineLimit(1)
                }
                Spacer()
                Link(destination: URL(string: "thehealthtracker://sos")!) {
                    Text("SOS").font(.system(size: 12, weight: .heavy)).tracking(1.5).foregroundColor(.white)
                        .padding(.horizontal, 14).frame(height: 34)
                        .background(Color(red: 0.90, green: 0.28, blue: 0.30)).cornerRadius(17)
                }
            }
            .padding(14)
            .activityBackgroundTint(Color(red: 0.03, green: 0.03, blue: 0.05))
            .widgetURL(URL(string: "thehealthtracker://medical-id"))
        } dynamicIsland: { ctx in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) { Text(ctx.state.blood.isEmpty ? "ID" : ctx.state.blood).font(.system(size: 16, weight: .heavy, design: .rounded)) }
                DynamicIslandExpandedRegion(.center) { Text(ctx.attributes.name).font(.system(size: 14, weight: .bold)).lineLimit(1) }
                DynamicIslandExpandedRegion(.trailing) {
                    Link(destination: URL(string: "thehealthtracker://sos")!) { Text("SOS").font(.system(size: 12, weight: .heavy)).foregroundColor(.white).padding(.horizontal, 10).frame(height: 28).background(Color.red).cornerRadius(14) }
                }
                DynamicIslandExpandedRegion(.bottom) { Text(line(ctx.state)).font(.system(size: 12)).foregroundColor(.secondary).lineLimit(1) }
            } compactLeading: {
                Text(ctx.state.blood.isEmpty ? "ID" : ctx.state.blood).font(.system(size: 12, weight: .heavy, design: .rounded)).foregroundColor(.red)
            } compactTrailing: {
                Text("SOS").font(.system(size: 11, weight: .heavy)).foregroundColor(.red)
            } minimal: {
                Text("+").font(.system(size: 14, weight: .heavy)).foregroundColor(.red)
            }
            .widgetURL(URL(string: "thehealthtracker://medical-id"))
        }
    }

    private func line(_ s: HealthCardAttributes.ContentState) -> String {
        var parts: [String] = []
        parts.append(s.allergies.isEmpty ? "No allergies on record" : "Allergic: \(s.allergies)")
        if !s.conditions.isEmpty { parts.append(s.conditions) }
        return parts.joined(separator: " · ")
    }
}

@main
struct HealthCardWidgetBundle: WidgetBundle {
    var body: some Widget {
        if #available(iOS 16.2, *) { HealthCardWidget() }
    }
}
