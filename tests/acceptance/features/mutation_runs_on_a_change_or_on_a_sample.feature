# BDL-074 D1, `beadloom-vr0b`.
#
# The whole-scope nightly mutated every declared target and was killed by its runner at
# about 95 minutes, ten times, before it reached a verdict. It was retired on 2026-09-27.
# What replaces it is two narrower runs, and each has to say what it covered, because a
# narrower run that does not say so reads as the whole scope:
#
# - a pull request mutates the functions it changed and runs the tests the binding ties to
#   their node, so `beadloom mutation --changed-since` names the change's population, the
#   node of each function, the tests bound to that node, and how many test files the
#   binding cannot place yet;
# - a weekly run mutates a random sample of the declared scope, so its score is reported
#   with the interval a sample of that size supports.
#
# Survivors are listed by the node that owns their file in both runs.

@bead:beadloom-vr0b
Feature: a mutation run covers a change or a sample, and says what it covered

  @node:mutation-scope @node:cli-commands
  Scenario: a change to one function names that function, its node and the tests bound to it
    Given a ledger project whose package is the declared mutation scope, committed to git
    And a unit test laid out under the mirror of the posting module
    When the post function is changed and the population of the change is printed
    Then the population is the post function of the posting module, over the posting node
    And the posting node's bound test is the laid-out unit test
    And the population is printed without a score it does not have

  @node:mutation-scope @node:cli-commands
  Scenario: a change that touches no function of the declared scope says its population is empty
    Given a ledger project whose package is the declared mutation scope, committed to git
    When only the readme is changed and the population of the change is printed
    Then the population is stated as empty

  @node:mutation-scope @node:cli-commands
  Scenario: while a test file is placed under no node, the change says its bound tests can be short
    Given a ledger project whose package is the declared mutation scope, committed to git
    And a test file at the top of the tests folder
    When the post function is changed and the population of the change is printed
    Then the change says 1 of 1 test files is placed under no node

  @node:mutation-scope @node:cli-commands
  Scenario: survivors are listed under the node that owns their file
    Given a ledger project whose package is the declared mutation scope, committed to git
    When a run over the posting module is reported with one surviving mutant of the post function
    Then the report lists 1 survivor under the posting node

  @node:mutation-scope @node:cli-commands
  Scenario: a score measured on a random sample carries the interval the sample supports
    Given a ledger project whose package is the declared mutation scope, committed to git
    When a sample of 200 mutants out of 7000 is reported with 180 killed and 20 survived
    Then the score reads 90.0% with a 95% interval from 85.1% to 93.4%
