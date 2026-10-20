# What a second tool reads of the composed flow (BDL-083 S2h, RFC D13, BDL-UX #356).
# One Feature per file.

@bead:beadloom-ybxm @node:tool-reach
Feature: the second tool reads the composed flow the first one reads

  Up to 9.0.0 a project that named Cursor received the five role files and a
  17-line pointer, and nothing else. The core, the project layer, the STACK
  overlay and the four commands were composed for Claude Code only, so an agent
  on Cursor ran the flow with no tracker discipline, no Definition of Done and no
  closure duties, and every rule the Gate does not enforce was absent for it.
  The role files were shared; the layer that makes the roles a flow was not.

  Scenario: a cursor-only project reads the same core and commands as a claude-only one
    Given a project scaffolded for "claude" with a project fragment for the core
    And a project scaffolded for "cursor" with the same project fragment for the core
    Then the body of the Cursor core rule is byte-identical to the Claude CLAUDE.md
    And the body of every Cursor command rule is byte-identical to its Claude command

  Scenario: every rule Beadloom writes for Cursor is applied to every request
    Given a project scaffolded for "cursor" with a project fragment for the core
    Then every rule written under ".cursor/rules/" declares "alwaysApply: true"
    And the pointer ".cursor/rules/beadloom-flow.md" is not written

  Scenario: a project composed by 9.0.0 for both tools is red, naming the tool and the layer
    Given a project scaffolded for both "claude" and "cursor" with a project fragment for the core
    And its Cursor rules are the layout 9.0.0 wrote
    When config-check runs
    Then config-check exits 1
    And a finding names the tool "cursor" and the layer "project"

  Scenario: a cursor-only project is not told to restore files its setup never writes
    Given a project scaffolded for "cursor" with a project fragment for the core
    When config-check runs
    Then config-check exits 0
    And no finding names ".claude/agents/"
