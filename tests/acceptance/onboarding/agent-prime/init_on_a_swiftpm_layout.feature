# BDL-076 B7. Measured by B3 (`beadloom-hmqn`) on the Swift adopter fixture: `init`
# on a Swift Package Manager project wrote `Graph: 0 nodes, 0 edges`,
# `languages: [python]` and `scan_paths: [src]`. `Package.swift` was no manifest it
# knew and `Sources/` no source folder, so no target was a node and no `import`
# between targets became an edge.
#
# The packages are written here, not taken from this repository, which holds no
# Swift. Each one imports what must stay unresolved: an Apple framework
# (`Foundation`) and a product of a remote package (`Logging`).

@bead:beadloom-ujzb.16 @node:agent-prime
Feature: init makes a node of each target of a Swift package and an edge of each import between them

  Scenario: init on a Swift package writes its targets, their source folders and the imports between them
    Given a Swift package with the library targets TrailCore and TrailNet and the executable target TrailApp
    When beadloom init is run without prompts
    Then the code nodes init writes have exactly the sources "Sources/TrailApp/", "Sources/TrailCore/", "Sources/TrailNet/"
    And the scan paths init writes are exactly "Sources/TrailApp", "Sources/TrailCore", "Sources/TrailNet"
    And the languages init writes are exactly ".swift"
    And the graph init writes has exactly the depends_on edges "TrailApp -> TrailCore", "TrailApp -> TrailNet", "TrailNet -> TrailCore"

  Scenario: reindex after init resolves the imports and binds the test target to the target it tests
    Given a Swift package with the library targets TrailCore and TrailNet and the executable target TrailApp
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the index holds exactly the depends_on edges "TrailApp -> TrailCore", "TrailApp -> TrailNet", "TrailNet -> TrailCore"
    And the test file "Tests/TrailCoreTests/RouteTests.swift" is bound to "TrailCore"

  Scenario: a target whose folder the manifest names is found there, and so are its tests
    Given a Swift package whose target Engine declares the path "Engine" and whose test target SmokeChecks depends on it
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the code nodes init writes have exactly the sources "Engine/", "Sources/Launcher/"
    And the scan paths init writes are exactly "Engine", "Sources/Launcher"
    And the index holds exactly the depends_on edges "Launcher -> Engine"
    And the test file "Tests/SmokeChecks/IgnitionSmoke.swift" is bound to "Engine"
