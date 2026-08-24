# BDL-UX #118, closed in BDL-061 S6. Parallel agents in one working tree do not
# conflict on disjoint FILES, but they collide on the shared pre-commit hook:
# it judged the whole tree, so one agent's commit was blocked by a neighbour's
# in-progress work. The repair is a boundary rather than a tolerance — the
# commit gate judges the commit, the push gate judges the tree — and the half it
# does not judge is stated rather than left to be assumed clean.

@bead:beadloom-mr2l.21 @node:sync-check
Feature: the commit gate judges the commit, and names the tree it did not judge

  Scenario: A neighbour's uncommitted work does not fail this commit
    Given a project with a stale doc pair whose code file is staged
    And a second stale doc pair whose code file is modified but not staged
    When the doc-freshness check is scoped to what the commit stages
    Then the check reports the staged pair as stale
    And the check does not report the unstaged pair as stale

  Scenario: The commit gate says how many pairs it left to the push gate
    Given a project with a stale doc pair whose code file is staged
    And a second stale doc pair whose code file is modified but not staged
    When the doc-freshness check is scoped to what the commit stages
    Then the check states the number of pairs it did not check

  Scenario: A commit that stages nothing the graph owns checks nothing and says so
    Given a project with a stale doc pair whose code file is modified but not staged
    When the doc-freshness check is scoped to what the commit stages
    Then the check reports no stale pair
    And the check states the number of pairs it did not check
