# BDL-068 S5, BDL-UX #187 and #97. Two of bd's answers cover a population that is
# not the population the question asked for, and the answer has no room to say so.
# `bd list` returns less than the tracker: two default filters, of which bd
# announces exactly one, on stderr. `bd close --suggest-next` returns MORE than
# the question — it names beads for which the closed issue was A blocker, without
# checking whether others remain.
#
# CONTEXT Q4 decides the shape of the fix: our call sites state which population
# they received, and no wrapper is placed in front of bd. So the module these
# scenarios drive reads bd's OWN output — the notice bd prints, the ids bd names —
# and never re-implements a decision bd makes.
#
# Measured on bd 1.0.4 (ce242a879). Eighteen dependency shapes, each in its own
# `bd init` rig: `--suggest-next` named a still-blocked bead in thirteen of them
# and `bd ready` was correct in all eighteen. Which of the two is authoritative is
# therefore a measurement, and `BD_MEASURED_VERSION` is what makes a later bd that
# fixes it fail loudly rather than leave this guarding nothing.

@bead:beadloom-0mdo.52 @node:bd-seam
Feature: an answer from the tracker states the population it covers, and cannot be read as the whole

  # bd announces the 50-row cap on stderr and says nothing at all about the status
  # filter. A consumer that reads only stdout is told nothing in either case, so
  # the population a listing covers is read from the call form AND from bd's own
  # notice, and the two disagreeing is the answer being narrower than it looks.

  Scenario: A listing that arrived truncated is stated as truncated, not returned as the whole
    Given a listing asked for with "list --all --json"
    And bd announced "Showing 50 issues; use --limit 0 for all" on stderr
    When the answer's population is read
    Then the answer covers "truncated"
    And the answer states how many rows bd said it withheld

  Scenario: A listing whose call form named its population and went unnoticed covers what it asked for
    Given a listing asked for with "list --all --json"
    And bd announced nothing on stderr
    When the answer's population is read
    Then the answer covers "as-asked"
    And the answer does not claim to cover the tracker

  Scenario: A listing whose call form named no population is filtered, however quiet bd was
    Given a listing asked for with "list --json"
    And bd announced nothing on stderr
    When the answer's population is read
    Then the answer covers "filtered"
    And the answer names the flag that would have widened it

  # An unmeasured subcommand must never read as a clean one. This is the same
  # distinction `beadloom-0mdo.32` shipped for unowned paths and `.42` for an
  # empty typed surface, applied to the tracker's answers.

  Scenario: A subcommand whose population this derivation has not measured is unchecked, not complete
    Given a listing asked for with "swarm status --json"
    And bd announced nothing on stderr
    When the answer's population is read
    Then the answer covers "unchecked"

  # BDL-UX #97. `bd ready` is the confirmation the flow's own instruction names,
  # and it was correct in all eighteen shapes measured.

  Scenario: A suggestion naming a bead the tracker does not call ready is reported as still blocked
    Given bd suggested "rig-a" and "rig-b" as newly unblocked
    And the tracker's ready list holds "rig-a"
    When the suggestion is confirmed against the ready list
    Then the confirmed beads are "rig-a"
    And the still-blocked beads are "rig-b"
    And the suggestion is not readable as a list of ready beads

  Scenario: A suggestion nobody could confirm is not compared, never a clean pass
    Given bd suggested "rig-a" and "rig-b" as newly unblocked
    And the tracker's ready list could not be read
    When the suggestion is confirmed against the ready list
    Then the suggestion reads "not compared"
    And no bead is reported as confirmed

  Scenario: A close that suggested nothing has nothing to check, which is not a clean pass
    Given bd suggested no bead as newly unblocked
    And the tracker's ready list holds "rig-a"
    When the suggestion is confirmed against the ready list
    Then the suggestion reads "nothing to check"

  # The derivation learns the securing shape, so the fix is visible to the report
  # that found the defect. An artifact is what a subagent reads: a role core is
  # read on its own, and the mitigation living in CLAUDE.md does not reach it.

  Scenario: An artifact instructing the suggestion and naming its confirmation nowhere is unsecured
    Given an artifact instructing "bd close <id> --suggest-next" and nothing else
    When the bd call sites are derived over the artifact
    Then the close site assumes "unblocked-is-ready" and the assumption is "unsecured"

  Scenario: An artifact that also names the confirmation secures the suggestion
    Given an artifact instructing "bd close <id> --suggest-next" and "bd ready --limit 0"
    When the bd call sites are derived over the artifact
    Then the close site assumes "unblocked-is-ready" and the assumption is "secured"
    And the verdict says what a derivation of call forms cannot see
