# The mutation SCOPE convention (BDL-061 S4b, CONTEXT Q5). One Feature per file.

@bead:beadloom-b0xl @node:mutation-scope
Feature: a declared mutation target that would run zero mutants is reported

  Beadloom owns no mutation runner — the tool is the project's choice. What it
  owns is the check that a declared scope could run a single mutant, because a
  score computed over an empty denominator reads as evidence of test strength
  and is evidence of nothing.

  Scenario: a target that is not on disk is reported
    Given a project declaring the mutation target "src/gone/"
    When the mutation scope is checked
    Then the target is reported as running zero mutants

  Scenario: a target outside the configured source paths is reported
    Given a project whose source path is "src" declaring the mutation target "tests/"
    When the mutation scope is checked
    Then the target is reported as outside the source paths

  Scenario: a target holding real source is not reported
    Given a project declaring the mutation target "src/core/" holding a Python module
    When the mutation scope is checked
    Then nothing is reported
