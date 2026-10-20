# BDL-083 S2d, RFC D6, BDL-UX #335. Measured on the first outside adopter's monorepo,
# anonymised as the monorepo fixture: a room for a 51-file `git mv` change had to be finished
# by hand, twice. The room is built from HEAD, so the old paths of a rename stayed in it — the
# old package importable, the old tests collected as a second set — and naming an old path in
# `--carry` refused the whole room: rc 2, `file_missing: <path> is not a path this project
# holds`. And a file shared with a neighbour bead was copied whole with the neighbour's edits
# in it, which the room did not say.
#
# So a carried path that HEAD holds and the working tree does not is deleted in the room, and
# the room names every file where the tree differs from HEAD that it does not carry: those are
# the differences it leaves out, a neighbour's work or a file the caller did not name.

@bead:beadloom-flrc @node:wave-plan
Feature: a clean room carries a deletion and names the differences it leaves out

  Scenario: Both sides of a rename are carried, and the old path is gone from the room
    Given the monorepo fixture checked out
    And the checkout renames "backend/src/file_history/entries.py" to "backend/src/file_history/history.py"
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/file_history/entries.py" and "backend/src/file_history/history.py"
    Then the room is built
    And the room does not hold "backend/src/file_history/entries.py"
    And the room holds the working tree's "backend/src/file_history/history.py"
    And the room reports "backend/src/file_history/entries.py" as deleted

  Scenario: A directory the deletions empty is gone from the room
    Given the monorepo fixture checked out
    And the checkout renames "backend/src/file_history" to "backend/src/history"
    When bead "beadloom-x.1" builds its clean room carrying every path of the rename
    Then the room is built
    And the room does not hold "backend/src/file_history"

  Scenario: The room names the files where the tree differs from HEAD that it does not carry
    Given the monorepo fixture checked out
    And the checkout renames "backend/src/file_history/entries.py" to "backend/src/file_history/history.py"
    And a neighbour has edited "docs/architecture.md" in the working tree
    And a neighbour has created "frontend/src/shared/lib/round.ts" in the working tree
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/file_history/entries.py" and "backend/src/file_history/history.py"
    Then the room reports "docs/architecture.md" as a modified file it does not carry
    And the room reports "frontend/src/shared/lib/round.ts" as an untracked file it does not carry
    And the room reports no carried path among the files it does not carry
    And the room holds HEAD's "docs/architecture.md"

  Scenario: A rebuild deletes a remembered path the tree no longer holds, and says so
    Given the monorepo fixture checked out
    And bead "beadloom-x.1" has built its clean room carrying "backend/src/file_history/entries.py"
    And the checkout deletes "backend/src/file_history/entries.py"
    When bead "beadloom-x.1" rebuilds its clean room naming no files
    Then the room is built
    And the room does not hold "backend/src/file_history/entries.py"
    And the room reports "backend/src/file_history/entries.py" as deleted

  Scenario: A path neither the tree nor HEAD holds is still refused
    Given the monorepo fixture checked out
    When bead "beadloom-x.1" builds its clean room carrying "backend/src/file_history/absent.py"
    Then no room is built
    And the refusal is reported as "file_missing"
