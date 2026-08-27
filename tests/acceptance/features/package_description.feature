# BDL-062 bead `.15`, and BDL-UX #211. Measured on the PUBLISHED 3.0.1 wheel in a fresh
# virtual environment: `importlib.metadata` reports the current description while line 3
# of `beadloom --help` still reads `Beadloom - Context Oracle + Doc Sync Engine.` — the
# 1.x sentence 3.0.1 was released to replace.
#
# The defect is not the missed strings. `.4` corrected two copies and
# `tests/test_package_description.py` compared exactly those two, so a check whose
# population was smaller than the fact's population printed the same word as one that had
# read all of it. Swept at `.15`: the retired sentence stood in FIVE live surfaces, not the
# four the hand-off named — the fifth being this repository's own `.beadloom/README.md`,
# which `init` had scaffolded from the same template.
#
# After this bead the check sweeps the shipped surface rather than naming copies, so a
# copy nobody thought to list is found instead of ignored.

@bead:beadloom-viaj.15 @node:cli-commands
Feature: the product's description says the same thing on every surface that states it

  Scenario: The command line's own help states the current description
    Given the installed distribution declares a one-line description
    When a user runs `beadloom --help`
    Then the summary line it prints states that same description

  Scenario: A retired description left behind in a shipped surface is reported
    Given a shipped surface still carries a description the product has retired
    When the description surface is swept
    Then the sweep names that file and the retired sentence it still states

  Scenario: A copy nobody listed is still part of the population
    Given the description is stated in more places than the check was written against
    When the description surface is swept
    Then the sweep reports how many copies it found and holds every one of them to the manifest
