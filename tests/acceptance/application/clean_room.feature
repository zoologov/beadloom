# BDL-UX #235 and #243, one capability. The clean-room convention named a fixed
# directory and said nothing about a second entry, so two agents of one S4 wave
# built one room: `beadloom-0mdo.31`'s archive at 22:53, `beadloom-0mdo.27`'s
# files copied in at 23:16, `.31`'s at 23:26. `.31`'s run there reported 8
# failures and five of them were `.27`'s, none a defect in either bead. And a
# room entered a second time manufactures a failure of its own: files copied in
# after the room was reindexed postdate its doc-freshness baseline, which
# `beadloom-0mdo.41` measured as `sync-check` exit 2 with `stale: 2` against a
# change that is clean at HEAD.
#
# Both are the same missing guarantee: the room is not derived from the bead and
# is not known to be one this run created. So the scenarios below are about who
# the room belongs to and how many times it may be built, and never about what a
# suite run inside it returns.

@bead:beadloom-0mdo.37 @node:wave-plan
Feature: a clean room is derived from the bead that owns it and is built exactly once

  Scenario: The room is named after the bead, not after the concept
    Given a project at a commit
    When bead "beadloom-x.1" builds its clean room
    Then the room is built
    And the room's directory is named "room-beadloom-x.1"

  Scenario: Two beads of one wave cannot be handed the same room
    Given a project at a commit
    And bead "beadloom-x.1" has built its clean room holding its own file "own.txt"
    When bead "beadloom-x.2" builds its clean room
    Then the room is built
    And the two beads' rooms are different directories
    And the room does not hold "own.txt"

  Scenario: A directory this run did not create is refused rather than entered
    Given a project at a commit
    And bead "beadloom-x.1" has built its clean room holding its own file "own.txt"
    When bead "beadloom-x.1" builds its clean room again
    Then no room is built
    And the refusal is reported as "already_exists"
    And the room still holds "own.txt"

  Scenario: A room says which bead and which commit it was built for
    Given a project at a commit
    When bead "beadloom-x.1" builds its clean room
    Then the room records that it belongs to "beadloom-x.1"
    And the room records the commit it was built from

  Scenario: The bead's own changed file is copied while the room is built
    Given a project at a commit
    And the working tree changes "src/thing.py"
    When bead "beadloom-x.1" builds its clean room carrying "src/thing.py"
    Then the room is built
    And the room holds the working tree's "src/thing.py"

  Scenario: A rebuild replaces the room rather than refreshing it
    Given a project at a commit
    And bead "beadloom-x.1" has built its clean room holding its own file "own.txt"
    When bead "beadloom-x.1" rebuilds its clean room
    Then the room is built
    And the room does not hold "own.txt"

  Scenario: A rebuild refuses a directory that is not a room this command built
    Given a project at a commit
    And a directory named "room-beadloom-x.1" that no room build created
    When bead "beadloom-x.1" rebuilds its clean room
    Then no room is built
    And the refusal is reported as "not_a_room"

  Scenario: A rebuild refuses a room whose record names another bead
    Given a project at a commit
    And a directory named "room-beadloom-x.2" recorded as the room of bead "beadloom-x.1"
    When bead "beadloom-x.2" rebuilds its clean room
    Then no room is built
    And the refusal is reported as "not_a_room"

  Scenario: A room inside the working tree it copies is refused
    Given a project at a commit
    When bead "beadloom-x.1" builds its clean room under the project itself
    Then no room is built
    And the refusal is reported as "inside_the_project"

  Scenario: A file named for the room that the project does not hold is refused
    Given a project at a commit
    When bead "beadloom-x.1" builds its clean room carrying "src/absent.py"
    Then no room is built
    And the refusal is reported as "file_missing"

  Scenario: The invocation handed back points the interpreter at the room's own sources
    Given a project at a commit
    When bead "beadloom-x.1" builds its clean room
    Then the room is built
    And the invocation sets PYTHONPATH to the room's own sources
    And the invocation prints where beadloom was imported from
