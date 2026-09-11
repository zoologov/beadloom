# BDL-069, `beadloom-yn6i` — the rest of the class `beadloom-h7b3` found.
#
# A pair is a document AND a code file, so three files of one package give three
# stale pairs over one README. `h7b3` made the Gate's summary say `stale pair(s)`
# and every `sync-check` line name its code file. Three more surfaces printed the
# same count as documents, measured on the repository below before this bead: the
# terminal dashboard's status bar said `Sync: 3 stale doc(s)`, the site dashboard's
# alert said `3 stale doc(s)`, and `prime` said `Health: 3 stale docs` over three
# identical lines `- domains/ledger/README.md (ledger)`. The JSON of the same run
# held one document.
#
# Each surface keeps counting pairs, because each shows a number some other
# surface already shows as pairs: the status bar is the dashboard's `sync-check`,
# the alert tells the reader to re-run `sync-check`, and `prime`'s list is cut at
# ten with a pointer to `sync-check` for the rest.

@bead:beadloom-yn6i
Feature: a surface that counts stale pairs says pairs, and a listed pair names its code file

  @node:agent-prime
  Scenario: prime lists each stale pair with its code file and counts pairs
    Given a git repository whose package document does not name one of its modules
    When beadloom prime is run on the repository
    Then every stale line prime lists names the code file of its pair
    And no two stale lines prime lists are the same
    And prime's health line counts stale pairs, as many as sync-check reports in JSON

  @node:application
  Scenario: the site dashboard's stale alert counts pairs
    Given a git repository whose package document does not name one of its modules
    When the documentation site is generated for the repository
    Then the dashboard's stale alert counts stale pairs, as many as sync-check reports in JSON

  @node:tui
  Scenario: the terminal dashboard's sync-check notification counts pairs
    Given a git repository whose package document does not name one of its modules
    When sync-check is run from the terminal dashboard
    Then the status bar counts stale pairs, as many as sync-check reports in JSON
