# BDL-068 S1.4. The `## Axes` section is one grammar read in both directions:
# `beadloom impact` renders it, the checks read it back, and the beads' `refs:`
# is generated from it. One home, so no two of the three can disagree -- the
# class this epic exists to remove (CONTEXT Q1).

@bead:beadloom-0mdo.4 @node:axes-section
Feature: the Axes section records the derivation it came from and the scope decision taken on it

  BDL-068 S1.3 measured, at af26750d, that the same derivations list two writers
  and four branches seeded from the commit point and no writers and three
  branches seeded from the function the bead was changing. The axes are
  therefore a property of the SEED, and a section that states them without it is
  a confident number with no way to tell which of the two runs produced it.

  Scenario: The axes name the population the derivation could not resolve
    Given an impact answer whose derivation could not resolve two call sites
    When the Axes section is rendered from it
    Then the section names the unresolved population

  Scenario: An absent seed renders as unresolved rather than as no axes
    Given an impact answer for which the seed rule found no seed
    When the Axes section is rendered from it
    Then the section states that the seed is none
    And the section does not state that there are zero co-writers

  Scenario: An Axes section that names no seed is reported
    Given a brief whose "Axes" section lists an axis and names no seed
    When the Axes section is checked
    Then the brief is reported as stating axes without a seed

  Scenario: An axis with no scope decision is reported
    Given a brief whose "Axes" section lists an axis with an undecided scope cell
    When the Axes section is checked
    Then the brief is reported as stating an axis with no scope decision

  Scenario: The refs line is generated from the axes kept in scope
    Given a brief whose "Axes" section keeps two nodes in scope and one out
    When the refs line is generated from the document
    Then it names the two nodes kept in scope and not the third

  # BDL-UX #244. This section's own rule is that a work item's axes are the UNION
  # of its slices' and that each slice appends its rows under its own `Derived by`
  # line, so a real section holds one table per slice. The reader took the first
  # table's header as the header for everything under the heading, and the second
  # table's header row came back as data: an approved node named `Node`, in the
  # list `scope-check` compares every commit against. Measured on this repository's
  # RFC laid out in the shape its own rule describes: 78 rows read where 74 exist,
  # 4 of them header rows, all four approved.

  @bead:beadloom-0mdo.46
  Scenario: A slice appending its rows under its own derivation block is read as its own table
    Given a work item whose "Axes" section carries two derivation blocks, each with its own table
    When the Axes section is read back
    Then the rows read are the rows the two tables state
    And no node named after a column heading is kept in scope

  @bead:beadloom-0mdo.46
  Scenario: The second table's rows are judged against the second table's columns
    Given a work item whose second derivation block orders its columns differently
    When the Axes section is read back
    Then the second table's row is read with its own node and its own scope decision

  # BDL-UX #284. `impact` now writes, on each row, the files the row's node owns
  # that the derivation could not read. This section is READ by `beadloom axes`,
  # and what it returns feeds `beadloom waves` and `scope-check`, so the reader
  # takes the new column and every table written before it existed reads exactly
  # as it did -- with the unstated column read as not stated, never as "none".

  @bead:beadloom-rqma.2
  Scenario: A row's unread ownership is read back from the section
    Given an impact answer whose caller's node owns a file the derivation could not read
    When the Axes section is rendered from it and read back
    Then the caller's row reads back with that file counted
    And the rows whose nodes own nothing unread read back as none

  @bead:beadloom-rqma.2
  Scenario: A table written before the column existed reads as it did
    Given a brief whose "Axes" table carries no column for unread ownership
    When the Axes section is read back
    Then every row reads with the node, sites and scope decision it states
    And no row claims a count of unread files
