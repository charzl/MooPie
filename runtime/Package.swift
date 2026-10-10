// swift-tools-version: 5.9
import PackageDescription
let package = Package(name: "OpenDManager", platforms: [.macOS(.v14)], products: [.executable(name: "OpenDManager", targets: ["OpenDManager"])], targets: [.target(name: "OpenDRuntime"), .executableTarget(name: "OpenDManager", dependencies: ["OpenDRuntime"]), .testTarget(name: "OpenDRuntimeTests", dependencies: ["OpenDRuntime"])])
