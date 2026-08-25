# BDL-UX #163, reached one layer below where bead `.78` closed #182/#133. `.78`
# moved the freshness FACT to the file (`sync_state.file_symbols_hash`), so a
# sibling now reports `unverified` instead of `stale`. Attestation stayed on the
# ref: `beadloom sync-update <ref> --yes` re-baselined every pair the ref owned,
# so every run recorded a claim about documents nobody had opened. Measured over
# one epic: 1 pair revised against 27 re-attested, then 13/20, 26/56 and 15/10.
#
# The split is the repair. The node's symbol hash is a FACT about the index and
# still advances for every pair, so the sibling verdict clears once its cause is
# re-baselined. The attestation is a CLAIM about a document somebody read, and is
# written only for the pairs the run has grounds for.

@bead:beadloom-mr2l.85 @node:sync-check
Feature: an attestation covers only the documents the run had grounds for

  Scenario: Re-baselining a ref does not claim the documents nobody read
    Given two documents paired with three code files of one node
    And one of those code files has changed its symbols
    When the ref is re-baselined non-interactively
    Then only the pairs whose own file changed are recorded as attested
    And the run says how many pairs it left unclaimed

  Scenario: An operator attests the one document they read
    Given two documents paired with three code files of one node
    When the operator attests one document by name
    Then only that document's pairs are recorded as attested

  Scenario: The whole ref is still attestable, deliberately
    Given two documents paired with three code files of one node
    And one of those code files has changed its symbols
    When the operator attests every pair of the ref deliberately
    Then every pair of the ref is recorded as attested
