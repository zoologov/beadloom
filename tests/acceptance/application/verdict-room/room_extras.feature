# The optional extras a room installed, and why a verdict cannot be read without
# them (BDL-068 S6, BDL-UX #236). One Feature per file.

@bead:beadloom-0mdo.38 @node:verdict-room
Feature: a room states the optional extras it installed

  Measured on this repository at 6c4d0a9, in one clean room, over one code base
  at one commit: `mypy src/` reports 0 errors under `.[all,dev]` and 82 under
  `.[dev]`, and under the second the whole `tui` suite leaves the run — three of
  its four modules skip and the fourth stops the collection. Nothing about the
  code differs between those two runs. The environment does, and no report said
  so.

  A room's name isolates its FILES. Which optional extras its interpreter has
  installed is a second question, and a clean-room report that cannot be
  reproduced from what it prints is a claim rather than a measurement.

  The extras are DERIVED on both sides: what this run has, from the project
  distribution's own metadata against the distributions the interpreter holds;
  what a leg installs, from the install step the workflow declares. Neither is
  a list this tool owns.

  Scenario: the room this run is in names the extras it installed
    Given a project whose packaging is this project's own
    And a workflow job that installs the project with the "dev" extra
    When the rooms are reported
    Then the room this run is in names an extras dimension

  Scenario: a leg installing different extras is not entered, and says which
    Given a project whose packaging is this project's own
    And a workflow job that installs the project with the "search" extra
    When the rooms are reported
    Then that leg is reported as not entered
    And the reason names the extras that differ

  Scenario: extras are an axis a checklist can loop over
    Given a project whose packaging is this project's own
    And a workflow job that installs the project with the "dev" extra
    When the extras axis is asked for
    Then the extras that leg installs are printed

  Scenario: a project this interpreter does not hold carries no extras dimension
    Given a project whose packaging names a distribution this interpreter does not hold
    And a workflow job that installs the project with the "dev" extra
    When the rooms are reported
    Then no room carries an extras dimension
    And the report says the extras could not be resolved

  Scenario: a clean room records the extras its interpreter installed
    Given a bead whose room has been built
    When the room's record is read
    Then it names the extras the invocation's interpreter has
