import SwiftUI

@main
struct VolatilityTerminalApp: App {
    @StateObject private var scanner = ScannerViewModel()

    var body: some Scene {
        MenuBarExtra {
            MenuBarView(scanner: scanner)
        } label: {
            Label {
                Text("VT")
            } icon: {
                Image(systemName: scanner.hasActiveSignals ? "chart.line.uptrend.xyaxis" : "chart.line.flattrend.xyaxis")
                    .symbolRenderingMode(.hierarchical)
            }
        }
        .menuBarExtraStyle(.window)

        Settings {
            SettingsView(scanner: scanner)
        }
    }
}
