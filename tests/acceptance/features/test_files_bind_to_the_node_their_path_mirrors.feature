# BDL-074 C1, `beadloom-5qgt`.
#
# Until this bead `beadloom ctx` named a node's tests from a guess: a test file was
# given to every node whose name its file name, its folder or one of its imports
# happened to spell. Measured on this repository on 2026-09-27: 532 of the 1 064
# entries were mutmut copies under `mutants/`, the root node was given 882 files
# because every test imports the top-level package, and `ctx rule-engine` said 0.
#
# A test file now belongs to the node that owns the code its path mirrors:
# `tests/unit/<path>/test_<name>.py` names `<package>/<path>/<name>.py`, and the
# node that owns that path — the most specific one, by the rule ownership already
# uses — is the node the test binds to. A node may also claim tests its path does
# not mirror, with a `tests:` list in its YAML.

@bead:beadloom-5qgt @node:test-mapping
Feature: A test file binds to the node that owns the code its path mirrors

  Scenario: a test under the mirrored path is shown as the tests of the node owning that code
    Given a project whose ledger package holds a posting module owned by its own node
    And a unit test laid out under the mirror of the posting module
    When the index is rebuilt and the context of the posting node is read
    Then the tests it names are that unit test and no other

  Scenario: a parent node's tests are its children's files counted once
    Given a project whose ledger package holds a posting module owned by its own node
    And a unit test laid out under the mirror of the posting module
    And a unit test laid out under the mirror of a ledger module no child node owns
    When the index is rebuilt and the context of the ledger node is read
    Then the tests it names are both unit tests, each counted once

  Scenario: a test a node declares in its tests list binds to that node and survives the rebuild
    Given a project whose ledger package holds a posting module owned by its own node
    And a test file at the top of the tests folder that the posting node declares in its tests list
    When the index is rebuilt and the context of the posting node is read
    Then the tests it names are the declared test file and no other

  Scenario: a test not yet laid out under a mirrored folder binds to nothing and is counted as unplaced
    Given a project whose ledger package holds a posting module owned by its own node
    And a test file at the top of the tests folder that no node declares
    When the index is rebuilt
    Then the rebuild reports one unplaced test file
    And the context of the posting node names no test

  Scenario: a mutation-testing copy of a test is no node's test
    Given a project whose ledger package holds a posting module owned by its own node
    And a unit test laid out under the mirror of the posting module
    And a mutation-testing copy of that unit test under the mutants folder
    When the index is rebuilt and the context of the posting node is read
    Then the tests it names are that unit test and no other
