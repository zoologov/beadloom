# The acceptance suite Beadloom holds ITSELF to (BDL-061 S4).
#
# These scenarios are the source of truth for what `scenario-coverage` promises;
# PLAN's "Done when" list references them by name. They RUN — a `.feature` file
# that nothing executes is prose, and the whole decision this slice rests on is
# that an executable artifact cannot silently lie.

@bead:beadloom-mr2l.13 @node:rule-engine
Feature: behaviour that carries no executable claim is reported

  A team adopting the flow states its acceptance criteria as scenarios. The
  question the rule answers is which behaviour has none, and which scenario
  claims something nobody can trace back to a piece of work.

  Scenario: a behaviour-bearing node with no scenario is reported
    Given a graph with the feature nodes "billing" and "shipping"
    And an acceptance suite whose only scenario is tagged "@node:billing"
    When the scenario-coverage rule is evaluated
    Then "shipping" is reported as carrying no scenario
    And "billing" is not reported

  Scenario: a scenario naming no bead is reported
    Given a graph with the feature node "billing"
    And an acceptance suite whose only scenario is tagged "@node:billing"
    When the scenario-coverage rule is evaluated
    Then the scenario is reported as naming no bead

  Scenario: a scenario naming a node outside the graph is reported
    Given a graph with the feature node "billing"
    And an acceptance suite whose only scenario is tagged "@node:billing @node:invoicing"
    When the scenario-coverage rule is evaluated
    Then "invoicing" is reported as not being a node in the graph

  Scenario: a node declared non-behavioural with a reason is accepted
    Given a graph with the feature nodes "billing" and "shipping"
    And an acceptance suite whose only scenario is tagged "@node:billing @bead:proj-1"
    And "shipping" is declared non-behavioural because "it is a vocabulary module"
    When the scenario-coverage rule is evaluated
    Then nothing is reported

  Scenario: a rule that cannot see a suite reports itself
    Given a graph with the feature nodes "billing" and "shipping"
    And no acceptance suite at all
    When the scenario-coverage rule is evaluated
    Then the rule reports that it could not fire
    And no node is reported as carrying no scenario
