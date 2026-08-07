// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "contacts",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "contacts", targets: ["contacts"])
    ],
    targets: [
        .executableTarget(
            name: "contacts",
            linkerSettings: [.linkedFramework("Contacts")]
        )
    ]
)
