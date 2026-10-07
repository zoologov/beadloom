# BDL-078, `beadloom-76mk` (observed by BDL-076 `beadloom-ujzb.17`).
#
# The most common Python layout keeps its tests directly under `tests/`. Init laid
# out no binding for them: the mirror reads `tests/unit/**` and
# `tests/integration/**` only, so every flat `tests/test_<module>.py` was unplaced,
# the node card said "no bound tests" and impact marked every node at risk.
#
# Init now declares `flat_tests: true` in the test layout of a Python project, and
# a flat test binds to the node owning the module its name names, else to the one
# node its imports reach. A project whose config does not declare it keeps the
# binding it had: the declaration is what makes the name a statement and not the
# guess the mirror replaced. Init names every test file it could not bind.

@bead:beadloom-76mk @node:test-mapping
Feature: A flat Python test binds to the node it tests after init

  Scenario: a flat test named after a module binds to the node owning that module
    Given a Python project with a billing and a storage package and its tests directly under tests
    And a flat test named after the invoice module of the billing package
    When the project is initialised
    Then the context of the billing node names that flat test

  Scenario: a flat test named after no module binds to the one node its imports reach
    Given a Python project with a billing and a storage package and its tests directly under tests
    And a flat test named after no module that imports only the storage package
    When the project is initialised
    Then the context of the storage node names that flat test

  Scenario: a flat test that names no module and imports two nodes is named by init as unbound
    Given a Python project with a billing and a storage package and its tests directly under tests
    And a flat test named after no module that imports both packages
    When the project is initialised
    Then the init output names that flat test as bound to no node
    And no node's context names that flat test

  Scenario: a project whose test layout does not declare flat tests keeps them unbound
    Given a Python project with a billing and a storage package and its tests directly under tests
    And a flat test named after the invoice module of the billing package
    And the project's config declares a test layout without flat tests
    When the index is rebuilt
    Then no node's context names that flat test
