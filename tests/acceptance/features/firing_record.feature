# BDL-061 bead `.56`, carried out of `.35` rather than solved by it. The firing
# record is append-only with no rotation and no cap, and `read_firings` parses it
# whole on every `guard --liveness`, so the cost of the report grows without bound
# with the number of guarded edits. `.35` added the `.gitignore` entry, which made
# the growth INVISIBLE rather than absent.
#
# What is bounded, and why: the number of RECORDS, not bytes and not age. A byte
# cap truncates mid-record; an age cap on a long-lived project loses "how often"
# and makes a quiet month read like a dead guard. A record cap bounds exactly the
# thing that was measured — the parse.
#
# What rotation may lose: no count and no verdict. `--liveness` treats a gate that
# cannot demonstrate it ran as not having run, so a rotation that dropped firings
# silently could turn a healthy guard into a false `never-fired`. The firings that
# leave the active record are folded into a carried summary that survives every
# later rotation, and their full detail stays on disk for one more generation.

@bead:beadloom-mr2l.56 @node:flow-guards
Feature: the firing record is bounded and loses no evidence

  Scenario: The record stops growing and the count does not change
    Given a firing record filled to its cap by one guard
    When one more guard evaluation is recorded
    Then the active record holds no more firings than its cap
    And the liveness report counts every firing ever recorded

  Scenario: A guard whose every firing was rotated away has still fired
    Given a firing record filled to its cap by one guard
    When one more guard evaluation is recorded
    Then the guard whose firings were rotated away is not reported as never-fired
    And its last recorded outcome is still reported

  Scenario: The detail that leaves the active record is not deleted
    Given a firing record filled to its cap by one guard
    When one more guard evaluation is recorded
    Then the rotated firings are still readable on disk
