// swift-tools-version:5.9
import PackageDescription

// Splits the helper into a pure, testable core (AudioTapCore) and the
// untestable-without-hardware executable that drives Core Audio itself
// (openspec/changes/add-macos-capture/tasks.md 4.3).
let package = Package(
    name: "audiotap-helper",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "AudioTapCore"),
        .executableTarget(
            name: "audiotap-helper",
            dependencies: ["AudioTapCore"]
        ),
        .testTarget(
            name: "AudioTapCoreTests",
            dependencies: ["AudioTapCore"]
        ),
    ]
)
