# BDL-083 S2g, beadloom-89gm (BDL-UX #354; RFC D12).
#
# Reported 2026-10-19 from the first outside adopter's second clone. The agent followed
# the composed landing instruction literally — acquire before the commit, release after —
# and pushed between the commit and the release. The export inside the pushed commit
# held the slot for the bead it landed, the merge request merged that commit, and the
# trunk exported the slot as held by a closed bead: the next clone's `acquire` was
# refused with `Slot held by: <bead>`, and the release made after the push reached no
# merged commit.

@bead:beadloom-89gm @node:cli-commands
Feature: a push does not land the hold of the bead it lands

  The slot is tracker state, exported into `.beads/issues.jsonl`, so what the trunk says
  about it is what the last landed export says. The pre-push hook reads the export at the
  commit being pushed and the `Bead:` trailers of the commits the push carries, and
  refuses a push whose export still holds the slot for one of those beads, naming the
  sequence that lands the release with the work.

  Scenario: a push whose export holds the slot for the bead it lands is refused with the sequence
    Given a repository with the composed hooks installed
    And a commit bound to "rig-1" whose export holds the merge slot for "rig-1"
    When the pre-push hook runs for that commit with beadloom on its PATH
    Then the hook exits non-zero
    And the hook names the sequence acquire, commit, release, export, push
    And the hook names the release "bd merge-slot release --holder rig-1"
    And the Gate did not run

  Scenario: the same push after the release is exported and landed goes on to the Gate
    Given a repository with the composed hooks installed
    And a commit bound to "rig-1" whose export shows the merge slot free
    When the pre-push hook runs for that commit with beadloom on its PATH
    Then the hook says the landing lock is clean
    And the Gate ran

  Scenario: a hold by a bead the push does not carry is named and does not refuse it
    Given a repository with the composed hooks installed
    And a commit bound to "rig-1" whose export holds the merge slot for "rig-2"
    When the pre-push hook runs for that commit with beadloom on its PATH
    Then the hook says the landing lock is clean
    And the hook names "rig-2" as the holder
