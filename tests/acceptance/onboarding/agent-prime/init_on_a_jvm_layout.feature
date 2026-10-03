# BDL-076 B6. Measured by B3 (`beadloom-hmqn`) on the Java (Maven) and Kotlin
# (Gradle) adopter fixtures: `init` made nodes of the source sets — `src/main`,
# `src/main/java`, `src/test`, `src/test/java` — wrote `scan_paths: [src]`, made no
# node of any package and drew no `depends_on` edge. With `src` as the scan path
# a dotted import is looked up under `src/org/...`, where no code is.
#
# The projects are written here, not taken from this repository, which holds no
# Java or Kotlin. Each one carries a trap the old reading falls into: a third-party
# import whose segments name one of the project's packages.

@bead:beadloom-ujzb.15 @node:agent-prime
Feature: init makes a node of each package of a Maven or Gradle project, not of its source sets

  Scenario: init on a Maven project writes its packages, its source root and its imports
    Given a Maven project with the packages web, pricing and model under src/main/java
    When beadloom init is run without prompts
    Then the code nodes init writes have exactly the sources "src/main/java/org/acme/toll/model/", "src/main/java/org/acme/toll/pricing/", "src/main/java/org/acme/toll/web/"
    And the scan paths init writes are exactly "src/main/java"
    And the graph init writes has exactly the depends_on edges "web -> pricing", "pricing -> model"

  Scenario: reindex after init resolves the dotted imports and binds the test to its package
    Given a Maven project with the packages web, pricing and model under src/main/java
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the index holds exactly the depends_on edges "web -> pricing", "pricing -> model"
    And the test file "src/test/java/org/acme/toll/pricing/TariffTest.java" is bound to "pricing"

  Scenario: init on a Gradle build of two modules puts each module's packages under the module
    Given a Gradle build whose settings include the modules core in Java and app in Kotlin
    When beadloom init is run without prompts
    And beadloom reindex is run
    Then the code nodes init writes have exactly the sources "app/", "app/src/main/kotlin/org/acme/app/planner/", "app/src/main/kotlin/org/acme/app/routing/", "core/", "core/src/main/java/org/acme/core/geo/", "core/src/main/java/org/acme/core/model/"
    And the scan paths init writes are exactly "app/src/main/kotlin", "core/src/main/java"
    And the graph init writes has exactly the depends_on edges "app -> core"
    And the index holds exactly the depends_on edges "app -> core", "app-routing -> app-planner", "app-routing -> core-model", "app-planner -> core-geo", "core-model -> core-geo"
