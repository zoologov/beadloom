# BDL-UX #182 and #133, closed in BDL-061 S6 by bead `.78`. A node's symbol hash
# was stored per pair and computed per node, so one changed file marked every
# pair the node owns `stale`. The followers could not be revised — nothing about
# their files had changed — so the tool's only remaining remedy was the bulk
# re-attestation #163 was filed to prevent. Measured on this repository: one new
# package made 72 pairs stale, 10 of which named a modified file.
#
# The repair is a word, not a tolerance. `stale`, `unverified` and `ok` are three
# states: the pair whose own file moved is stale, the pairs that merely share its
# node were not verified, and neither reading is reached by looking less hard.

@bead:beadloom-mr2l.78 @node:sync-check
Feature: a doc pair says whose file moved

  Scenario: A pair whose own file did not change is not called stale
    Given a document paired with three code files of one node
    And one of those code files has changed its symbols
    When the doc-freshness check runs
    Then only the pair whose own file changed is reported stale
    And the other pairs report that a sibling moved

  Scenario: A pair nobody can revise is not told to re-attest it
    Given a document paired with three code files of one node
    And one of those code files has changed its symbols
    When the doc-freshness check runs
    Then the pairs that report a sibling moved name the file that moved
    And the check does not recommend sync-update for those pairs

  Scenario: Integrating a parallel wave does not re-baseline untouched doc pairs
    Given a document paired with three code files of one node
    When a parallel wave's change to one of those files is integrated and reindexed
    Then only the pair whose own file changed is reported stale
    And the untouched pairs keep the baseline they were integrated with
