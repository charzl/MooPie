// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MooSwift",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "MooSwift", targets: ["MooSwift"])],
    targets: [
        .target(name: "MooCore"),
        .executableTarget(name: "MooSwift", dependencies: ["MooCore"]),
        .testTarget(name: "MooCoreTests", dependencies: ["MooCore"])
    ]
)
