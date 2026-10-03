# BDL-076 R2 finding 7 (`beadloom-fht7`), fixed by `beadloom-ujzb.19`. init reads Swift
# through Swift Package Manager manifests (B7). The most common iOS layout - an
# `.xcodeproj` beside a folder of `.swift` files, no `Package.swift` - got
# "Graph: 0 nodes, 0 edges", `languages: [python]`, `scan_paths: [src]` and exit 0,
# with no word that Swift files were seen and not read.
#
# Decision: say it, do not guess it. An Xcode project keeps its modules (targets) and
# their file membership in `project.pbxproj`, not in folders, and the files of one
# target see each other without an import, so folder nodes guessed from the tree
# would carry no edge by construction and would look like a reading. init names what
# it found and what it could not read.

@bead:beadloom-ujzb.19 @node:agent-prime
Feature: init says which Swift files it could not read, rather than writing an empty graph silently

  Scenario: an Xcode project with no Package.swift is named, with the Swift files init did not read
    Given an Xcode project "Beacon.xcodeproj" with 2 Swift files and no Package.swift
    When beadloom init is run without prompts
    Then init says it did not read 2 Swift files and names "Beacon.xcodeproj"
    And init says Swift is read through Package.swift only

  Scenario: a Swift package beside an Xcode app names only the app's files as unread
    Given an Xcode project "Beacon.xcodeproj" with 2 Swift files and no Package.swift
    And a Swift package "Packages/BeaconKit" with one target holding 1 Swift file
    When beadloom init is run without prompts
    Then the code nodes init writes have exactly the sources "Packages/BeaconKit/", "Packages/BeaconKit/Sources/BeaconKit/"
    And init says it did not read 2 Swift files and names "Beacon.xcodeproj"
