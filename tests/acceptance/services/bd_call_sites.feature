# BDL-068 S5, CONTEXT Q4: "External bd findings are answered by deriving our own
# call sites and asserting what each assumes about the answer, not by a wrapper."
# A wrapper is a second thing to keep in step with upstream; a derived population
# fails on a call site added later.
#
# Every verdict below is measured against ONE release of bd, and the report says
# which. Three premises this slice inherited were re-measured and destroyed:
# BDL-UX #194 and #237 (merge-slot grants no exclusion — it does) and
# beadloom-l2f2's (`bd import -i` does not exist — it does, as a documented legacy
# alias). A FOURTH withdrawal, of #97, was made here and was WRONG, which is why
# the version pin exists in both directions: a verdict carried across a release
# without re-measuring, and a withdrawal taken on one dependency shape, fail the
# same way.

@bead:beadloom-0mdo.51 @node:bd-seam
Feature: every place this project reaches bd is derived, and each one's assumption about the answer is stated

  # `bd list` carries TWO default filters and announces exactly one of them.
  # Measured on bd 1.0.4 against this repository's tracker: `--limit 0` alone
  # returns 55 rows of 842 with both streams silent, while the 50-row cap does
  # print a notice — on stderr, where a consumer that merged its streams has
  # already destroyed its own JSON.

  Scenario: A list that names no filter is unsecured on the population it received
    Given an instruction artifact carrying "bd list --json"
    When the bd call sites are derived
    Then the site assumes "complete-population" and the assumption is "unsecured"
    And the site assumes "untruncated-population" and the assumption is "unsecured"

  Scenario: A list that names its status is secured on the population and still capped
    Given an instruction artifact carrying "bd list --status open --json"
    When the bd call sites are derived
    Then the site assumes "complete-population" and the assumption is "secured"
    And the site assumes "untruncated-population" and the assumption is "unsecured"

  Scenario: The override that lifts both defaults secures both assumptions
    Given an instruction artifact carrying "bd list --all --json"
    When the bd call sites are derived
    Then the site assumes "complete-population" and the assumption is "secured"
    And the site assumes "untruncated-population" and the assumption is "secured"

  Scenario: A ready that names no limit is unsecured, because its cap is a different number
    Given an instruction artifact carrying "bd ready"
    When the bd call sites are derived
    Then the site assumes "untruncated-population" and the assumption is "unsecured"

  Scenario: A create that does not read the id back is unsecured on the id it allocated
    Given an instruction artifact carrying "bd create 'a title' --type task"
    When the bd call sites are derived
    Then the site assumes "allocated-id" and the assumption is "unsecured"

  Scenario: A create that asks for the allocated id is secured
    Given an instruction artifact carrying "bd create 'a title' --type task --json"
    When the bd call sites are derived
    Then the site assumes "allocated-id" and the assumption is "secured"

  # `beadloom-l2f2` records `bd import -i` as a flag that does not exist. It does:
  # upstream's help calls it a legacy alias for a named file, and it imported 137
  # issues at exit 0. Nothing at the call site can secure an alias upstream may
  # retire, so the verdict is a third one — true, and pinned to a release.

  Scenario: An assumption measured true is reported as holding, not as clean
    Given an instruction artifact carrying "bd import -i backup.jsonl"
    When the bd call sites are derived
    Then the site assumes "legacy-alias" and the assumption is "holds"
    And the assumption names the bd version it was measured against

  # BDL-UX #97 stands, and this scenario exists because it was WITHDRAWN here on a
  # measurement that was true and one-shaped. `--suggest-next` was silent while the
  # target was blocked and spoke when it became ready — both directions of the
  # outcome, one dependency shape. Over ten shapes it lies in four, and it is
  # silent in every shape where exactly ONE blocker had been closed, which is the
  # cell that first measurement picked. No flag settles it; `bd ready` does.

  Scenario: An assumption no measurement supports is unsecured, whatever its subject
    Given an instruction artifact carrying "bd close <id> --suggest-next"
    When the bd call sites are derived
    Then the site assumes "unblocked-is-ready" and the assumption is "unsecured"

  # BDL-UX #171. bd 1.0.4 offers no `--expect-title`, so nothing at the call site
  # can check that the ids passed name the beads intended. That reads differently
  # from an assumption measured true.

  Scenario: An assumption no call form can secure is unsecured rather than holding
    Given an instruction artifact carrying "bd dep add child parent"
    When the bd call sites are derived
    Then the site assumes "intended-id" and the assumption is "unsecured"

  Scenario: A subcommand this derivation has not measured is unmeasured, not clean
    Given an instruction artifact carrying "bd quickstart"
    When the bd call sites are derived
    Then the site assumes "unmeasured-subcommand" and the assumption is "unmeasured"

  # The Python channel reads argv from the source rather than from a spelling, so
  # a constant resolves and a runtime value does not hide the subcommand it
  # belongs to.

  Scenario: A python call site is read from its argv, and a name that resolves is resolved
    Given a python module invoking run_bd with argv from a module constant
    When the bd call sites are derived
    Then the site assumes "complete-population" and the assumption is "secured"

  Scenario: An argument the derivation cannot resolve does not hide the subcommand
    Given a python module invoking run_bd with a runtime bead id
    When the bd call sites are derived
    Then the subcommand is still reported as "close"
    And the site records that it carries an argument the derivation could not resolve

  Scenario: A region the sweep did not reach is named rather than omitted
    Given an instruction artifact carrying "bd list --json"
    And a region the sweep cannot reach
    When the bd call sites are derived
    Then the report names the region it could not reach
    And the report names the bd version every verdict was measured against
