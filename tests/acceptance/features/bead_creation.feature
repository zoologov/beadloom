# BDL-068 S5, BDL-UX #171 and #165. The bead-creation path, where this project kept
# one number in two places and paid one process per bead.
#
# #171 is a defect of OUR convention and not of bd's allocator: a bead's number is
# AUTHORED before creation and ALLOCATED at creation, so under a concurrent wave the
# two diverge, and the damage is the wiring rather than the cosmetics — a `bd dep add`
# built from an authored id is a real, valid, wrong edge that nothing can reject.
#
# #165 is one process per bead against embedded Dolt.
#
# Measured on bd 1.0.4 (ce242a879), in isolated `bd init` rigs, streams read separately
# and exit codes read without a pipe. A 60-bead DAG with 59 edges cost 34.25 s over 60
# `bd create` processes plus 35.20 s over 59 `bd dep add` processes, against 1.15 s in
# one `bd create --graph` process — a factor of 60. Four `bd create --parent` launched
# simultaneously took `.1` to `.4` out of launch order, while a `bd create --graph` run
# racing them returned four FLAT ids and consumed no number from that sequence.
#
# So the plan form closes #171 for the path it covers, for two independent reasons:
# it allocates no positional number to disagree with, and its edges name plan-local
# KEYS, so no id is ever authored. It closes nothing for `bd create --parent`, which
# is how every per-slice bead of this epic is created.
#
# And one measurement decides the guidance: `bd dep add` echoes BOTH TITLES, which is
# the only reason #171 was caught in seconds, while `bd dep add --file` — the bulk form
# a reader of #165 reaches for next — prints `✓ Added 2 dependencies` and no titles at
# all. The fast form of the WIRING half destroys the check; the fast form of the
# CREATION half removes the need for it.

@bead:beadloom-0mdo.53 @node:bd-seam
Feature: a bead's id comes from the tracker's answer, never from a number we authored

  # The plan is the artifact that makes an authored id impossible rather than
  # discouraged: an edge names two keys the author chose, and the tracker maps
  # each key to the id it allocated.

  Scenario: A plan wires its beads by the keys the author chose, not by ids
    Given a creation plan of 4 beads wired dev -> test -> review -> tech-writer
    When the plan document is written
    Then every edge names two plan keys
    And no id appears anywhere in the plan

  Scenario: The ids a plan's beads carry are read out of the tracker's own answer
    Given the tracker answered a plan with ids dev=proj-fac and test=proj-5lm
    When the allocated ids are read
    Then the bead keyed dev is proj-fac

  Scenario: An answer that could not be read is not an answer naming no beads
    Given the tracker's answer to a plan was not readable
    When the allocated ids are read
    Then the ids are reported as unreadable rather than as an empty plan

  # At creation there is no allocated id yet, so a number in a title is a promise
  # nobody can check. `beadloom waves` compares the two AFTER the fact; this is the
  # same convention enforced where the divergence is created.

  Scenario: A title that numbers a bead before the tracker has is refused
    Given a creation plan whose bead titles include "[BDL-061.39][dev] the split"
    When the plan document is written
    Then the plan is refused for authoring a number the tracker has not allocated
    And the refusal names "BDL-061.39"

  Scenario: A title that carries no number is planned without complaint
    Given a creation plan of 4 beads wired dev -> test -> review -> tech-writer
    When the plan document is written
    Then the plan is accepted

  # The derivation learns both securing shapes, so a call site fixed here is visible
  # to the report that found it.

  Scenario: A creation that asks the tracker for the id it allocated is settled
    Given an artifact that instructs "bd create --type task --parent <parent-id> --json"
    When the call sites are judged
    Then the site's allocated-id assumption is secured

  Scenario: A creation that authors its ids by hand is reported as unsettled
    Given an artifact that instructs "bd create --type task --parent <parent-id> --silent"
    When the call sites are judged
    Then the site's allocated-id assumption is unsecured

  Scenario: A wiring an artifact tells its reader to verify is settled
    Given an artifact that instructs "bd dep add <blocked> <blocker>" and "bd dep tree <parent-id>"
    When the call sites are judged
    Then the site's intended-id assumption is secured

  Scenario: A wiring nothing in the artifact verifies is reported as unsettled
    Given an artifact that instructs "bd dep add <blocked> <blocker>"
    When the call sites are judged
    Then the site's intended-id assumption is unsecured

  # The echo is preserved rather than tidied away, and the form that discards it is
  # named. This scenario reddens the day an artifact of ours instructs the bulk form.

  Scenario: Bulk wiring that echoes no titles is reported rather than silently faster
    Given an artifact that instructs "bd dep add --file edges.ndjson"
    When the call sites are judged
    Then the site's echoed-titles assumption is unsecured
    And the detail names the count bd prints instead of the titles

  # The threshold is not tuned for speed. Two beads imply an edge, an edge implies an
  # id somebody writes down, and the plan is the form where nobody does.

  Scenario: One bead is created directly and two are planned
    Given a creation of 1 bead
    Then a plan is not required
    Given a creation of 2 beads
    Then a plan is required
