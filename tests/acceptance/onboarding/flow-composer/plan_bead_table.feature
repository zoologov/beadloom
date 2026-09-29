# BDL-075 T1. The PLAN template's bead table carried a Status column that nothing
# reconciled, so it went stale within a few waves: BDL-074's PLAN showed every
# bead Pending while fifteen were done. ACTIVE.md is the copy the pre-commit
# active-sync reconciles from the tracker, and two copies of one fact diverge.
# The table names the plan and the tracker id instead; the status lives in one
# place.
#
# Bound to `flow-composer` for the reason `axes_ruling.feature` gives: the steps
# run `compose`, and `onboarding` owns template text, which is read and not run.

@bead:beadloom-10er @node:flow-composer
Feature: a plan's bead table names the tracker id and leaves the status to the focus document

  Scenario: The PLAN skeleton carries a tracker column and no status column
    Given the templates command composed for a ddd python project
    Then the PLAN skeleton's bead table has a "Tracker" column
    And the PLAN skeleton's bead table has no "Status" column
    And the PLAN skeleton says the status lives in ACTIVE.md, reconciled from the tracker

  Scenario: The step that creates the beads fills the tracker column
    Given the task-init command composed for a ddd python project
    Then the step that creates the beads says to fill the PLAN's Tracker column
