# BDL-069 acceptance (`beadloom-956f`). US-1's two criteria, under the names the
# PRD references them by, measured where the PRD says they have to be measured:
# on a WHEEL BUILT FROM THIS TREE, installed into an interpreter of its own, run
# against projects that are not this repository.
#
# Sixteen dev beads each verified their own change, and every one of those
# verdicts was taken by importing `beadloom` out of the working tree. That is a
# claim about the tree. The artifact an adopter installs is a wheel, and the two
# defects this epic exists for were both found on one — BDL-UX #282 and #214,
# measured on the published 4.0.0 against `myapp`/`src/ledger/`+`src/billing/`
# and `myapp`/`src/myapp/`. Both layouts are ordinary and neither exists here:
# `src/beadloom/` holds seven packages and none of them is named `beadloom`.
#
# MEASURED on 2026-09-12, the same two projects under both artifacts:
#
#   published 4.0.0   init rc 0 "Graph: 3 nodes"   ci rc 1  "6 stale doc(s)"
#   this tree         init rc 0 "Graph: 3 nodes"   ci rc 0  "6 pair(s) fresh"
#
#   published 4.0.0   init rc 0 "Graph: 2 nodes"   status "Nodes: 1"
#   this tree         init rc 0 "Graph: 2 nodes"   status "Nodes: 2"
#
# The scenarios below are the second row of each pair. The first row is the
# contrast and is not a scenario: asserting it would pin this suite to a
# published artifact and a network, and it would go green for the wrong reason
# the day that release is yanked.
#
# The wheel is built once per session. If it cannot be built — no `uv`, no
# manifest, an offline index — every scenario here SKIPS with that reason
# printed, because a suite that cannot reach the artifact has measured nothing
# and must not read as having measured it.

@bead:beadloom-956f
Feature: the first two commands an adopter runs, measured on the built artifact

  @node:ci-gate
  Scenario: A virgin init on a multi-package layout is followed by a green gate
    Given a wheel built from this tree, installed into an interpreter of its own
    And a git repository holding two Python packages under src, which is not this repository
    When the installed beadloom initialises it in bootstrap mode without prompts
    And the installed beadloom runs its gate on the repository
    Then the gate exits 0
    And nothing in the repository was edited between the two commands
    And the gate's freshness leg names the pairs it found fresh
    And the beadloom that ran is the installed wheel and not this working tree

  @node:onboarding
  Scenario: A virgin init on a single-package layout keeps every node it reported writing
    Given a wheel built from this tree, installed into an interpreter of its own
    And a git repository whose only Python package is named after it, which is not this repository
    When the installed beadloom initialises it in bootstrap mode without prompts
    And the installed beadloom reports the project's status
    Then the status counts every node the initialisation reported writing
    And the node carrying the package's source is one of them
    And the gate over that project exits 0
