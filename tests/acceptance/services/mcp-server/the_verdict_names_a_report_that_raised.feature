# BDL-083 S1 fix 4, beadloom-ba9w.17 (the #318 class on the MCP surface; RFC D1).
#
# S1 fix 1 put the Gate's three post-step reports under one boundary and gave each a
# reason when it raises. The MCP `complete_bead` tool reads two of them on its own
# account: its `not_run` list was empty when the coverage report raised, so a report
# that raised read as "nothing was skipped", and it took its own room census outside
# any boundary, so an exception there ended the tool call with a traceback.

@bead:beadloom-ba9w.17 @node:mcp-server
Feature: the verdict an agent closes a bead on names a report that raised

  The room and the list of verifications not run qualify the verdict and change
  neither its status nor which findings it returns. When one of them could not be
  derived, the tool says so in a sentence naming the exception, and the verdict is
  the one the gate produced.

  Scenario: the coverage report raises and the verdict says why nothing is listed as not run
    Given a project on which every gate step passes and whose pipeline runs the test suite
    And the coverage report raises an unexpected exception
    When an agent completes a bead through the MCP tool without the test suite
    Then the tool closes the bead with the verdict "PASS"
    And its "not_run_reason" is "the coverage report raised LookupError: injected fault"

  Scenario: the coverage report is derived and no reason is given
    Given a project on which every gate step passes and whose pipeline runs the test suite
    When an agent completes a bead through the MCP tool without the test suite
    Then the tool closes the bead with the verdict "PASS"
    And its "not_run" names "the test suite"
    And its "not_run_reason" is empty

  Scenario: the room census raises and the verdict says why no room is stated
    Given a project on which every gate step passes and whose pipeline runs the test suite
    And the room census raises an unexpected exception
    When an agent completes a bead through the MCP tool without the test suite
    Then the tool closes the bead with the verdict "PASS"
    And its room gives the reason "the room census raised LookupError: injected fault"
