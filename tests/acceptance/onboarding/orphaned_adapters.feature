# Role adapters Beadloom wrote for a tool the flow no longer declares
# (BDL-068 S6, beadloom-ec1a). One Feature per file.

@bead:beadloom-ec1a @node:config-check
Feature: an adapter set whose tool left flow.yml is still reported

  Every reader of role adapters takes its population from `config.tools` --
  `_adapter_states`, `declined_adapter_rewrites` and `_role_files_on_disk` all
  open with the same loop. So dropping a tool from `flow.yml` does not add a
  finding about the files that tool wrote; it removes them from the check. The
  files stay on disk, the tool that reads them still reads them, and nothing
  compares them against anything ever again.

  Measured before this Feature was written, with a control: the same two lines
  appended to `.claude/agents/dev.md` and to `.cursor/agents/dev.md` in one
  project whose flow declares `claude` only. The first is an error and the
  second is exit 0.

  The population is taken from the flow manifest, not from the role names and
  tool directories this release happens to ship. A file Beadloom recorded
  writing is Beadloom's orphan; a file nothing records is somebody else's, and
  claiming it would be the false positive `_adapter_drifts` avoids by checking
  only adapters it recognises.

  Scenario: an adapter of a dropped tool is reported
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    When the agent-config check runs
    Then ".cursor/agents/dev.md" is reported as orphaned

  Scenario: every adapter the dropped tool wrote is reported, not just one
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    When the agent-config check runs
    Then one orphan finding is reported for each role adapter the manifest records under ".cursor/agents"

  Scenario: an orphan that already diverged says so rather than only warning it could
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    And ".cursor/agents/dev.md" is edited by hand
    When the agent-config check runs
    Then the finding for ".cursor/agents/dev.md" says it already differs from what Beadloom wrote

  Scenario: an orphan nobody has touched says it has not diverged yet
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    When the agent-config check runs
    Then the finding for ".cursor/agents/dev.md" says nothing compares it any more

  Scenario: the finding is reported and does not block
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    When the agent-config check runs
    Then every orphan finding carries severity "warn"
    And no orphan finding offers --fix as its remedy
    And the check does not exit non-zero because of them

  Scenario: an adapter of a declared tool is not an orphan
    Given a project whose flow scaffolded claude and cursor
    When the agent-config check runs
    Then no orphan finding is reported

  Scenario: an adapter file nothing recorded writing is not claimed
    Given a project whose flow scaffolded claude only
    And a hand-authored ".cursor/agents/dev.md" the manifest does not record
    When the agent-config check runs
    Then no orphan finding is reported

  Scenario: a role the manifest records under a dropped tool is reported even when this release no longer composes it
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    And the manifest records ".cursor/agents/legacy.md" and the file exists
    When the agent-config check runs
    Then ".cursor/agents/legacy.md" is reported as orphaned

  Scenario: a recorded adapter the adopter already deleted is not reported
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    And the ".cursor/agents" directory is deleted
    When the agent-config check runs
    Then no orphan finding is reported

  Scenario: a project with no flow.yml has no orphans
    Given a project with no flow.yml and a ".cursor/agents/dev.md" on disk
    When the agent-config check runs
    Then no orphan finding is reported

  # The Cursor orchestrator pointer is a stated exclusion, not an oversight:
  # `role_adapters` publishes that no check compares it in either state, so
  # calling it orphaned would claim it was guarded before the tool was dropped.

  Scenario: the Cursor orchestrator pointer is not reported as an orphaned adapter
    Given a project whose flow scaffolded claude and cursor
    And cursor is removed from the flow's tools
    When the agent-config check runs
    Then ".cursor/rules/beadloom-flow.md" is not reported as orphaned
