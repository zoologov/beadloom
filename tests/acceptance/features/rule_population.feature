# BDL-061 bead `.63`, measured by `.14`. The population is honest today and that
# was measured, not asserted: the shipped rule selects `kind: feature` and all 37
# declared feature nodes are in it. The hole is that the population is defined by
# KIND, and a node's kind is one line in `services.yml` — changing `feature` to
# `component` removes a node from the rule with no finding of any sort, and the
# run stays the same colour.
#
# Widening the rule to components is NOT the fix: excluding plumbing is the
# architecture model's own definition, and it would add 24 findings without a
# decision having been taken. The fix is that leaving the population is VISIBLE —
# the denominator is stated in the same breath as the fraction, so a shrinking
# denominator cannot hide behind an improving one. This is `.77`'s shape: a node
# the rule cannot reach is counted and reported rather than dropped.

@bead:beadloom-mr2l.63 @node:rule-engine
Feature: a rule states the population its coverage fraction is taken from

  Scenario: The nodes the population leaves out are counted beside the fraction
    Given a graph with 2 feature nodes and 3 component nodes
    When the scenario-coverage rule is evaluated
    Then the run states that 2 of 5 graph nodes are in the rule's population
    And it names the kind the 3 nodes outside the population left by

  Scenario: Reclassifying a feature as a component moves the stated population
    Given a graph with 2 feature nodes and 3 component nodes
    And one feature node is reclassified as a component
    When the scenario-coverage rule is evaluated
    Then the run states that 1 of 5 graph nodes are in the rule's population

  Scenario: A rule that leaves no node out says nothing about its population
    Given a graph with 2 feature nodes and 0 component nodes
    When the scenario-coverage rule is evaluated
    Then the run makes no statement about nodes outside the population
