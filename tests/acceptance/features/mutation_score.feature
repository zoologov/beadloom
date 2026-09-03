# The score a mutation run produced, as against a sentence claiming one
# (BDL-068 S3.1). One Feature per file.

@bead:beadloom-0mdo.22 @node:mutation-scope
Feature: a mutation score is produced by a command over a declared scope

  BDL-061 S4 put a mutation-testing duty into every composed role core and
  shipped no way to tell a performed check from a claimed one. Four beads in
  BDL-067 then reported "mutation checking" by four different hand methods, and
  one of those reports -- "all 20 assertions red before the fix" -- turned out
  to be eleven guards that cannot fail.

  Beadloom still owns no runner: the tool is the project's choice. What it owns
  is the declared SCOPE and this REPORT over whatever counters a run left
  behind.

  Scenario: a mutation run reports a score for the slice it was scoped to
    Given a project declaring the mutation target "src/core/"
    And a run over "src/core/" that killed 8 of 10 mutants
    When the mutation score is reported
    Then the score is 80 percent
    And the report names the room the run was measured in

  Scenario: a run that produced no mutants is a finding rather than a full score
    Given a project declaring the mutation target "src/core/"
    And a run over "src/core/" that produced no mutants at all
    When the mutation score is reported
    Then the run is reported as having produced no mutants
    And no score is stated

  Scenario: a declared target no run covered is reported
    Given a project declaring the mutation target "src/core/"
    And a run over "src/other/" that killed 8 of 10 mutants
    When the mutation score is reported
    Then "src/core/" is reported as measured by no run

  Scenario: counters a score cannot be computed from are reported, not defaulted
    Given a project declaring the mutation target "src/core/"
    And a run over "src/core/" whose counters do not say how many were killed
    When the mutation score is reported
    Then the missing counter is reported
    And no score is stated

  Scenario: a slice names the declared targets it did not judge
    Given a project declaring the mutation targets "src/core/" and "src/other/"
    And a run over "src/core/" that killed 8 of 10 mutants
    And the run is answerable only for "src/core/"
    When the mutation score is reported
    Then "src/other/" is named as not judged by this run
    And nothing is reported about "src/other/"
