# BDL-068 S5, BDL-UX #210 and #207. The two findings of this slice that are entirely
# ours: no `bd` defect is involved in either.
#
# #210 -- the reconcile could not read a bead id written as a Markdown code span, and
# said the id was at fault. Measured on this repository at 5846b20, before the fix:
# `beadloom active-sync --check --json` read 329 rows, resolved 211 and reported 118
# unresolved, every one of them under the single sentence "is not a bead id in either
# form". Twenty-seven of the 118 are BDL-067's own table, whose every row writes its id
# as `` `beadloom-e8s4.1` `` -- a whole epic invisible to the mechanism that exists to
# keep it honest, on the branch this bead is being written on.
#
# The 118 are four different faults wearing one sentence: an id under decoration, an id
# followed by a title, a range of ids, and a label that is not an id at all. Only the
# first is a reading fault of ours; the other three are facts about the table, and each
# is worth a different sentence because each has a different remedy.
#
# #207 -- `active-sync --stage` added `.beads/issues.jsonl` to a commit after the agent
# had deliberately removed it, and announced the addition. The project's own instruction
# to stage by explicit path cannot survive a tool that stages after the agent decided.
# The index at pre-commit time IS the set of paths the agent chose, so a correction to a
# path that set does not contain is reported and never added.

@bead:beadloom-0mdo.54 @node:active-table
Feature: the reconcile reads the id a row names and stages nothing the commit did not

  # The id is present in every one of these cells. What differs is the decoration a
  # Markdown document puts around it, and decoration is not a fact about the bead.

  Scenario: A bead id written as a code span resolves to the bead it names
    Given the tracker reports proj-x.10 as closed
    When the row cell "`proj-x.10`" is resolved
    Then the row resolves to proj-x.10

  Scenario: A short bead id written as a code span resolves against its epic
    Given the tracker reports proj-x.10 as closed
    When the row cell "`.10`" is resolved against the epic proj-x
    Then the row resolves to proj-x.10

  Scenario: A bead id written in bold resolves to the bead it names
    Given the tracker reports proj-x.10 as closed
    When the row cell "**proj-x.10**" is resolved
    Then the row resolves to proj-x.10

  # A row the reconcile skipped must read differently from a row it checked and found
  # correct, and differently again from the next row it skipped for another reason.

  Scenario: A cell that names an id and then a title says so, and names the id
    Given the tracker reports proj-x.7 as closed
    When the row cell "`.7` review" is resolved against the epic proj-x
    Then the row does not resolve
    And the reason names the shape "names a bead and then adds text"
    And the reason quotes ".7"

  Scenario: A cell that names a range of beads says so
    Given the tracker reports proj-x.73 as closed
    When the row cell ".73-.76" is resolved against the epic proj-x
    Then the row does not resolve
    And the reason names the shape "names more than one bead"

  Scenario: A cell that carries no bead id at all says that, and nothing else
    Given the tracker reports proj-x.7 as closed
    When the row cell "BEAD-01" is resolved against the epic proj-x
    Then the row does not resolve
    And the reason names the shape "carries no bead id"

  Scenario: An id the tracker does not hold is a finding about the tracker, not the cell
    Given the tracker reports proj-x.7 as closed
    When the row cell "`.99`" is resolved against the epic proj-x
    Then the row does not resolve
    And the reason names the tracker rather than the cell

  # The four shapes are counted, because "118 unresolved" is a number nobody can act on
  # and "27 of them are a decoration we cannot read" is one somebody fixes in an hour.

  Scenario: The unresolved rows are counted by the shape that made each unresolvable
    Given an ACTIVE table whose rows are "`.1`", ".2 the title", "BEAD-01" and ".3-.4"
    And the tracker reports .1, .2, .3 and .4 of that epic as closed
    When the tables are reconciled
    Then 1 row resolved
    And the unresolved rows are counted as 1 with-text, 1 no-id and 1 range

  # A row the table does not carry is drift the reconcile cannot correct and must not
  # hide. It is never written: adding a row to somebody's document is the same fault as
  # adding a path to somebody's commit.

  Scenario: A bead the tracker holds and the table has no row for is named
    Given an ACTIVE table whose rows are "`.1`"
    And the tracker reports .1 and .2 of that epic as closed
    When the tables are reconciled
    Then the bead .2 is reported as carried by no row
    And the table still has 1 row

  Rule: the reconcile stages nothing the commit had not already staged

    @node:cli-commands

    # The index at pre-commit time is the agent's decision about what this commit is.

    Scenario: A corrected file the commit already stages is restaged
      Given the commit already stages the corrected ACTIVE.md
      When the reconcile decides what to stage
      Then the ACTIVE.md is staged
      And nothing is withheld

    Scenario: A corrected file the commit does not stage is withheld and named
      Given the commit stages nothing
      When the reconcile decides what to stage
      Then nothing is staged
      And the ACTIVE.md is withheld

    Scenario: A commit whose scope cannot be read has nothing decided for it
      Given the commit's staged paths cannot be read
      When the reconcile decides what to stage
      Then nothing is staged
      And the decision states that the commit's scope could not be read

    # The hook is the surface the defect was reported through, so the promise is
    # asserted on the text that gets installed rather than on the code behind it.

    Scenario: The installed pre-commit hook stages nothing of its own
      Given the pre-commit hook this project installs
      Then it runs no git add of its own
      And it reports the paths the reconcile withheld

  # BDL-068 S5 fix wave, from the S5 review's Major 1. The report above named a bead as
  # having no row while the SAME run reported the row that names it, under
  # `bead-and-text` or `more-than-one-bead`. Measured on this repository at 27db92b: 79
  # beads reported as carried by no row, and 38 of the 79 had a row whose first cell's
  # head is exactly that bead's id. A reader acting on the message adds a row that is
  # already there.

  Rule: a bead a row names is never reported as having no row

    @bead:beadloom-0mdo.61 @node:active-table

    Scenario: A run that could not read a row does not also report the row as missing
      Given an ACTIVE table whose rows are ".1 Contract model"
      And the tracker reports .1 and .2 of that epic as closed
      When the tables are reconciled
      Then the bead .1 is reported as named by a row this run could not read
      And the bead .2 is reported as carried by no row
      And the two populations name no bead in common

    Scenario: The row a bead is named by is quoted, so the reader can find it
      Given an ACTIVE table whose rows are ".1 Contract model"
      And the tracker reports .1 of that epic as closed
      When the tables are reconciled
      Then the row quoted against the bead .1 is ".1 Contract model"

    Scenario: A range names its first bead and is not expanded into the rest
      Given an ACTIVE table whose rows are ".3-.8"
      And the tracker reports .3 and .8 of that epic as closed
      When the tables are reconciled
      Then the bead .3 is reported as named by a row this run could not read
      And the bead .8 is reported as carried by no row

    Scenario: A bead whose row resolved is in neither population
      Given an ACTIVE table whose rows are "`.1`"
      And the tracker reports .1 of that epic as closed
      When the tables are reconciled
      Then 1 row resolved
      And the bead .1 is reported in neither population
