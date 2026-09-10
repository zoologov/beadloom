# Who owns what the Gate found (BDL-068 S6, offered by beadloom-0mdo.76).
# One Feature per file.

@bead:beadloom-0mdo.78 @node:ci-gate
Feature: a gate finding names its owner

  This branch carried a red Gate across two waves of S6 — two stale docs owned
  by no bead in the running plan — and every gate owner in those waves had to
  be told by the coordinator, by hand, that the red was not theirs, so their
  reports would attribute the finding rather than discount it. A red everyone
  learns to ignore is the shape this project has now measured three times, and
  here it arrived on the instrument rather than in the suite.

  So a finding names its owner: the graph node it is about, held against the
  beads the tracker reports claimed right now and the scope each of them
  declares. The other two candidate populations lose for stated reasons. The
  work item's axes answer whether a change is inside the approval, which
  `scope-check` already asks as a step of this same run, and which every agent
  on one branch shares. A wave's plan names beads that have not started and
  beads whose wave is over, and says what should run rather than what is
  running.

  Nothing here changes the verdict. A finding nobody claims is still a finding,
  and a gate that goes green because no bead owns a red would be the false
  green this epic exists to remove.

  Scenario: a finding a claimed bead declares names that bead
    Given a project whose gate finds a fault in a node
    And a bead is claimed that declares that node
    When the gate reports on that project
    Then the report names the claimed bead as the owner of that finding

  Scenario: a finding no claimed bead declares is unowned rather than blank
    Given a project whose gate finds a fault in a node
    And a bead is claimed that declares a different node
    When the gate reports on that project
    Then the report calls that finding unowned
    And it says no bead claimed now declares the node that owns it

  Scenario: a finding no node can be derived from is unattributed, not unowned
    Given a project whose gate finds a fault with no node and no path
    And a bead is claimed that declares a different node
    When the gate reports on that project
    Then the report calls that finding unattributed
    And it does not call that finding unowned

  Scenario: a tracker that cannot answer is a reason, never an absence of owners
    Given a project whose gate finds a fault in a node
    And the work tracker cannot be reached
    When the gate reports on that project
    Then the report states that the claim could not be read
    And it attributes no finding to any bead

  Scenario: naming the owner of a finding does not change the verdict
    Given a project whose gate finds a fault in a node
    And a bead is claimed that declares a different node
    When the gate reports on that project
    Then the verdict and the exit code are the ones the steps produced
