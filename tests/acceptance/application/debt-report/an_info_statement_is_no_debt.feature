# BDL-083 S1 fix 2 (`beadloom-ilrn`), S1R Major 2, RFC D2. S1b states an import rule whose
# `to:` glob matches no import today as live with nothing to ban, at `info`, and lint
# counts that statement as neither an error nor a warning. The debt collector counted
# every finding that is not an error as a warning, so the same statement was a false
# warning in an adopter's debt score.
#
# Measured on the monorepo fixture, whose digest domain bans every import of `os`.

@bead:beadloom-ilrn @node:debt-report
Feature: a rule stated live with nothing to ban is no debt

  Scenario: the debt report counts an info statement as neither an error nor a warning
    Given the monorepo fixture, whose digest domain bans every import of "os/**"
    When the debt report is collected
    Then the rule engine stated "domain-no-io-imports-digest-os" at info
    And the debt report counts 0 rule errors and 0 rule warnings

  Scenario: an import of the banned module is still a debt
    Given the monorepo fixture, whose digest domain bans every import of "os/**"
    And the digest domain imports "os"
    When the debt report is collected
    Then the debt report counts 1 rule error and 0 rule warnings
