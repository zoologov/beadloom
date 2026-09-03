# A duty declared for a role is carried by that role's composed core (BDL-068 S4).
# One Feature per file.

@bead:beadloom-0mdo.27 @node:role-duties
Feature: a duty declared for a role reaches that role's composed core

  Measured four times across two epics: a duty an agent is obliged to perform is
  written somewhere the performer does not read. The clean-room rule lives in the
  coordinator's prose and in the wave planner, and occurs zero times in the role
  cores the roles actually receive. Every agent said the right words because the
  coordinator typed them into every launch prompt.

  A duty is DECLARED, never inferred from prose. An English-keyword detector over
  role text would be the fourth instance of a class this project has already filed
  three times -- a classifier that binds "supports 11 languages" to a count of the
  languages the project is written in, reads a version cited as an example as a
  claim, and verifies nothing in a non-English document while counting it scanned.
  So a duty carries a marker, the way a scenario carries its bead and its node, and
  the binding is checked in BOTH directions.

  The check covers composed artifacts and nothing else. A duty carried only by a
  coordinator's launch prompt is unreachable by any file-based check, because a
  prompt is not an artifact -- and that limit is the argument for moving a duty
  into a composed core rather than a reason to leave it where it is.

  Scenario: a duty declared for a role that does not carry it is a finding
    Given a flow whose coordinator declares the "clean-room" duty for dev and review
    And the dev role's project layer carries the "clean-room" duty
    When the duties are checked
    Then "review" is reported as a role that does not carry "clean-room"
    And "dev" is not reported as a role that does not carry "clean-room"

  Scenario: a duty a role carries and no artifact declares is a finding
    Given the dev role's project layer carries the "clean-room" duty
    And no artifact declares the "clean-room" duty
    When the duties are checked
    Then "clean-room" is reported as carried by dev and declared by nothing

  Scenario: a duty declared for a role this flow does not ship is a finding
    Given a flow whose coordinator declares the "clean-room" duty for dev and scout
    And the dev role's project layer carries the "clean-room" duty
    When the duties are checked
    Then "scout" is reported as a role no core fragment ships

  Scenario: a duty declared and carried by every role it names is no finding
    Given a flow whose coordinator declares the "clean-room" duty for dev and review
    And the dev role's project layer carries the "clean-room" duty
    And the review role's project layer carries the "clean-room" duty
    When the duties are checked
    Then no duty finding is reported
    And the report still names the channel it cannot inspect

  Scenario: the report names the channel it cannot inspect
    Given a flow whose coordinator declares the "clean-room" duty for dev and review
    And the dev role's project layer carries the "clean-room" duty
    When the duties are checked
    Then the report names the launch prompt as a channel no file-based check reaches
    And the report states how many artifacts it did inspect

  Scenario: a fragment no composition includes is named as not inspected, not as absent
    Given a project fragment for a role this flow does not ship carries the "clean-room" duty
    When the duties are checked
    Then that fragment is reported as not inspected
    And it is not reported as a role that carries "clean-room"

  Scenario: a duty finding blocks the agent-config check
    Given a flow whose coordinator declares the "clean-room" duty for dev and review
    And the dev role's project layer carries the "clean-room" duty
    When the agent-config check runs
    Then the check reports the undelivered duty and blocks
