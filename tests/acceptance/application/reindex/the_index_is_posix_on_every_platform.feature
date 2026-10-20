# BDL-083 S2f (`beadloom-27br`), RFC D11, BDL-UX #353. On a teammate's Windows checkout of
# the first outside adopter's monorepo, the index stored every path with a backslash while the
# graph declares `source:` with a forward slash. Every directory node read "no indexed code",
# every file node read stale, and the declared surface counted 167 pairs where the macOS
# checkout of the same commit counted 347.
#
# The Windows CI leg is withdrawn by the owner's decision (BDL-074), so this scenario is the
# measurement: every path `relative_to` returns is made to print with a backslash, as it does
# on Windows, and the monorepo fixture is indexed under it. It simulates the separator of a
# relative path only; Windows itself is not run.

@bead:beadloom-27br @node:reindex
Feature: the index spells a path the same way on every platform

  Background:
    Given the monorepo fixture indexed and sync-checked on this platform
    And a second checkout of it on which a relative path prints with a backslash

  Scenario: every path the index holds is written with forward slashes
    When the second checkout is indexed and sync-checked
    Then no path in the second checkout's index holds a backslash

  Scenario: the second checkout declares the pairs the first one declares
    When the second checkout is indexed and sync-checked
    Then the second checkout's declared pairs are the first checkout's, pair for pair
    And no node of the second checkout reads no indexed code
