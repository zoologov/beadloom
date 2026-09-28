# BDL-074 G2, `beadloom-2mj3.11` (review `beadloom-b9ll` M3 and m5).
#
# The binding read only `tests/**/test_*.py`. On a Go module with a test beside
# each package, `beadloom ctx billing` said "go_test, 1 tests in 1 files" before
# the binding and "none, 0 tests in 0 files" after it. The owner ruled on
# 2026-09-28: a test file inside a node's source binds to the node covering it,
# the test roots and file-name patterns are configuration, and nothing is bound
# by a guess at its name.

@bead:beadloom-2mj3.11 @node:test-mapping
Feature: A test beside the code, or under a declared root, binds to its node

  Scenario: a Go test beside its package is shown as that package's test
    Given a Go module with a test beside each of its two packages
    When the index is rebuilt and the context of the billing node is read
    Then the context names the billing test as a go_test file holding 1 test

  Scenario: a Python test under the root the project declares is shown as its node's test
    Given a Python project that declares test as its test root and mirrors billing under it
    When the index is rebuilt and the context of the billing node is read
    Then the context names the mirrored billing test as a pytest file holding 2 tests

  Scenario: a tests list entry that covers no test file is reported by node and entry
    Given a Go module with a test beside each of its two packages
    And the billing node declares a tests entry that names no test file
    When the index is rebuilt
    Then the rebuild warns that the billing entry binds nothing
