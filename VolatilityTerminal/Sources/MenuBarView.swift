import SwiftUI
import UserNotifications

struct MenuBarView: View {
    @ObservedObject var scanner: ScannerViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Text("Volatility Terminal")
                    .font(.headline)
                Spacer()
                if scanner.isScanning {
                    ProgressView()
                        .controlSize(.small)
                }
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 8)

            Divider()

            if let error = scanner.error {
                Label(error, systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.red)
                    .font(.caption)
                    .padding(12)
            }

            if scanner.signals.isEmpty && !scanner.isScanning {
                VStack(spacing: 8) {
                    Image(systemName: "chart.line.flattrend.xyaxis")
                        .font(.title)
                        .foregroundStyle(.secondary)
                    Text("No active signals")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(24)
            } else {
                ScrollView {
                    LazyVStack(spacing: 2) {
                        ForEach(scanner.signals) { signal in
                            SignalRow(signal: signal)
                        }
                    }
                }
                .frame(maxHeight: 320)
            }

            Divider()

            // Footer
            HStack {
                if let time = scanner.lastScanTime {
                    Text("Last scan: \(time.formatted(.relative(presentation: .named)))")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button("Scan Now") {
                    scanner.scan()
                }
                .buttonStyle(.borderless)
                .disabled(scanner.isScanning)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            Divider()

            HStack {
                SettingsLink {
                    Text("Settings...")
                }
                .buttonStyle(.borderless)
                Spacer()
                Button("Quit") {
                    NSApplication.shared.terminate(nil)
                }
                .buttonStyle(.borderless)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
        .frame(width: 360)
        .onAppear {
            scanner.startScanning()
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
        }
    }
}

struct SignalRow: View {
    let signal: Signal

    var body: some View {
        HStack(spacing: 12) {
            // Direction icon
            Image(systemName: signal.signalType.icon)
                .font(.title3)
                .foregroundStyle(signal.signalType.color == "green" ? .green : signal.signalType.color == "red" ? .red : .purple)
                .frame(width: 24)

            // Info
            VStack(alignment: .leading, spacing: 2) {
                HStack {
                    Text(signal.symbol)
                        .font(.system(.body, design: .monospaced, weight: .semibold))
                    Text(signal.signalType.rawValue.replacingOccurrences(of: "_", with: " "))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .textCase(.uppercase)
                }

                Text(signal.rationale)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer()

            // Price + strength
            VStack(alignment: .trailing, spacing: 2) {
                Text("$\(signal.currentPrice, specifier: "%.2f")")
                    .font(.system(.body, design: .monospaced))

                HStack(spacing: 2) {
                    ForEach(0..<signal.strength.dots, id: \.self) { _ in
                        Circle()
                            .fill(.primary)
                            .frame(width: 4, height: 4)
                    }
                    ForEach(0..<(4 - signal.strength.dots), id: \.self) { _ in
                        Circle()
                            .fill(.quaternary)
                            .frame(width: 4, height: 4)
                    }
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .contentShape(Rectangle())
    }
}
