# BDL-069 S1, the second half of BDL-UX #282.
#
# A staleness verdict printed a command that could not change it. Measured before
# this epic on a repository whose package document does not name one of its
# modules: `beadloom ci` printed "run `beadloom sync-update <ref>` to review and
# re-attest", `sync-update --yes --all` then exited 0 and reported the pairs
# re-attested, and the verdict did not move. `sync-update` re-baselines recorded
# hashes, and `missing_modules` is a claim about what the document says.
#
# Two more defects lived on the same lines. A pair is a document AND a code file,
# so three files in one package give three pairs over one README, and the text
# line dropped the code file that tells them apart: three different pairs printed
# as three identical lines. The summary counted them as `3 stale doc(s)` over one
# document.
#
# Since `beadloom-qylh` a virgin `init` names every module, so `init` no longer
# produces this staleness. Each scenario below takes one module's name back out
# of a document `init` wrote, which is the state an adopter reaches by editing.

@bead:beadloom-h7b3 @node:ci-gate
Feature: a stale verdict names its pair, and the remediation it prints can be followed

  @node:sync-check
  Scenario: A staleness reason that re-attesting cannot clear says so in its remediation
    Given a git repository whose package document does not name one of its modules
    When beadloom ci is run on the repository
    Then the gate does not exit 0
    And no finding about that document tells the reader to re-attest it
    And every finding about that document names the module the document lacks

  Scenario: the remediation the gate printed turns the gate green once it is followed
    Given a git repository whose package document does not name one of its modules
    When beadloom ci is run on the repository
    And the document is revised the way the gate's remediation says
    And beadloom ci is run on the repository
    Then the gate exits 0

  @node:cli-commands
  Scenario: sync-update names the pairs it left stale and why attesting could not move them
    Given a git repository whose package document does not name one of its modules
    When beadloom sync-update is run for every stale ref without prompts
    Then the command exits 0
    And its output names every pair the freshness check still reports stale
    And its output says re-attesting cannot clear the reason those pairs are stale

  @node:cli-commands
  Scenario: two pairs over one document render as two distinguishable lines
    Given a git repository whose package document does not name one of its modules
    When beadloom sync-check is run on the repository
    Then every stale line names the code file of its pair
    And no two stale lines are the same
    And the gate's summary counts stale pairs, as many as sync-check reports in JSON
