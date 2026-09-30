// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "BeaconKit",
    products: [
        .executable(name: "beacon", targets: ["BeaconApp"]),
    ],
    targets: [
        .target(name: "BeaconCore"),
        .target(name: "BeaconNetwork", dependencies: ["BeaconCore"]),
        .executableTarget(name: "BeaconApp", dependencies: ["BeaconNetwork", "BeaconCore"]),
        .testTarget(name: "BeaconCoreTests", dependencies: ["BeaconCore"]),
    ]
)
