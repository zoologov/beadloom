# Measured by `beadloom-0mdo.37` while using the command on the bead that built
# it: a rebuild retyped the same `--carry` list, 16 flags entered twice, once
# after each fix the room itself caught. The room is correct today and the
# retyping costs seconds — what earns this a place in the slice is that the
# alternative an agent reaches for under that friction is to copy files into the
# LIVE room, which is the failure BDL-UX #243 records and `.37` fixed. And
# `beadloom-0mdo.74` made the rebuild cost more than it did when this was filed:
# a room now builds its own interpreter, measured at 0.04 s plus 3.6 s warm.
#
# So a rebuild reproduces the REQUEST the room it replaces recorded, and never
# its content: the files are copied from the working tree at build time, which is
# what keeps #243 answered. There is still no "everything that differs from HEAD"
# mode, and the remembered list must not become a proxy for one — it holds
# exactly what a caller once named.

@bead:beadloom-uzck @node:wave-plan
Feature: a rebuild reproduces the room it replaces, over the working tree's files

  Scenario: A rebuild carries the files the room it replaces named
    Given a project at a commit
    And the working tree changes "src/thing.py"
    And bead "beadloom-x.1" has built its clean room carrying "src/thing.py"
    When bead "beadloom-x.1" rebuilds its clean room naming no files
    Then the room is built
    And the room holds the working tree's "src/thing.py"
    And the rebuild reused "carry"

  Scenario: What is reused is the list, and never the content
    Given a project at a commit
    And the working tree changes "src/thing.py"
    And bead "beadloom-x.1" has built its clean room carrying "src/thing.py"
    And the working tree changes "src/thing.py" again
    When bead "beadloom-x.1" rebuilds its clean room naming no files
    Then the room is built
    And the room holds the working tree's "src/thing.py"

  Scenario: A carry named beside a rebuild replaces the remembered list
    Given a project at a commit
    And the working tree changes "src/thing.py"
    And bead "beadloom-x.1" has built its clean room carrying "src/thing.py"
    When bead "beadloom-x.1" rebuilds its clean room carrying "pyproject.toml"
    Then the room is built
    And the room carried only "pyproject.toml"
    And the rebuild reused nothing

  Scenario: A remembered file the working tree no longer holds refuses the rebuild
    Given a project at a commit
    And the working tree changes "src/thing.py"
    And bead "beadloom-x.1" has built its clean room carrying "src/thing.py"
    And the working tree no longer holds "src/thing.py"
    When bead "beadloom-x.1" rebuilds its clean room naming no files
    Then no room is built
    And the refusal is reported as "file_missing"
    And the room still holds "src/thing.py"

  Scenario: A first build has no room to remember from
    Given a project at a commit
    When bead "beadloom-x.1" builds its clean room
    Then the room is built
    And the rebuild reused nothing

  Scenario: The extras a caller pinned survive the rebuild
    Given a project at a commit
    And bead "beadloom-x.1" has built its clean room with extras "dev" and no environment
    When bead "beadloom-x.1" rebuilds its clean room with no environment and naming no files
    Then the room is built
    And the room records the extras request "dev"
    And the rebuild reused "extras"

  Scenario: A room the caller gave no environment is not rebuilt without one
    Given a project at a commit
    And bead "beadloom-x.1" has built its clean room with no environment
    When bead "beadloom-x.1" rebuilds its clean room naming no files
    Then the room is built
    And the room records that an environment was asked for
