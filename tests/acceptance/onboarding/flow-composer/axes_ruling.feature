# BDL-UX #284. Measured across one epic: three axis rows were ruled out of scope
# as blast radius and turned out to be work sites, and every re-ruling moved the
# same way. The ruling read each node by the axis it FIRST surfaced under -- a
# `callers` row read as "calls into the change, is not changed" -- while the
# axis is the node's relation to the seed and says nothing about its role in the
# fix. The guidance belongs where the person rules the rows, in the shipped
# sources the flow is composed from, not in one project's composed copy.
#
# Bound to `flow-composer`, not `onboarding` (BDL-074 F3, `beadloom-2mj3.8`).
# Measured under coverage on 2026-09-28: the three scenarios run no line of a
# module `onboarding` owns itself. What they run is `compose` (flow-composer, all
# three) and, in the third, `compose_role` (role-composer). `onboarding` owns the
# template TEXT the guidance is written in, and a template is read, not executed.

@bead:beadloom-rqma.2 @node:flow-composer
Feature: a person rules an axis row by the node's role in the change, not by the axis it surfaced under

  Scenario: The step where the rows are ruled says an axis is not a role
    Given the task-init command composed for a ddd python project
    Then the step that rules the axis rows says the axis a node surfaced under is not its role
    And that step says a callers row can be a work site
    And that step points at the column naming what the node owns and was not read

  Scenario: Every Axes skeleton says it where the table is filled in
    Given the templates command composed for a ddd python project
    Then every Axes skeleton says the axis a node surfaced under is not its role
    And every Axes skeleton carries the column naming what the node owns and was not read

  @node:role-composer
  Scenario: The Explore role returns the column with the section
    Given the Explore role composed for a ddd python project
    Then its deliverable table carries the column naming what the node owns and was not read
    And it says the axis a node surfaced under is not its role
