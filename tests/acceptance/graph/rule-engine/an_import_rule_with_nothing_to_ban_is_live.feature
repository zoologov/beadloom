# BDL-083 S1b (`beadloom-q8x6`), RFC D2, BDL-UX #328. A `forbid_import` rule whose
# `to:` glob matches no import the index holds was reported as a rule that "cannot
# fire", in the same sentence as a glob no import could ever match. On the first
# adopter's project `to: os/**` read as dead while `import os` fired it, and two
# reviews concluded the boundary was unchecked. The two are now two verdicts: a glob
# that can match no import path is a rule that cannot fire, at warn; a glob that can
# match and has nothing to ban today is a live rule, stated at info.
#
# Measured on the monorepo fixture, whose digest domain bans every import of `os`.

@bead:beadloom-q8x6 @node:rule-engine
Feature: an import rule with nothing to ban is told from a rule that cannot fire

  Scenario: a banned module the project does not import leaves the rule live
    Given the monorepo fixture, whose digest domain bans every import of "os/**"
    When the project is linted
    Then "domain-no-io-imports-digest-os" is stated live with nothing to ban, at info
    And no finding says "domain-no-io-imports-digest-os" cannot fire
    And the strict lint passes

  Scenario: an import of the banned module fires the rule that was stated live
    Given the monorepo fixture, whose digest domain bans every import of "os/**"
    And the digest domain imports "os"
    When the project is linted
    Then "domain-no-io-imports-digest-os" reports the import in "backend/src/digest/sections.py"
    And "domain-no-io-imports-digest-os" is not stated live with nothing to ban
    And the strict lint fails

  Scenario: a glob that names a source root cannot fire
    Given the monorepo fixture, whose digest domain's rule "digest-no-backend-src-file-history" bans every import of "backend/src/file_history/**"
    When the project is linted
    Then "digest-no-backend-src-file-history" cannot fire, at warn, because its glob begins with "backend"

  Scenario: a test boundary with nothing to ban is live too
    Given the monorepo fixture, whose backend unit tests ban every import of "os/**"
    When the project is linted
    Then "backend-unit-tests-no-os" is stated live with nothing to ban, at info
    And no finding says "backend-unit-tests-no-os" cannot fire
