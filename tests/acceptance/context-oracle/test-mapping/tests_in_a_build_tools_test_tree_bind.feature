# BDL-074 G2b, `beadloom-2mj3.13`.
#
# After G2 a Java, Kotlin or Swift project found no test file at all: the defaults
# named Python, Go and JS/TS only. On main the retired mapper had read "junit, 2
# tests in 1 files" for a Maven package and "xctest, 2 tests in 1 files" for a
# Swift package's target. The owner ruled on 2026-09-28: add each ecosystem's own
# conventions — its test file names, and the test tree its build tool runs.

@bead:beadloom-2mj3.13 @node:test-mapping
Feature: A test in a build tool's test tree binds to the code it mirrors

  Scenario: a Java test in the Maven test tree is shown as its package's test
    Given a Maven project with a test class for each of its two packages
    When the index is rebuilt and the context of the billing node is read
    Then the context names the billing test class as a junit file holding 2 tests

  Scenario: a Swift test in a package's test target is shown as the test of the folder it names
    Given a Swift package whose test target holds a test file for each of its two folders
    When the index is rebuilt and the context of the billing node is read
    Then the context names the billing test file as an xctest file holding 2 tests
