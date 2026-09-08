# BDL-068 S5. BDL-UX #194 (2026-08-26) and #237 (2026-09-04) are one defect
# filed twice, nine days apart, by two agents that had never met: the primitive
# every launch prompt mandates before a commit in a shared tree grants no
# exclusion. Re-measured on bd 1.0.4 in an isolated rig, the primitive is not
# the broken part. `acquire` refuses a held slot with exit 1, and 32 simultaneous
# acquires over four rounds produced exactly one winner each round. What grants
# nothing is the CALL FORM this project instructs: no `--holder`, so every agent
# is the one tracker actor; a bare `release`, which is the one form bd does not
# check the holder of; and `--wait`, which appends the caller to a queue nothing
# drains and returns without blocking, under prose of ours that says it blocks.
#
# So the scenarios below are about what a wave is TOLD, not about what bd does.

@bead:beadloom-0mdo.39 @node:wave-plan
Feature: a wave states what serialises its landings, and what the lock it names does not grant

  Scenario: A wave names the landing order among the media it shares
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    When the wave shape is decided
    Then the wave names the landing order among its shared media
    And the landing-order statement says the exclusion rests on the derived scopes

  Scenario: An acquire that names no holder is reported, because one actor serves every role
    Given a flow artifact instructing "bd merge-slot acquire" before a commit
    When the landing lock sites are derived
    Then the site is reported as "anonymous-holder"

  Scenario: A release that names no holder is reported, because bd checks the holder only when asked
    Given a flow artifact instructing "bd merge-slot release" after a commit
    When the landing lock sites are derived
    Then the site is reported as "unguarded-release"

  Scenario: A wait flag is reported, because it queues the caller and returns
    Given a flow artifact instructing "bd merge-slot acquire --wait" before a commit
    When the landing lock sites are derived
    Then the site is reported as "queue-only-wait"

  Scenario: The call form that grants exclusion is reported as no defect
    Given a flow artifact instructing "bd merge-slot acquire --holder <bead-id>" before a commit
    And a flow artifact instructing "bd merge-slot release --holder <bead-id>" after a commit
    When the landing lock sites are derived
    Then no site is reported as defective

  Scenario: A wave planned over an instruction that grants nothing fails its precondition
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the shared media were measured and are clean
    And a flow artifact instructing "bd merge-slot acquire --wait" before a commit
    When the wave shape is decided
    Then the wave reports "landing-order" as failed
    And the plan is not clean

  Scenario: A wave nobody measured the instruction for is unmeasured, not clean
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    When the wave shape is decided
    Then the wave reports "landing-order" as unmeasured
    And the plan is not clean

  # The population this check reads is the flow artifacts on disk, which is what
  # an agent is handed. A project that has never scaffolded a flow has none, and
  # a pass over nothing is a pass that cannot fail — so the verdict says how many
  # artifacts it read, the way `role-duties` counts the adapters it found.

  Scenario: A verdict over no artifact at all says so rather than passing quietly
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the shared media were measured and are clean
    And no flow artifact instructs the landing lock at all
    When the wave shape is decided
    Then the wave reports "landing-order" as passed
    And the landing-order verdict states that it read no instruction
