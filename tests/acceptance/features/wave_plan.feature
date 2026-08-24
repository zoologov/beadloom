# The S6 acceptance suite (BDL-061). A wave shape is DECIDED from the code-level
# independence of the beads' node scopes, never advised — an advisory wave shape
# is the same failure this epic exists to remove.
#
# The scenarios below state the guarantee in two halves, because this session's
# own evidence says one half is not enough. Code independence is the first half
# (BDL-UX #155 A). The second is that a wave shares media the code graph knows
# nothing about — the working tree, the commit gate, the doc baseline and the
# tracker's id space — and each of those has already carried one bead's state
# into another's result (#181, #118, #133/#182, #171).

@bead:beadloom-mr2l.21 @node:wave-plan
Feature: a wave shape is decided from the graph, and says what it does not decide

  Scenario: Two beads touching independent subgraphs are allowed to run in parallel
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    When the wave shape is decided
    Then "alpha" and "beta" are in the same wave

  Scenario: Two beads touching the same node are serialised
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "gamma" declaring the node scope "billing"
    When the wave shape is decided
    Then "alpha" and "gamma" are in different waves
    And the decision names "shared_node" over "billing"

  Scenario: A bead that declares no node scope is serialised against every bead
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "mute" declaring no node scope at all
    When the wave shape is decided
    Then "alpha" and "mute" are in different waves
    And the decision names "unresolved_scope" for "mute"

  Scenario: A declared node the graph does not have is unresolved, not empty
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "ghost" declaring the node scope "nowhere"
    When the wave shape is decided
    Then "alpha" and "ghost" are in different waves
    And the decision names "unresolved_scope" for "ghost"

  Scenario: A human override forcing parallelism is recorded with its reason and exit condition
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "gamma" declaring the node scope "billing"
    And an override placing "alpha" and "gamma" in parallel with a reason and an exit condition
    When the wave shape is decided
    Then "alpha" and "gamma" are in the same wave
    And the override reports that it changed 1 decision

  Scenario: An override that changes no decision is reported as inert
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And an override placing "alpha" and "beta" in parallel with a reason and an exit condition
    When the wave shape is decided
    Then the override is reported as inert

  Scenario: A wave of more than one bead names the media it did not make independent
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    When the wave shape is decided
    Then the wave names the working tree, the commit gate, the doc baseline and the tracker id space
    And exactly one bead of the wave owns the combined-tree result
