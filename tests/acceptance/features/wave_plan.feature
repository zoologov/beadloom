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
    And the work item keeps "billing" and "shipping" in scope
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

  # BDL-UX #228 / beadloom-67t1. Stating the media only for a wave of MORE THAN
  # ONE bead made the instrument speak exactly where the coordinator was already
  # thinking about concurrency and stay silent where it was not: roughly twenty
  # single-bead waves across two epics carried the rule by prompt alone. A wave
  # of one is not solitude -- `_check_working_tree` reports paths owned by no
  # bead in the plan, which is the module already knowing that work outside the
  # plan lands in the same tree.

  @bead:beadloom-67t1
  Scenario: A wave of one bead names the same media and the room its bead owes
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "billing"
    And the shared media were measured and are clean
    When the wave shape is decided
    Then no wave holds more than one bead
    And the wave names the working tree, the commit gate, the doc baseline and the tracker id space
    And every bead is told the clean room it owes, named after its own id
    And exactly one bead of the wave owns the combined-tree result
    And every medium the wave names carries a verdict of its own

  # BDL-UX #232 / beadloom-en0x. The scope every verdict above rests on was a
  # line the bead's AUTHOR wrote, while everything else BDL-068 built is
  # derived. Measured: `beadloom-0mdo.21` and `beadloom-0mdo.26` both edited
  # `docs/services/cli.md`, neither declaration named the node that owns it,
  # and the plan reported 1 wave, 2 beads, 0 findings. CONTEXT Q1 decides the
  # direction — the declaration is COMPARED against the recorded derivation and
  # the gap is reported — and CONTEXT Q2 decides the unit: the WORK ITEM's
  # axes, never the bead's, because a bead may narrow freely inside them.

  @bead:beadloom-en0x
  Scenario: A node the work item approves that no bead of a wave declares is reported
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the work item keeps "billing", "shipping" and "invoicing" in scope
    And the shared media were measured and are clean
    When the wave shape is decided
    Then "alpha" and "beta" are in the same wave
    And the plan reports "invoicing" as declared by no bead of that wave
    And the plan is not clean

  @bead:beadloom-en0x
  Scenario: A wave whose beads together declare every approved node reports no gap
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the work item keeps "billing" and "shipping" in scope
    And the shared media were measured and are clean
    When the wave shape is decided
    Then the plan is clean

  @bead:beadloom-en0x
  Scenario: A bead declaring a node the work item ruled out of scope is a finding
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the work item keeps "billing" in scope and rules "shipping" out
    And the shared media were measured and are clean
    When the wave shape is decided
    Then the plan reports "beta" declaring "shipping" outside the approved axes
    And the plan is not clean

  # A derivation this project has MEASURED to under-report (BDL-UX #225: no node
  # was attributed to any of 148 caller sites under `tests/`). So a declared ref
  # the table never names is the derivation not reaching, which is a different
  # answer from the declaration being wrong, and only one of them is a finding.

  @bead:beadloom-en0x
  Scenario: A declared node the derivation never reached is not reported as a wrong declaration
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the work item keeps "billing" in scope
    And the shared media were measured and are clean
    When the wave shape is decided
    Then the plan states "shipping" as a node the derivation did not reach
    And the plan reports no finding against "beta" for declaring it

  # `beadloom-0mdo.32` measured this branch's own eleven commits: 52 paths, 11
  # with an owning node and 41 with none. Four paths in five could not be
  # compared at all. The axes table has the same shape — a row the derivation
  # found and attributed to no node — and it is `not compared`, never `agrees`.

  @bead:beadloom-en0x
  Scenario: An axis row attributing no node is stated as compared against nothing
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the work item keeps "billing" and "shipping" in scope
    And the work item records an axis "co-writers" that names no node
    And the shared media were measured and are clean
    When the wave shape is decided
    Then the plan states the axis "co-writers" as compared against nothing
    And the plan is clean

  @bead:beadloom-en0x
  Scenario: A concurrent wave whose declarations were compared against nothing says so
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "beta" declaring the node scope "shipping"
    And the shared media were measured and are clean
    When the wave shape is decided
    Then the plan states that it compared the declarations against no derivation
    And the plan is not clean

  # BDL-UX #234 / beadloom-en0x. The reason already tells four causes apart; the
  # printed remedy did not follow it that far. `beadloom-nn4c` declares no scope
  # ON PURPOSE and its note explains in prose why writing one would be
  # dishonest. The parser matched the `refs:` inside that explanation, serialised
  # correctly, and then printed "move the declaration to the start of its own
  # line" over a bead with no declaration to move — following which would have
  # authored exactly the scope #232 is filed against.

  @bead:beadloom-en0x
  Scenario: The remedy for a refs token inside prose states both causes rather than choosing one
    Given a bead "alpha" declaring the node scope "billing"
    And a bead "essay" that mentions "billing" in a sentence about declarations
    When the wave shape is decided
    Then the remedy for "essay" says this check cannot tell the two apart
    And the remedy for "essay" states the prose case as well as the declaration case

  @bead:beadloom-en0x
  Scenario: A bead that declares nothing where the work item records axes is sent to the document
    Given a bead "mute" declaring no node scope at all
    And the work item keeps "billing" and "shipping" in scope
    When the wave shape is decided
    Then the remedy for "mute" names the document the axes were read from
