# BDL-083 S1 fix 1, beadloom-4m0w (S1R Major 1 on beadloom-pohj; BDL-UX #318; RFC D1).
#
# S1e put every gate step inside the boundary. The room census, the verification
# coverage and the ownership report are derived after the steps, and an exception in
# any of them left `run_ci_gate` as a traceback: the verdict of steps that had all run
# was lost with it (measured on 2026-10-18 by the strict test the review ruled on).

@bead:beadloom-4m0w @node:ci-gate
Feature: a report the gate derives after its steps that raises leaves the verdict standing

  The room, the coverage and the ownership reports describe a finished run. None of
  them changes a status or the exit code, so one of them raising must not take the
  verdict of the steps with it. The report that raised says so and names the exception,
  and the verdict and the exit code are the ones the steps produced.

  Scenario Outline: the <report> raises and the verdict of the steps stands
    Given a project on which every gate step passes
    And the <report> raises an unexpected exception
    When the gate runs on that project
    Then the gate exits 0 with the verdict "PASS — gate clean"
    And the report says "the <report> raised LookupError: injected fault"

    Examples:
      | report           |
      | room census      |
      | coverage report  |
      | ownership report |

  Scenario Outline: the JSON report carries the reason on the report that raised
    Given a project on which every gate step passes
    And the <report> raises an unexpected exception
    When the gate reports on that project as JSON
    Then the JSON report is ok with no crashed step
    And its "<key>" entry gives the reason "the <report> raised LookupError: injected fault"

    Examples:
      | report           | key       |
      | room census      | room      |
      | coverage report  | not_run   |
      | ownership report | ownership |
