# What the push Gate does NOT do, said by the Gate (BDL-068 S6, BDL-UX #247).
# One Feature per file.

@bead:beadloom-0mdo.48 @node:ci-gate
Feature: the gate names the verifications no step of it performed

  `beadloom ci` runs reindex, lint, sync-check, docs-audit, docs-quality,
  doc-spaces, scope-check, config-check and doctor. It does not run the test
  suite. The division is reasonable and every step it does run is named. What
  was missing is the other half: the run never said the suite was not among
  them, while the pre-push hook it backs is described as "the full `beadloom
  ci`".

  Measured twice in one slice: a document change reddened two tests and the
  Gate returned rc 0, and a docs wave spilled a code span past a line and the
  Gate returned rc 0 over that tree twice, after which all six test legs went
  red on one assertion that reproduces locally in 0.07 seconds.

  The claim is DERIVED from the run's own step list, so a suite step added to
  the gate later removes the line by the same act rather than by somebody
  remembering to delete a sentence.

  Scenario: the gate names the test suite as not run by it
    Given a project whose pipeline runs the test suite
    When the gate reports on that project
    Then the report names the test suite as not run by this gate
    And it names the command the pipeline runs for it

  Scenario: a verification a step of the run performs is not named as not run
    Given a project whose pipeline runs the test suite
    When the gate reports a run that performs the suite itself
    Then the report does not name the test suite as not run

  Scenario: a verification this project's pipeline does not run is not claimed
    Given a project whose pipeline runs no verification this report reads
    When the gate reports on that project
    Then the report names no verification as not run

  Scenario: a pipeline this report could not read is said to be unread
    Given a project whose workflow file cannot be parsed
    When the gate reports on that project
    Then the report says the pipeline could not be read

  Scenario: naming what was not run does not change the verdict
    Given a project whose pipeline runs the test suite
    When the gate reports on that project
    Then the verdict and the exit code are the ones the steps produced
