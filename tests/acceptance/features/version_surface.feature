# BDL-069 S3, `beadloom-jtcx` (BDL-UX #281). Cutting 4.0.0, the version was
# stated in nine places. Four instruments judged parts of that population, no
# two of those parts overlapped, and three places were judged by nothing. Every
# instrument was individually correct and the union was unnamed, so the release
# bumped the four places its author remembered and met the rest one at a time --
# a `lint --strict` error at `severity: error` and two assertions inside the
# suite, both arriving after the work was believed finished.
#
# The derivation behind this command (`beadloom-w4cd`) finds several times more
# places on this repository than the hand-written list of seven or the nine the
# instruments added to it. What the scenario below pins is not the count, which
# moves on every commit that mentions the release, but the three things a report
# of it has to say: where each place is, what checks it, and which ones nothing
# checks.

@bead:beadloom-jtcx @node:version-surface
Feature: the version's homes are derived, and every one of them names what checks it

  Scenario: The version report names each place, its checker, and the places nothing checks
    Given a project stating its version where an instrument reads and where none does
    When the version surface is reported
    Then every place is named with the file and the line that states it
    And the place an instrument holds names that instrument
    And the place no instrument holds is reported as checked by nothing, with the reason
    And the report states the population it read and what it did not read
