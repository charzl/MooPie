// swift-tools-version: 5.9
import PackageDescription
import Foundation
let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().path
let sdkData = try! Data(contentsOf: URL(fileURLWithPath: root + "/sdk.json"))
let sdkInfo = try! JSONSerialization.jsonObject(with: sdkData) as! [String: String]
let sdkRoot = root + "/" + sdkInfo["source_dir"]!
let package = Package(name: "MooSwiftCpp", platforms: [.macOS(.v14)],
 products: [.executable(name: "MooSwiftCpp", targets: ["MooSwift"])],
 targets: [
 .target(name: "MooBridge", publicHeadersPath: "include",
 cxxSettings: [.unsafeFlags(["-I\(sdkRoot)/include", "-I\(root)/thirdlib/include"])],
 linkerSettings: [.unsafeFlags(["-L\(root)/build-sdk", "-L\(root)/thirdlib/lib", "-lMMAPI", "-lprotobuf", "-lssl", "-lcrypto", "-Xlinker", "-rpath", "-Xlinker", "\(root)/thirdlib/lib"])]),
 .target(name: "MooCore", dependencies: ["MooBridge"]),
 .executableTarget(name: "MooSwift", dependencies: ["MooCore", "MooBridge"]),
 .testTarget(name: "MooCoreTests", dependencies: ["MooCore", "MooBridge"]),
 .testTarget(name: "MooIntegrationTests", dependencies: ["MooCore", "MooBridge", "MooSwift"])
 ], cxxLanguageStandard: .cxx17)
