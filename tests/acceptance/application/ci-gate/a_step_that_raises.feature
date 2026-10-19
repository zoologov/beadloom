# BDL-083 S1e, beadloom-ba9w.13 (BDL-UX #318; RFC D1).
#
# Measured at 3e95a208 (Darwin arm64, CPython 3.13): `beadloom ci` over this
# repository with the docs-audit step made to raise exited 1 and printed nothing at all.
# The exception left the command, and the seven steps after docs-audit never ran. The
# Gate promises it never short-circuits, and the promise held for a step that FAILED
# and not for a step that raised.

@bead:beadloom-ba9w.13 @node:ci-gate
Feature: a gate step that raises is reported as crashed, and the other steps still run

  A step that raises has checked nothing, so it cannot read PASS, and it did not choose
  not to run, so it cannot read SKIP. It reads ERROR, with the exception it raised, and
  the steps after it run as they would have. The verdict is red and says how many steps
  crashed, because a run in which a checker broke is a run whose green nobody measured.

  Scenario: a step that raises reads ERROR and every step after it still reports
    Given a project on which every gate step passes
    And the docs-audit step raises an unexpected exception
    When the gate runs on that project
    Then the docs-audit step reads ERROR and names the exception it raised
    And every step after docs-audit reported a status of its own
    And the gate exits 1
    And the verdict says 1 step(s) crashed and names docs-audit

  Scenario: the JSON report names the crashed step and its exception
    Given a project on which every gate step passes
    And the docs-audit step raises an unexpected exception
    When the gate reports on that project as JSON
    Then the docs-audit step's status is ERROR and its error names the exception
    And the report lists docs-audit as the one crashed step
