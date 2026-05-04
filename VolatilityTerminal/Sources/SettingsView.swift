import SwiftUI

struct SettingsView: View {
    @ObservedObject var scanner: ScannerViewModel

    var body: some View {
        Form {
            Section("Scan Settings") {
                Picker("Scan Interval", selection: $scanner.scanIntervalMinutes) {
                    Text("15 min").tag(15)
                    Text("30 min").tag(30)
                    Text("1 hour").tag(60)
                    Text("2 hours").tag(120)
                }

                Toggle("Use Yahoo Finance only (no API key needed)", isOn: $scanner.useYFinanceOnly)
            }

            if !scanner.useYFinanceOnly {
                Section("Alpaca API") {
                    TextField("API Key", text: $scanner.alpacaApiKey)
                    SecureField("Secret Key", text: $scanner.alpacaSecretKey)
                }
            }

            Section {
                LabeledContent("Signals", value: "\(scanner.signals.count)")
                if let time = scanner.lastScanTime {
                    LabeledContent("Last Scan", value: time.formatted())
                }
            } header: {
                Text("Status")
            }
        }
        .formStyle(.grouped)
        .frame(width: 420, height: 300)
    }
}
