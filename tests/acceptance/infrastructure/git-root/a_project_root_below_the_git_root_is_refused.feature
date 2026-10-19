# BDL-083 S2e (`beadloom-7pd6`), BDL-UX #325, the owner's ruling of 2026-10-12. A project whose
# `.beadloom/` sits in a subfolder of a git repository reads git in two path frames: git answers
# relative to its own root, the project asks relative to the subfolder. `sync-check --since`
# then reads both sides of every pair as empty and calls every pair fresh, whatever changed.
# Nested roots are a transition-period layout, so the answer is a refusal by name, not support:
# `init`, `doctor` and `sync-check --since` say the git root is above the project root and exit
# non-zero. The same project at its git root is the control: nothing is refused there.

@bead:beadloom-7pd6 @node:git-root
Feature: a project root below the git root is refused by name

  Scenario: init refuses a project root below the git root and writes nothing
    Given a git repository whose code sits one folder below its root, with no .beadloom
    When init runs non-interactively in that folder
    Then the command exits 1
    And the output says the git root is above the project root and names both paths
    And the folder holds no .beadloom

  Scenario: doctor refuses a project root below the git root
    Given the monorepo fixture committed one folder below its git root, indexed
    When doctor runs in the project root
    Then the command exits 1
    And the output says the git root is above the project root and names both paths

  Scenario: sync-check --since refuses rather than comparing two empty sides
    Given the monorepo fixture committed one folder below its git root, indexed
    And a code file of a documented pair changed since HEAD
    When sync-check runs against HEAD in the project root
    Then the command exits 1
    And the output says the git root is above the project root and names both paths
    And no pair is reported fresh

  Scenario: the same project at its git root is not refused
    Given the monorepo fixture committed at its own git root, indexed
    And a code file of a documented pair changed since HEAD
    When doctor runs in the project root
    Then the command exits 0
    And doctor says no git root is above the project root
    When sync-check runs against HEAD in the project root
    Then the command exits 2
    And the changed pair is reported stale
