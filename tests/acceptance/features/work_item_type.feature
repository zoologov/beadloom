# BDL-068 S1.5. The type of a work item is a claim about how far the change
# ranges, and until now nothing checked it. Measured at 2a5c0d1 with
# `beadloom docs quality`: "BRIEF documents do not carry Axes (0/12)" and "RFC
# documents do not carry Axes (0/48)" -- .4's missing-section is peer-relative
# by design, so a section no peer keeps produces a kind-level statement and no
# document-level finding at all. A work item could be routed `bug` with no axes
# and the flow said nothing, which is what happened to BDL-067.

@bead:beadloom-0mdo.5 @node:work-item-type
Feature: the type a work item was routed as is checked against the axes it was decided from

  The simplified flow writes one BRIEF and no RFC, so it passes no approval
  gate at which a mis-route would meet a human. `beadloom impact
  src/beadloom/onboarding/scanner/bootstrap.py --section` -- BDL-067's own
  target -- keeps rows naming four graph nodes, and BDL-067 was routed `bug`.
  A change ranging over more than one node has no document in the simplified
  flow that records the crossing.

  Scenario: A simplified work item with no axes shows nothing the type was decided from
    Given a work item routed through the simplified flow with no Axes section
    When the work item's type is checked against its axes
    Then the work item is reported as routed without axes

  Scenario: Axes crossing more than one node do not support a simplified route
    Given a work item routed through the simplified flow whose axes keep two nodes
    When the work item's type is checked against its axes
    Then the work item is reported as routed past what its axes support
    And the finding names both nodes

  Scenario: A simplified work item whose axes stay in one node is silent
    Given a work item routed through the simplified flow whose axes keep one node
    When the work item's type is checked against its axes
    Then the work item is not reported

  Scenario: A work item routed through the full flow is judged by its approvals
    Given a work item routed through the full flow with no Axes section
    When the work item's type is checked against its axes
    Then the work item is not reported

  Scenario: The route the check polices is the one /task-init declares
    Given the composed task-init command
    When the work-item routing is derived from it
    Then a bug is routed through the simplified flow
    And an epic is routed through the full flow
    And the simplified flow's documents include the BRIEF

  Scenario: The type decision cannot be reached before the explore step
    Given the composed task-init command
    Then the explore step is stated before the type decision
    And the explore step names the Explore role
