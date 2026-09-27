# BDL-074 C2, `beadloom-3z94`.
#
# C1 made the binding the source of a node's tests: a test file belongs to the node
# that owns the code its path mirrors. Two readers were left. `beadloom ctx` printed
# the bound count and nothing else, so a repository whose tests are not laid out yet
# read "0 tests" — the same words a node with no test at all gets. And the debt
# report still called the name-guessing mapper, which counted a node "untested" only
# when no test framework was detected anywhere, so on this repository it said 0.
#
# Both now read the binding, and both say when the binding cannot answer yet: a test
# file that is not under `tests/unit/` or `tests/integration/` binds to no node, so a
# node with no bound test may still be tested by it.

@bead:beadloom-3z94
Feature: ctx and the debt report read the test binding, and say when it cannot answer yet

  @node:context-builder @node:cli-commands
  Scenario: ctx says how many of the repository's test files are not laid out yet
    Given a project whose ledger package holds a posting module owned by its own node
    And a unit test laid out under the mirror of the posting module
    And a test file at the top of the tests folder
    When the index is rebuilt and the context of the posting node is printed
    Then the Tests line names the one laid-out test file
    And the context says that 1 of 2 test files in the repository is unplaced

  @node:context-builder @node:cli-commands
  Scenario: ctx says nothing about unplaced files when every test file is laid out
    Given a project whose ledger package holds a posting module owned by its own node
    And a unit test laid out under the mirror of the posting module
    When the index is rebuilt and the context of the posting node is printed
    Then the Tests line names the one laid-out test file
    And the context does not mention unplaced test files

  @node:debt-report
  Scenario: the debt report withholds the untested count while test files are unplaced
    Given a project whose ledger package holds a posting module owned by its own node
    And a test file at the top of the tests folder
    When the index is rebuilt and the debt report is read
    Then the debt report counts no node as untested
    And the debt report says the count was withheld because 1 of 1 test files is unplaced

  @node:debt-report
  Scenario: once every test file is laid out, a node with no bound test is untested
    Given a project whose ledger package holds a posting module owned by its own node
    And a unit test laid out under the mirror of a ledger module no child node owns
    When the index is rebuilt and the debt report is read
    Then the debt report counts the posting node as untested and the ledger node as tested
