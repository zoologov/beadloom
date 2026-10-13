# BDL-082 S2a (`beadloom-6e2o`), the coordinator's addition from S1T's measurement: `init`
# on a project of TypeScript and Vue files without the `languages` extra printed
# "Index: 0 symbols, 0 imports" and nothing else, and every FSD rule then passed with no
# input. The reindex records every code file it saw; the ones whose language has no parser
# installed are now counted by language and named. The line is information: no exit code
# moves on it, and with no import read the rules find nothing, so init exits 0.

@bead:beadloom-6e2o @node:reindex
Feature: the index names the code files it could not read

  Background:
    Given the specification's slice group "features/auth" holding "login" and "register"
    And no grammar is installed for TypeScript

  Scenario: init names the files it read no symbol from
    When beadloom init is run with --yes
    Then the output says "8 TypeScript files, no parser installed — install with: uv tool install "beadloom[languages]""
    And init exits 0

  Scenario: a reindex names them as well
    When beadloom init is run with --yes
    And beadloom reindex is run
    Then the output says "8 TypeScript files, no parser installed — install with: uv tool install "beadloom[languages]""
    And the reindex exits 0

  # BDL-082 S2 fix (`beadloom-us5r.2`), review S2R minor 1: where the reindex read no symbol
  # at all, the older warning fired beside this line, so `init --bootstrap` and a full
  # reindex announced one missing parser twice, with two hints of which one could be run.
  @bead:beadloom-us5r.2
  Scenario: init --bootstrap names a missing parser once, with the command that installs it
    When beadloom init is run with --bootstrap
    Then the output says "8 TypeScript files, no parser installed — install with: uv tool install "beadloom[languages]""
    And exactly one line of the output speaks of a parser
    And init exits 0

  @bead:beadloom-us5r.2
  Scenario: a full reindex names a missing parser once
    When beadloom init is run with --yes
    And beadloom reindex --full is run
    Then the output says "8 TypeScript files, no parser installed — install with: uv tool install "beadloom[languages]""
    And exactly one line of the output speaks of a parser
    And the reindex exits 0
