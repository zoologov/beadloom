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

  So a finding names its owner. The rule it is attributed by changed in BDL-083
  S1c (BDL-UX #329): a claimed bead owns a finding when its commits changed the
  finding's files, never because its `refs:` name a node that covers them, and
  the scenarios of that rule live in
  `application/gate-ownership/ownership_by_changed_files.feature`. What stays
  here is what the rule change did not touch: a tracker that cannot answer, and
  a verdict that ownership never changes.

  Nothing here changes the verdict. A finding nobody claims is still a finding,
  and a gate that goes green because no bead owns a red would be the false
  green this epic exists to remove.

  Scenario: a tracker that cannot answer is a reason, never an absence of owners
    Given a project whose gate finds a fault in a node
    And the work tracker cannot be reached
    When the gate reports on that project
    Then the report states that the claim could not be read
    And it attributes no finding to any bead

  Scenario: naming the owner of a finding does not change the verdict
    Given a project whose gate finds a fault in a node
    And a bead is claimed
    When the gate reports on that project
    Then the verdict and the exit code are the ones the steps produced
