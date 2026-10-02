# BDL-076, the re-review's finding m5 (`beadloom-ujzb.22`), fixed by `beadloom-ujzb.24`.
# Since R2 finding 6 a Java or Kotlin import is mapped to its package's folder through
# each file's `package` declaration. Where two folders declare one package, the first
# folder read kept it: `import org.ex.shared.B` resolved to the folder holding `A`, and
# init and reindex both drew the false edge `c -> a` while `B` lives in `b`.
#
# An import that names a class is resolved to the folder holding that class; an import
# that names none of them resolves to nothing, rather than to a folder picked by order.

@bead:beadloom-ujzb.24 @node:import-resolver
Feature: an import of a package declared in two folders reaches the folder holding its class

  Scenario: init and reindex draw the edge to the folder of the imported class only
    Given a Kotlin project where "src/main/kotlin/a" and "src/main/kotlin/b" both declare "org.ex.shared" and "c" imports "org.ex.shared.B"
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the graph init writes has exactly the depends_on edges "c -> b"
    And the index holds exactly the depends_on edges "c -> b"
    And the import "org.ex.shared.B" of "src/main/kotlin/c/C.kt" is resolved to "b"

  Scenario: a wildcard import of that package resolves to no folder
    Given a Kotlin project where "src/main/kotlin/a" and "src/main/kotlin/b" both declare "org.ex.shared" and "c" imports "org.ex.shared.*"
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the graph init writes has no depends_on edge
    # The index records a Kotlin wildcard import by the package it names.
    And the import "org.ex.shared" of "src/main/kotlin/c/C.kt" is not resolved
