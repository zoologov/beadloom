# BDL-078, `beadloom-jcng`. Found by BDL-076 (`beadloom-ujzb.14`, `beadloom-ujzb.16`): a Go
# import is resolved through the `go.mod` and `go.work` that govern the importing file, and
# a Swift import through `Package.swift`, but an incremental reindex re-read a file's
# imports only when that file changed. Editing a manifest alone left every import under it
# resolved as before, until the importing files were touched or a full reindex ran. And a
# module whose path has no `/`, imported as its own root package, was dropped by the
# extractor before any manifest was read, because the extractor took every such path for
# the standard library.
#
# The fixtures are Go and Swift projects this repository cannot be mistaken for.

@bead:beadloom-jcng @node:import-resolver
Feature: a manifest is an input of every file it governs

  Scenario: an incremental index after go.mod renames the module equals a fresh index
    Given a Go service whose go.mod declares a module path its imports do not use
    And the project is indexed
    When go.mod is rewritten to declare the module path the imports use and the index is updated
    Then the import "example.org/harbour/internal/berths" of "internal/ledger/ledger.go" resolves to "berths"
    And every resolved import and every derived edge equals a fresh index of the same tree

  Scenario: an incremental index after go.work replaces a module with a folder equals a fresh index
    Given a Go workspace whose go.work does not yet replace the money module
    And the project is indexed
    When go.work is rewritten to replace the money module with its folder and the index is updated
    Then the import "example.org/money/fx" of "services/orders/orders.go" resolves to "money"
    And every resolved import and every derived edge equals a fresh index of the same tree

  Scenario: an incremental index after Package.swift moves a target equals a fresh index
    Given a Swift package whose manifest places the Core target in a folder that holds no code
    And the project is indexed
    When Package.swift is rewritten to place Core where its code is and the index is updated
    Then the import "Core" of "Sources/App/main.swift" resolves to "core"
    And every resolved import and every derived edge equals a fresh index of the same tree

  Scenario: a module whose path has no slash is imported as its own root package
    Given a Go module named tidewater whose command imports the module's root package
    When the project is indexed
    Then the import "tidewater" of "tidewater/cmd/tide/main.go" resolves to "tide"
    And the import "fmt" of "tidewater/cmd/tide/main.go" is recorded with no node
