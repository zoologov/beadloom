# BDL-076 R2 finding 6 (`beadloom-fht7`), fixed by `beadloom-ujzb.19`. Kotlin's coding
# conventions recommend, for a pure Kotlin project, omitting the common root package
# from the folders: `package org.example.orchard.geo` lives in `src/main/kotlin/geo/`.
# init read an import as a folder path below the source root, so
# `org.example.orchard.geo.Row` was looked up at `src/main/kotlin/org/example/orchard/geo`,
# which does not exist: init drew no edge, reindex resolved no import, and the graph
# showed the packages unconnected with nothing saying why. The package declaration,
# not the folder path, decides which package a file is in.
#
# The project is the Kotlin adopter fixture, copied and rearranged that way.

@bead:beadloom-ujzb.19 @node:agent-prime
Feature: init and reindex read a Kotlin package by its declaration, not by its folder path

  Scenario: init draws every edge when the root package is omitted from the folders
    Given the Kotlin adopter fixture with its root package "org.example.orchard" omitted from the folders
    When beadloom init is run without prompts
    Then the code nodes init writes have exactly the sources "src/main/kotlin/geo/", "src/main/kotlin/planner/", "src/main/kotlin/routing/"
    And the graph init writes has exactly the depends_on edges "routing -> geo", "routing -> planner", "planner -> geo"

  Scenario: reindex resolves every import of the project's own packages in that layout
    Given the Kotlin adopter fixture with its root package "org.example.orchard" omitted from the folders
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then every import of a package below "org.example.orchard" in the index is resolved
    And the index holds exactly the depends_on edges "routing -> geo", "routing -> planner", "planner -> geo"
    And the test file "src/test/kotlin/planner/RoutePlannerTest.kt" is bound to "planner"
