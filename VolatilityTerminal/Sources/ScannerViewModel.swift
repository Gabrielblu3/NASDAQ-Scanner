import SwiftUI
import Foundation
import UserNotifications

@MainActor
final class ScannerViewModel: ObservableObject {
    @Published var signals: [Signal] = []
    @Published var isScanning = false
    @Published var lastScanTime: Date?
    @Published var error: String?

    // Settings
    @AppStorage("scanInterval") var scanIntervalMinutes = 60
    @AppStorage("alpacaApiKey") var alpacaApiKey = ""
    @AppStorage("alpacaSecretKey") var alpacaSecretKey = ""
    @AppStorage("useYFinanceOnly") var useYFinanceOnly = true

    private var scanTimer: Timer?

    var hasActiveSignals: Bool {
        !signals.isEmpty
    }

    var strongSignals: [Signal] {
        signals.filter { $0.strength == .strong || $0.strength == .veryStrong }
    }

    func startScanning() {
        scan()
        scanTimer = Timer.scheduledTimer(withTimeInterval: TimeInterval(scanIntervalMinutes * 60), repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.scan()
            }
        }
    }

    func stopScanning() {
        scanTimer?.invalidate()
        scanTimer = nil
    }

    func scan() {
        guard !isScanning else { return }
        isScanning = true
        error = nil

        Task {
            do {
                let results = try await ScannerService.shared.runScan(useYFinanceOnly: useYFinanceOnly)
                signals = results
                lastScanTime = Date()

                // Send notification for strong signals
                for signal in strongSignals {
                    await sendNotification(for: signal)
                }
            } catch {
                self.error = error.localizedDescription
            }
            isScanning = false
        }
    }

    private func sendNotification(for signal: Signal) async {
        let content = UNMutableNotificationContent()
        content.title = "\(signal.signalType.rawValue) \(signal.symbol)"
        content.body = "\(signal.strength.label) — $\(String(format: "%.2f", signal.currentPrice))"
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: "\(signal.symbol)-\(signal.signalType.rawValue)-\(Date().timeIntervalSince1970)",
            content: content,
            trigger: nil
        )

        try? await UNUserNotificationCenter.current().add(request)
    }
}
