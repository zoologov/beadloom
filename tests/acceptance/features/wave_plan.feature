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

  # BDL-061.80. Naming the media was the whole of the second clause until `.22`
  # measured that nothing checked any of them. The three scenarios below are the
  # difference between a wave that STATES what it shares and one that also says
  # whether the sharing is currently safe.

  @bead:beadloom-mr2l.80
  Scenario: Every medium a wave names is also checked
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the shared media were measured and are clean
    When the wave shape is decided
    Then every medium the wave names carries a verdict of its own
    And the plan is clean

  @bead:beadloom-mr2l.80
  Scenario: A concurrent wave whose shared media nobody measured is not reported clean
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    When the wave shape is decided
    Then the wave reports "working-tree" as unmeasured
    And the plan is not clean

  @bead:beadloom-mr2l.80
  Scenario: A bead whose title numbers it differently from its allocated id is reported
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping" titled "[BDL-061.39] the other bead"
    And the shared media were measured and are clean
    When the wave shape is decided
    Then the wave reports "tracker-ids" as failed
    And the plan is not clean

  # BDL-061.83. The parser the whole decision rests on failed toward MORE
  # parallelism: a `refs:` written inside a sentence adopted the next word as a
  # real scope, and a second ref written without a comma was dropped. Both made
  # two beads MORE likely to share a wave, which is the direction that costs.

  @bead:beadloom-mr2l.83
  Scenario: A bead that only mentions refs in a sentence is unresolved, not scoped
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "essay" that mentions "billing" in a sentence about declarations
    When the wave shape is decided
    Then "alpha" and "essay" are in different waves
    And the decision names "unresolved_scope" for "essay"

  @bead:beadloom-mr2l.83
  Scenario: A second ref the parser had to drop is named rather than silently lost
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "terse" declaring the node scopes "shipping billing" without a comma
    When the wave shape is decided
    Then "alpha" and "terse" are in different waves
    And the decision names "unresolved_scope" for "terse"
    And the plan is not clean
