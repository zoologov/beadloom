# The ignore block Beadloom generates, checked against the file it was written into
# (BDL-068 S6, BDL-UX #238). One Feature per file.

@bead:beadloom-0mdo.40 @node:config-check
Feature: the ignore block on disk still declares what this version generates

  The block is GENERATED into a repository Beadloom does not own and then
  hand-maintained there, which is the one shape that can only stay correct by
  coincidence. It stayed correct by coincidence until S4: this repository's
  .gitignore carried the exact filename `.beadloom/guard-firings.jsonl` while the
  generator had emitted the glob `.beadloom/guard-firings*.jsonl` since rotation
  shipped, and nobody found it. An unrelated change tripled the firings, the log
  rotated for the first time, and the second file appeared as untracked churn.

  An adopter is worse off than this repository was, because the upgrade path
  writes no ignore block at all: a project initialised before a pattern shipped
  keeps the old set forever and nothing says so.

  What is compared is the PATTERNS the generator emits, not the block's text. The
  reason comments are prose in a human's file, and a project that ignores the same
  paths under its own hand-written heading is correct — this repository does
  exactly that, and has no generated block at all.

  Scenario: a pattern this version emits that the file does not declare is reported
    Given a git project whose .gitignore declares every generated pattern
    And the generator emits one pattern the file does not declare
    When the agent-config check runs
    Then that pattern is reported against ".gitignore"

  Scenario: a finding names the declared line the current pattern supersedes
    Given a git project whose .gitignore declares ".beadloom/guard-firings.jsonl"
    When the ignore block is checked
    Then the finding for ".beadloom/guard-firings*.jsonl" names ".beadloom/guard-firings.jsonl" as the line it supersedes
    And its remediation says to replace that line rather than to add one

  Scenario: a file that declares every generated pattern is no finding
    Given a git project whose .gitignore declares every generated pattern
    When the ignore block is checked
    Then no ignore-block finding is reported

  Scenario: every pattern the generator emits is checked, with no second list
    Given a git project whose .gitignore declares nothing
    When the ignore block is checked
    Then one finding is reported for each pattern the generator emits

  Scenario: a block whose reason text predates this version is not a finding
    Given a git project whose .gitignore declares every generated pattern under its own heading
    When the ignore block is checked
    Then no ignore-block finding is reported

  Scenario: a project outside a git working tree is not checked
    Given a project with no git working tree and a .gitignore that declares nothing
    When the ignore block is checked
    Then no ignore-block finding is reported

  Scenario: an undeclared pattern is reported and does not block
    Given a git project whose .gitignore declares nothing
    When the agent-config check runs
    Then every ignore-block finding carries severity "warn"
    And no ignore-block finding offers --fix as its remedy

  # The drift this bead exists for was in this repository's own file, so the
  # repository is a subject of the check and not only its author.

  Scenario: this repository's own .gitignore declares every pattern this version emits
    Given the .gitignore of the project this flow ships from
    When its declared patterns are checked against the generator
    Then no ignore-block finding is reported
