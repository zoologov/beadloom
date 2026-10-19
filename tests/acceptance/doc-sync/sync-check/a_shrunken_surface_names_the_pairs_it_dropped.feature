# BDL-083 S2f (`beadloom-27br`), RFC D11, BDL-UX #353. A Windows checkout of the first
# outside adopter's monorepo counted 167 declared pairs where the macOS checkout of the same
# commit counted 347, and `.beadloom/sync-surface.json` held two integers, so the 180 pairs
# that went had no names. The ledger records the pairs it counted, and a run whose surface
# shrank names the ones it dropped, on the command line and in the Gate.
#
# A deleted code file does not shrink the surface: its pair stays, reported `missing`. What
# shrinks it is a pair no declaration reaches any more, as on the Windows checkout, where no
# `source:` matched. Here one commit misspells the backend service's `source:`, and the one
# file the service owns directly, under no nested node, is held by no document after it.

@bead:beadloom-27br @node:sync-check
Feature: a shrunken surface names the pairs it dropped

  Background:
    Given the monorepo fixture indexed with its declared surface recorded
    And the backend service's source misspelled and the index rebuilt

  Scenario: the recorded ledger lists every declared pair
    Then the ledger lists the pair of the backend document and the file the service owns

  Scenario: sync-check names the dropped pair beside the two counts
    When sync-check runs
    Then its declared surface says the surface shrank and names the dropped pair

  Scenario: the Gate names the dropped pair in its sync-check finding
    When the Gate runs
    Then its sync-check step's finding names the dropped pair
