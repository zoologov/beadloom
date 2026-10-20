# A version bump on a project composed for both tools (BDL-083 S2R pass 1 Major 1, RFC D13).
# One Feature per file.

@bead:beadloom-ba9w.24 @node:config-check
Feature: a release moves the rendered section in both tools, and one refresh repairs both

  Measured at b7d46e27 on a project composed for Claude and Cursor and clean: the
  version went from 1.0.0 to 2.0.0 and a dependency was added. config-check exited
  1 with two errors. .claude/CLAUDE.md named the rendered project-info section,
  and the Cursor core rule blamed the core, the overlays and the project layer,
  none of which had moved. setup-rules --refresh repaired CLAUDE.md and left the
  rule stale, so the two tools carried two texts after the first release.

  Both files carry one composed core with one rendered section. Each is compared
  with that section blanked, each names the section when it moves, and one
  refresh re-renders it in both.

  Scenario: a version bump and a new dependency name the rendered section in both files
    Given a project composed for "claude" and "cursor" at version "1.0.0"
    When the project is released as version "2.0.0" with a new dependency
    And config-check runs
    Then config-check exits 1
    And ".claude/CLAUDE.md" is reported with "auto-managed section(s) stale: project-info"
    And ".cursor/rules/beadloom-flow.mdc" is reported with "auto-managed section(s) stale: project-info"
    And no finding blames "CORE + the flow.yml overlays"

  Scenario: one refresh repairs both files into one text
    Given a project composed for "claude" and "cursor" at version "1.0.0"
    When the project is released as version "2.0.0" with a new dependency
    And setup-rules --refresh runs
    And config-check runs
    Then config-check exits 0
    And the body of the Cursor core rule is byte-identical to the Claude CLAUDE.md
    And the Claude CLAUDE.md states version "2.0.0"
