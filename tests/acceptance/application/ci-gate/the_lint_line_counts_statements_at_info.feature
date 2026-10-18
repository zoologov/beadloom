# BDL-083 S1 fix 1, beadloom-4m0w (S1R Minor 5 on beadloom-pohj).
#
# S1b added `info` as the severity of a live rule with nothing to ban. The Gate's lint
# line counted errors and warnings only, so a lint whose only findings were statements
# at info read "0 error(s), 0 warning(s)" and named no count for what it had found.

@bead:beadloom-4m0w @node:ci-gate
Feature: the gate's lint line counts the statements it made at info

  A statement at info decides nothing, and it is still something the lint found. The
  line that summarises the lint names how many there were, so the findings printed
  under the verdict are not more than the counts beside it.

  Scenario: a live rule with nothing to ban is counted on the lint line
    Given the monorepo fixture, whose digest domain has nothing of "os" to ban
    When the gate runs on that project
    Then the lint line counts 1 statement(s) at info
    And the lint step passes

  Scenario: a lint with no statement at info keeps its line
    Given a project on which every gate step passes
    When the gate runs on that project
    Then the lint line names no statement at info
