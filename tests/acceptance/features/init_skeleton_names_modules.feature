# BDL-069 S1, the first of the two adopter blockers filed as BDL-UX #282.
#
# `beadloom init --yes --mode bootstrap` wrote a README skeleton for every
# package and, in the same run, installed the freshness rule those skeletons
# fail. The rule is `missing_modules`: a document paired with a source directory
# has to name each module in it. The skeleton named the directory and never the
# modules. Measured on the published 4.0.0 wheel against a fresh repository
# holding `src/ledger/` and `src/billing/`: `init` rc 0, `Graph: 3 nodes`, then
# `beadloom ci` rc 1 on `sync-check FAIL: 4 stale doc(s)`, `missing modules: core`.
#
# This repository cannot show the defect. Every one of its documents was written
# or revised by hand long after `init`, so a scenario stated over its own tree is
# green whether or not the skeleton names anything. Each fixture below is a
# repository built for the purpose, and none of its names exists here.
#
# The fix NAMES the modules and does not attest the pair at write time. The third
# scenario is what holds that decision: a green that came from a recorded verdict
# would survive taking a module's name back out of the document, and this one
# does not.

@bead:beadloom-qylh @node:doc-generator
Feature: the documents init writes pass the freshness check init installs

  Scenario: a repository with two packages under src passes the gate straight after init
    Given a git repository holding two Python packages under src
    When beadloom init is run in bootstrap mode without prompts
    And beadloom ci is run on the repository
    Then the gate exits 0
    And every package document names each module of its package
    And each package document is paired with every code file of its package

  Scenario: a repository whose only package is named after it passes the gate straight after init
    Given a git repository whose only Python package is named after the repository
    When beadloom init is run in bootstrap mode without prompts
    And beadloom ci is run on the repository
    Then the gate exits 0
    And every package document names each module of its package

  Scenario: the green comes from what the document says, not from a recorded verdict
    Given a git repository holding two Python packages under src
    When beadloom init is run in bootstrap mode without prompts
    And one module's name is taken back out of its package document
    And beadloom ci is run on the repository
    Then the gate does not exit 0
    And the freshness check names that module as missing from that document
