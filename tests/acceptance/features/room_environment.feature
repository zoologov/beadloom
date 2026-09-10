# BDL-UX #256, its surviving half. The entry was filed as an import-path defect
# and half of it was already closed: `beadloom-0mdo.37`'s invocation points
# PYTHONPATH at the room's own `src`, and `beadloom-0mdo.38` verified in its own
# room that `import beadloom` prints a path under the room. What survives is the
# ENVIRONMENT. A room isolates the files it was built from and nothing was
# isolating the interpreter those files run under, so a room's verdict was
# decided by whatever the machine happened to have installed: measured at
# `6c4d0a9` over one code base at one commit, `mypy src/` reports 0 errors under
# `.[all,dev]` and 82 under `.[dev]`, and under the second the whole `tui` suite
# leaves the run — three modules skip and the fourth stops the collection.
#
# So the scenarios below are about the interpreter a room's verdict is taken
# under: that the room has one, that which extras it holds is read off this
# project's own legs rather than off a constant, and that a room which could not
# build one says so instead of returning a verdict under somebody else's.

@bead:beadloom-0mdo.74 @node:wave-plan
Feature: a room's verdict is taken under an interpreter the room holds

  Scenario: The room holds the interpreter its suite runs under
    Given a project at a commit whose legs install "dev" and "tui"
    When bead "beadloom-x.1" builds its clean room
    Then the room is built
    And the room holds an interpreter of its own
    And that interpreter imports the project from inside the room
    And the invocation names the room's own interpreter
    And the room records the extras of that interpreter rather than of this process

  Scenario: The extras come from the legs the project declares, not from a constant
    Given a project at a commit whose legs install "dev" and "tui"
    When bead "beadloom-x.1" builds its clean room
    Then the room installed the extras "dev+tui"
    And the room records that the choice came from the project's own legs

  Scenario: Where the legs disagree the room installs every extra any of them names
    Given a project at a commit whose legs install "dev" and "tui"
    And one further leg that installs only "watch"
    When bead "beadloom-x.1" builds its clean room
    Then the room installed the extras "dev+tui+watch"

  Scenario: A caller may name the extras instead, to reproduce one particular leg
    Given a project at a commit whose legs install "dev" and "tui"
    When bead "beadloom-x.1" builds its clean room installing "dev"
    Then the room installed the extras "dev"
    And the room records that the choice was named by the caller

  Scenario: A project whose legs declare no install gets no manufactured environment
    Given a project at a commit that declares no legs
    When bead "beadloom-x.1" builds its clean room
    Then the room is built
    And the room holds no interpreter of its own
    And the room says which environment its verdict is taken under instead

  Scenario: An environment that could not be installed leaves a room that says so
    Given a project at a commit whose legs install an extra it does not declare
    When bead "beadloom-x.1" builds its clean room
    Then the room is built
    And the room holds no interpreter of its own
    And the room reports why the environment was not built
