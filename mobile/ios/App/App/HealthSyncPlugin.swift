// HealthKit → TheHealthTracker. Same contract as the Android HealthSyncPlugin (Health Connect), plus Apple Watch ECG.
//   available()            → { available: Bool }
//   requestPermissions()   → { granted: [String] }      (HealthKit never reveals which read permissions were denied; we return what we asked for)
//   read({ days })         → { steps:[{date,count}], sleep:[{date,hours}], heartRate:[{t,bpm,id}], weight:[{t,kg,id}], bloodPressure:[{t,sys,dia,id}],
//                              glucose:[{t,mgdl,id}], spo2:[{t,pct,id}], ecg:[{id,t,classification,avgHr,fs,durationS,samples:[µV]}] }
import Foundation
import Capacitor
import HealthKit

@objc(HealthSyncPlugin)
public class HealthSyncPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "HealthSyncPlugin"
    public let jsName = "HealthSync"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "available", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "requestPermissions", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "read", returnType: CAPPluginReturnPromise)
    ]
    private let store = HKHealthStore()

    private var readTypes: Set<HKObjectType> {
        var s: Set<HKObjectType> = []
        for id in [HKQuantityTypeIdentifier.stepCount, .heartRate, .bodyMass, .bloodPressureSystolic, .bloodPressureDiastolic, .bloodGlucose, .oxygenSaturation] {
            if let t = HKObjectType.quantityType(forIdentifier: id) { s.insert(t) }
        }
        if let sleep = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) { s.insert(sleep) }
        if #available(iOS 14.0, *) { s.insert(HKObjectType.electrocardiogramType()) }
        return s
    }

    @objc func available(_ call: CAPPluginCall) {
        call.resolve(["available": HKHealthStore.isHealthDataAvailable()])
    }

    @objc func requestPermissions(_ call: CAPPluginCall) {
        guard HKHealthStore.isHealthDataAvailable() else { call.resolve(["granted": []]); return }
        store.requestAuthorization(toShare: nil, read: readTypes) { ok, err in
            if let err = err { call.reject(err.localizedDescription); return }
            call.resolve(["granted": ok ? ["steps", "sleep", "heartRate", "weight", "bloodPressure", "glucose", "spo2", "ecg"] : []])
        }
    }

    @objc func read(_ call: CAPPluginCall) {
        let days = max(1, min(90, call.getInt("days") ?? 30))
        let end = Date(), start = Calendar.current.date(byAdding: .day, value: -days, to: end)!
        let pred = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
        let group = DispatchGroup()
        var out: [String: Any] = ["steps": [], "sleep": [], "heartRate": [], "weight": [], "bloodPressure": [], "glucose": [], "spo2": [], "ecg": []]
        let lock = NSLock()
        func put(_ k: String, _ v: [Any]) { lock.lock(); out[k] = v; lock.unlock() }
        let df = DateFormatter(); df.dateFormat = "yyyy-MM-dd"; df.timeZone = TimeZone.current
        let ms: (Date) -> Int = { Int($0.timeIntervalSince1970 * 1000) }

        // steps per day
        if let st = HKObjectType.quantityType(forIdentifier: .stepCount) {
            group.enter()
            var comps = DateComponents(); comps.day = 1
            let anchor = Calendar.current.startOfDay(for: start)
            let q = HKStatisticsCollectionQuery(quantityType: st, quantitySamplePredicate: pred, options: .cumulativeSum, anchorDate: anchor, intervalComponents: comps)
            q.initialResultsHandler = { _, coll, _ in
                var rows: [Any] = []
                coll?.enumerateStatistics(from: start, to: end) { s, _ in
                    if let n = s.sumQuantity()?.doubleValue(for: .count()), n > 0 { rows.append(["date": df.string(from: s.startDate), "count": Int(n)]) }
                }
                put("steps", rows); group.leave()
            }
            store.execute(q)
        }
        // sleep hours per night (asleep stages only)
        if let sl = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) {
            group.enter()
            let q = HKSampleQuery(sampleType: sl, predicate: pred, limit: HKObjectQueryNoLimit, sortDescriptors: nil) { _, samples, _ in
                var byDay: [String: Double] = [:]
                for s in (samples as? [HKCategorySample]) ?? [] {
                    var asleep = s.value != HKCategoryValueSleepAnalysis.inBed.rawValue && s.value != HKCategoryValueSleepAnalysis.awake.rawValue
                    if #available(iOS 16.0, *) { asleep = asleep && s.value != HKCategoryValueSleepAnalysis.awake.rawValue }
                    guard asleep else { continue }
                    let day = df.string(from: s.endDate)  // the night belongs to the morning it ends
                    byDay[day, default: 0] += s.endDate.timeIntervalSince(s.startDate) / 3600
                }
                put("sleep", byDay.map { ["date": $0.key, "hours": ($0.value * 10).rounded() / 10] }); group.leave()
            }
            store.execute(q)
        }
        func quantity(_ id: HKQuantityTypeIdentifier, _ key: String, _ unit: HKUnit, _ field: String, _ scale: Double = 1, limit: Int = 500) {
            guard let t = HKObjectType.quantityType(forIdentifier: id) else { return }
            group.enter()
            let q = HKSampleQuery(sampleType: t, predicate: pred, limit: limit, sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)]) { _, samples, _ in
                let rows: [Any] = ((samples as? [HKQuantitySample]) ?? []).map { ["t": ms($0.startDate), field: $0.quantity.doubleValue(for: unit) * scale, "id": $0.uuid.uuidString] }
                put(key, rows); group.leave()
            }
            store.execute(q)
        }
        quantity(.heartRate, "heartRate", HKUnit.count().unitDivided(by: .minute()), "bpm", limit: 2000)
        quantity(.bodyMass, "weight", .gramUnit(with: .kilo), "kg")
        quantity(.bloodGlucose, "glucose", HKUnit.gramUnit(with: .milli).unitDivided(by: .literUnit(with: .deci)), "mgdl")
        quantity(.oxygenSaturation, "spo2", .percent(), "pct", 100)
        // blood pressure comes as a correlation of two quantities
        if let bp = HKObjectType.correlationType(forIdentifier: .bloodPressure), let sysT = HKObjectType.quantityType(forIdentifier: .bloodPressureSystolic), let diaT = HKObjectType.quantityType(forIdentifier: .bloodPressureDiastolic) {
            group.enter()
            let q = HKSampleQuery(sampleType: bp, predicate: pred, limit: 500, sortDescriptors: nil) { _, samples, _ in
                var rows: [Any] = []
                for c in (samples as? [HKCorrelation]) ?? [] {
                    guard let s = (c.objects(for: sysT).first as? HKQuantitySample), let d = (c.objects(for: diaT).first as? HKQuantitySample) else { continue }
                    rows.append(["t": ms(c.startDate), "sys": s.quantity.doubleValue(for: .millimeterOfMercury()), "dia": d.quantity.doubleValue(for: .millimeterOfMercury()), "id": c.uuid.uuidString])
                }
                put("bloodPressure", rows); group.leave()
            }
            store.execute(q)
        }
        // Apple Watch ECG: classification + the waveform (downsampled 512 Hz → 128 Hz so a 30 s strip is ~3,800 points)
        if #available(iOS 14.0, *) {
            group.enter()
            let q = HKSampleQuery(sampleType: HKObjectType.electrocardiogramType(), predicate: pred, limit: 10, sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)]) { _, samples, _ in
                let ecgs = (samples as? [HKElectrocardiogram]) ?? []
                if ecgs.isEmpty { put("ecg", []); group.leave(); return }
                var rows: [Any] = []
                let inner = DispatchGroup()
                for e in ecgs {
                    inner.enter()
                    var volts: [Double] = []
                    var i = 0
                    let vq = HKElectrocardiogramQuery(e) { _, m, done, _ in
                        if let m = m, i % 4 == 0, let v = m.quantity(for: .appleWatchSimilarToLeadI)?.doubleValue(for: HKUnit.voltUnit(with: .micro)) { volts.append((v * 10).rounded() / 10) }
                        i += 1
                        if done {
                            let cls: String
                            switch e.classification {
                            case .sinusRhythm: cls = "sinus_rhythm"
                            case .atrialFibrillation: cls = "atrial_fibrillation"
                            case .inconclusiveLowHeartRate: cls = "inconclusive_low_hr"
                            case .inconclusiveHighHeartRate: cls = "inconclusive_high_hr"
                            case .inconclusivePoorReading: cls = "inconclusive_poor_reading"
                            case .inconclusiveOther: cls = "inconclusive"
                            default: cls = "not_set"
                            }
                            lock.lock()
                            rows.append(["id": e.uuid.uuidString, "t": ms(e.startDate), "classification": cls, "avgHr": e.averageHeartRate?.doubleValue(for: HKUnit.count().unitDivided(by: .minute())) ?? 0,
                                         "fs": Int(e.samplingFrequency?.doubleValue(for: .hertz()) ?? 512) / 4, "durationS": Int(e.endDate.timeIntervalSince(e.startDate)), "samples": volts])
                            lock.unlock()
                            inner.leave()
                        }
                    }
                    self.store.execute(vq)
                }
                inner.notify(queue: .global()) { put("ecg", rows); group.leave() }
            }
            store.execute(q)
        }
        group.notify(queue: .global()) { call.resolve(out) }
    }
}
