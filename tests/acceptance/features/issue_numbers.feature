# BDL-068 S6, beadloom-0mdo.66. The UX issue log is a numbered append-only
# markdown file that every bead writes into, and the number an author takes is
# the one they read off the end of it. That has collided five times: #187,
# #211, #253, and twice in one hour on 2026-09-09 when one agent took #259 --
# already taken hours earlier by another bead in the same slice -- and #260,
# which never reached the file at all.
#
# The number is therefore ALLOCATED rather than read. The allocation is one
# file per number in a ledger directory, created with O_CREAT|O_EXCL, which is
# `beadloom-l9ee`'s one-file-per-incident primitive taken at the boundary: the
# claim file is where the incident's body grows when the log becomes a composed
# view of that directory.
#
# The check ships beside the allocator and not instead of it. O_EXCL spans one
# filesystem, so two agents in two clones can still take one number and only
# the merge shows it.

@bead:beadloom-0mdo.66 @node:issue-numbers
Feature: an issue number is allocated from the log, never read off the end of it

  Scenario: Two writers allocating at the same moment receive different numbers
    Given an issue log whose highest number is 261
    When two writers allocate a number without either seeing the other
    Then the two writers hold different numbers
    And each number has a claim file of its own

  Scenario: A number the log states only in a closed entry's heading is never handed out again
    Given an issue log that states 159 in a consolidated heading and in no entry
    When a number is allocated
    Then the allocated number is not 159

  Scenario: A number two entries both define is reported
    Given an issue log in which two entries are both numbered 187
    When the issue numbers are checked
    Then 187 is reported as defined twice

  Scenario: A number claimed and never written into the log is reported
    Given a ledger holding a claim for 262 and a log with no entry numbered 262
    When the issue numbers are checked
    Then 262 is reported as claimed and unwritten

  Scenario: An entry written past the ledger's floor without claiming its number is reported
    Given a ledger whose floor is 262 and a log entry numbered 263 that no claim holds
    When the issue numbers are checked
    Then 263 is reported as unclaimed

  Scenario: A project that declares no issue log is not judged
    Given a project that declares no issue log
    When the issue numbers are checked
    Then the check reports that no issue log is declared
    And the check reports no finding

  # BDL-068 S6, beadloom-l9ee. `unclaimed-number` skips every entry below the
  # ledger's floor, which is deliberate -- the floor is derived so that a
  # project adopting the allocator is judged from its first allocation onwards.
  # The verdict did not say so. On this repository it reads "240 entr(ies), 5
  # claim(s), floor 262" and then "No duplicate, unwritten or unclaimed
  # number", over a log whose 235 entries below the floor that leg never
  # entered. A clean list is trusted and stopped at, which is this epic's own
  # constraint met by the module that states it.
  @bead:beadloom-l9ee
  Scenario: A verdict over a log older than its ledger names the entries no leg judged
    Given a ledger whose floor is 262 and a log holding 3 entries below it
    When the issue numbers are checked
    Then the verdict names 3 entries as below the floor and judged by no leg

  # The same sentence must not appear when there is nothing to qualify: a
  # project whose whole log was allocated has no unreached population, and a
  # check that says so anyway is noise that trains a reader to skip the line.
  @bead:beadloom-l9ee
  Scenario: A log whose every entry was allocated qualifies nothing
    Given a ledger whose floor is the log's own first entry
    When the issue numbers are checked
    Then the verdict names no entry as below the floor
