# What an adopter's role protocol files are made of (BDL-068 S6, BDL-UX #177).
# One Feature per file.

@bead:beadloom-iur5 @node:agentic-flow-setup
Feature: the role protocols a project receives are composed for that project

  The scaffold writes three kinds of artifact into a repository it does not own.
  Two of them — the slash commands and CLAUDE.md — are composed from authored
  package data plus the overlays that project's own flow selects. The third was
  not: `.claude/agents/*.md` came from five `agents/*.md.txt` assets that were
  a byte-snapshot of THIS repository's live `.claude/agents/`, refreshed by a
  function with no production caller and held byte-identical by two tests.

  That is the shape BDL-UX #177 removed for CLAUDE.md and the commands, left
  standing on one leg. It was harmless only while this repository had no
  `.beadloom/flow/roles/` fragment, because the snapshot then happened to equal
  the pure shipped composition. A fragment added here would have been written
  into the package by the next refresh and shipped to every adopter, silently,
  and byte-identically to what the tests asserted.

  It had a second cost that did not need a fragment to appear: the snapshot is
  one composition — this project's DDD and Python — so a project whose flow
  declares anything else received role protocols for an architecture it does not
  use.

  Scenario: a role file is the composition for that project's own flow
    Given a project the scaffold writes role files into
    When the scaffold writes its role files
    Then every role file it wrote is the composition for that project's own flow

  Scenario: the project's own role fragment reaches the role file it receives
    Given a project the scaffold writes role files into
    And that project declares its own "dev" role fragment
    When the scaffold writes its role files
    Then the fragment's text is in ".claude/agents/dev.md"

  Scenario: a project that declares another architecture receives that one
    Given a project the scaffold writes role files into
    And that project's flow declares architecture "fsd"
    When the scaffold writes its role files
    Then ".claude/agents/dev.md" carries the "fsd" architecture overlay
    And ".claude/agents/dev.md" carries no "ddd" architecture overlay

  Scenario: no role body is shipped as package data
    Given the agentic-flow assets this package ships
    Then none of them is a role body

  Scenario: no function refreshes package data from a live role directory
    Given the module that scaffolds the agentic flow
    Then it exposes nothing that writes package data
