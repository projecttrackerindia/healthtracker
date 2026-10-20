import UIKit
import Capacitor

// Registers the in-app HealthKit plugin with the Capacitor bridge (Capacitor 6 "local plugin" pattern).
class MainViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(HealthSyncPlugin())
        bridge?.registerPluginInstance(HealthCardPlugin())
    }
}
