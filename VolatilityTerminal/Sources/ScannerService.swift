import Foundation

/// Bridges the Python scanner backend via a local subprocess call.
/// Runs the scanner in a background thread to avoid blocking the UI.
actor ScannerService {
    static let shared = ScannerService()

    private let scannerPath: String

    init() {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        scannerPath = "\(home)/Cursor Projects/NASDAQ-Scanner"
    }

    func runScan(useYFinanceOnly: Bool = true) async throws -> [Signal] {
        let scannerPath = self.scannerPath

        return try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                do {
                    let process = Process()
                    let stdout = Pipe()
                    let stderr = Pipe()

                    process.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/uv")
                    process.arguments = [
                        "run", "--project", scannerPath, "python", "-c",
                        """
                        import json, sys
                        sys.stderr = open('/dev/null', 'w')
                        from nasdaq_scanner.main import run_scan
                        signals = run_scan(send_alerts=False, use_yfinance_only=\(useYFinanceOnly ? "True" : "False"))
                        print("__JSON_START__")
                        print(json.dumps(signals))
                        print("__JSON_END__")
                        """
                    ]
                    process.standardOutput = stdout
                    process.standardError = stderr
                    process.currentDirectoryURL = URL(fileURLWithPath: scannerPath)
                    process.environment = [
                        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
                        "HOME": FileManager.default.homeDirectoryForCurrentUser.path,
                    ]

                    try process.run()
                    process.waitUntilExit()

                    let data = stdout.fileHandleForReading.readDataToEndOfFile()

                    guard process.terminationStatus == 0 else {
                        let errData = stderr.fileHandleForReading.readDataToEndOfFile()
                        let errMsg = String(data: errData, encoding: .utf8) ?? "Unknown error"
                        continuation.resume(throwing: ScannerError.scanFailed("Exit \(process.terminationStatus): \(errMsg)"))
                        return
                    }

                    let output = String(data: data, encoding: .utf8) ?? ""

                    // Extract JSON between markers to avoid log noise
                    guard let startRange = output.range(of: "__JSON_START__"),
                          let endRange = output.range(of: "__JSON_END__") else {
                        continuation.resume(returning: [])
                        return
                    }

                    let jsonString = String(output[startRange.upperBound..<endRange.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
                    guard let jsonData = jsonString.data(using: .utf8) else {
                        continuation.resume(returning: [])
                        return
                    }

                    let signals = try JSONDecoder().decode([Signal].self, from: jsonData)
                    continuation.resume(returning: signals)
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}

enum ScannerError: LocalizedError {
    case scanFailed(String)

    var errorDescription: String? {
        switch self {
        case .scanFailed(let msg): return msg
        }
    }
}
