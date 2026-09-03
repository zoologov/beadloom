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
