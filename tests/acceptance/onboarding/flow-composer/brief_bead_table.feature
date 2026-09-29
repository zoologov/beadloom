# BDL-075, beadloom-3nwz. The same defect `plan_bead_table.feature` pins, in the
# simplified flow: the BRIEF skeleton's bead table carried a Status column that
# nothing reconciled, a second copy of what ACTIVE.md holds and the pre-commit
# active-sync keeps current. A bug, task or chore BRIEF names its beads by
# tracker id and leaves the status to ACTIVE.md.
#
# Bound to `flow-composer` for the reason `axes_ruling.feature` gives: the steps
# run `compose`, and `onboarding` owns template text, which is read and not run.

@bead:beadloom-3nwz @node:flow-composer
Feature: a brief's bead table names the tracker id and leaves the status to the focus document

  Scenario: The BRIEF skeleton carries a tracker column and no status column
    Given the templates command composed for a ddd python project
    Then the BRIEF skeleton's bead table has a "Tracker" column
    And the BRIEF skeleton's bead table has no "Status" column
    And the BRIEF skeleton says the status lives in ACTIVE.md, reconciled from the tracker

  Scenario: The simplified flow's step that creates the beads fills the tracker column
    Given the task-init command composed for a ddd python project
    Then the simplified flow's step that creates the beads says to fill the BRIEF's Tracker column
