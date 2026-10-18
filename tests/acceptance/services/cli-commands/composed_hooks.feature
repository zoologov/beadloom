# BDL-083 S1a, beadloom-7i09 (BDL-UX #326, #327; RFC D1; PRD ruling 3).
#
# Measured on 9.0.0 on 2026-10-18. The composed pre-push hook exited 0 and printed
# nothing when `beadloom` was not on the PATH git ran it with. The composed
# pre-commit hook ran no `beadloom lint`: on the monorepo fixture, with a widget's
# spec importing the app layer staged, `lint --strict` on the tree exited 1 and the
# warn-mode hook exited 0 without a line about it. Its ruff leg, with uv on PATH and
# no ruff anywhere, printed "Warning: ruff lint violations in this commit" for a
# ruff that never started.

@bead:beadloom-7i09 @node:cli-commands
Feature: the composed hooks say when a check did not run

  A hook that passes without running its check is the worst kind of gate this
  project names: it reads exactly like one that ran and found nothing. The pre-push
  hook is installed per clone by `install-hooks`, so a missing `beadloom` is a setup
  error the person pushing must see, and the push is refused with a sentence. The
  pre-commit hook judges the architecture of the nodes the commit touches, and each
  of its legs tells a check that found something from a check that could not start.

  Scenario: a push whose hook cannot find beadloom is refused with a sentence
    Given a repository with the composed hooks installed
    When the pre-push hook runs without beadloom on its PATH
    Then the hook exits non-zero
    And the hook says the Gate did not run because beadloom is not on its PATH

  Scenario: a Gate that stopped without a verdict is reported as not run
    Given a repository with the composed hooks installed
    And a beadloom whose Gate exits 1 without printing a verdict
    When the pre-push hook runs
    Then the hook exits non-zero
    And the hook says the Gate did not run
    And the hook says nothing about stale documentation

  Scenario: a commit that stages a layer violation is told so before it is made
    Given the monorepo fixture as a repository with the blocking hooks installed
    And a staged widget spec that imports the app layer
    When the pre-commit hook runs with beadloom on its PATH
    Then the hook names the fsd-layers violation of the widget's node
    And the hook blocks the commit for the architecture lint

  Scenario: a ruff that cannot start is reported as not run, not as violations
    Given a repository with the composed hooks installed
    And a staged Python file at the repository root
    And a uv that cannot find ruff
    When the pre-commit hook runs
    Then the hook says ruff did not run and shows uv's own words
    And the hook does not report ruff lint violations

  Scenario: ruff runs in the Python project that holds the staged file
    Given a repository with the composed hooks installed
    And a staged Python file under a subfolder that holds its own pyproject.toml
    And a uv that records where it was run
    When the pre-commit hook runs
    Then ruff ran in that subfolder over the file's path inside it
