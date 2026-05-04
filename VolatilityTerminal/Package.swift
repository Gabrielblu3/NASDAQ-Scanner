// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "VolatilityTerminal",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "VolatilityTerminal",
            path: "Sources"
        ),
    ]
)
