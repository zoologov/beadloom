# BDL-083 S1e2, beadloom-jwfc (BDL-UX #226; RFC D1).
#
# Measured at 12c35cf3 (Darwin arm64, CPython 3.13.7). `beadloom ci --format rich` over
# this repository, its stdout and stderr on a pipe set non-blocking whose reader started
# two seconds late, exited 1 with `BlockingIOError: [Errno 35] write could not complete
# without blocking`, and the reader received 83518 of the 229492 bytes the same run
# writes to a file. Through the pre-push hook the Gate itself survived, because the hook
# captured its report, but the shell then printed that report into the same pipe: under
# dash the print stopped at 65575 bytes, the verdict line and the hook's own sentence never
# arrived, and the hook exited 0.

@bead:beadloom-jwfc @node:cli-commands
Feature: the Gate's report survives a pipe that will not wait

  An agent's shell hands `git push` a pipe it reads when it gets to it, and sets the pipe
  non-blocking. A write that does not fit then fails at once instead of waiting, and the
  bigger the honest report, the likelier it fails. The Gate writes its report whole and
  waits for the reader when it must. The pre-push hook does not print that report a second
  time through the shell, and it does not let its own sentence fall on the floor.

  Scenario: the whole report reaches a reader that starts late
    Given a project on which every gate step passes
    And its doctor step reports more findings than a pipe holds
    When the gate runs with its output on a non-blocking pipe whose reader starts late
    Then the gate exits 1
    And the reader receives every byte the gate writes to a file
    And the pipe is non-blocking again when the gate is done

  Scenario: the pre-push hook passes the whole report and its own sentence through
    Given a project on which every gate step passes
    And its doctor step reports more findings than a pipe holds
    And the composed hooks installed in it
    When the pre-push hook runs with its output on a non-blocking pipe whose reader starts late
    Then the hook exits non-zero
    And the reader receives every byte the gate writes to a file
    And the hook says the Gate blocked this push and names the verdict

  Scenario: the hook tells a Gate in which a step crashed from one that found something
    Given a project on which every gate step passes
    And the docs-audit step raises an unexpected exception
    And the composed hooks installed in it
    When the pre-push hook runs with its output on a non-blocking pipe whose reader starts late
    Then the hook exits non-zero
    And the hook says a step crashed and that what it checks was not checked
    And the hook does not say the findings above name their fixes
