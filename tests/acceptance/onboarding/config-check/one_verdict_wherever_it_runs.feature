# `config-check` over the same files in the main checkout, a git worktree and a clean room
# (BDL-083 S2c, RFC D7, BDL-UX #334). One Feature per file.

@bead:beadloom-ixbd @node:config-check
Feature: config-check gives the checkout's verdict in a worktree and in a clean room

  Measured on 9.0.0 at f3d6f293 over a copy of the monorepo fixture, which names
  itself in no root manifest: the flow composed in the main checkout carried the
  checkout's directory name in the heading of .claude/CLAUDE.md. config-check
  exited 0 in the checkout, 1 in a worktree of a clean HEAD and 1 in a clean room
  of the same files, each time with "composed body is stale", and the verdict
  named neither what it composed nor what it compared.

  The composition now takes the project's declared name: `project_name:` in
  .beadloom/config.yml, then a root manifest. A project that declares neither keeps
  the name its last composition wrote into the heading, which is a tracked file and
  reads the same in all three places. The directory's name is reached only by the
  first composition of a project that declares nothing.

  Scenario: a worktree of a clean HEAD gives the checkout's verdict
    Given the monorepo fixture composed and committed in a checkout named "desk-checkout"
    When config-check runs in the checkout and in a worktree of HEAD
    Then both runs exit 0

  Scenario: a clean room gives the checkout's verdict
    Given the monorepo fixture composed and committed in a checkout named "desk-checkout"
    When config-check runs in the checkout and in the clean room of bead "desk-ixbd"
    Then both runs exit 0

  Scenario: the verdict names the file it composed from and the file it compared against
    Given the monorepo fixture composed and committed in a checkout named "desk-checkout"
    When config-check runs in the checkout and in the clean room of bead "desk-ixbd"
    Then both runs say they compared ".claude/CLAUDE.md" against its composition from ".beadloom/flow.yml"
    And both runs say the name "desk-checkout" was read from ".claude/CLAUDE.md" and is not compared

  @node:project-name
  Scenario: a declared name is the name the composition takes in every place
    Given the monorepo fixture declaring the project name "metrics-desk"
    And the monorepo fixture composed and committed in a checkout named "desk-checkout"
    When config-check runs in the checkout and in a worktree of HEAD
    Then both runs exit 0
    And the composed heading names the project "metrics-desk"
