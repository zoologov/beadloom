# BDL-070 B3 (`beadloom-ku26`). The release that changes what the layer rule
# decides. Until it, the rule read a node's OWN layer tags and passed over every
# edge whose ends carried none — 16 of 365 live `depends_on` edges on this
# repository, measured 2026-09-13 — so a dependency between two components
# nobody tagged was legal by not being looked at.
#
# An end now takes its layer from the nearest `part_of` container that declares
# one, and an edge inside one layer is legal when both ends share such a
# container and a finding when they do not (RFC Q1).
#
# The graphs below declare `tier-web` / `tier-core` / `tier-store`, a vocabulary
# this repository does not ship, because a scenario written over `layer-domain`
# would pass against an implementation that hardcoded it.

@bead:beadloom-ku26 @node:rule-engine
Feature: the layer rule judges an edge by the layer each end is in

  Scenario: a component inherits its layer from the nearest tagged ancestor
    Given a project whose layering is declared as two containers in different tiers
    When the project is linted
    Then "store-db -> web-api" is reported as a layering violation
    And the finding says that layer was inherited from "store"

  Scenario: the same dependency the right way round is not reported
    Given a project whose layering is declared as two containers in different tiers
    When the project is linted
    Then no finding names "web-api -> store-db"

  Scenario: a dependency between peers inside one layer is reported
    Given a project whose layering is declared as two peer containers in one tier
    When the project is linted
    Then "ledger-api -> postings-api" is reported as a same-layer crossing

  Scenario: a dependency between two parts of one container is not reported
    Given a project whose layering is declared as two peer containers in one tier
    When the project is linted
    Then no finding names "ledger-api -> ledger-store"

  Scenario: a graph with no containment is judged as it was before
    Given a project whose layering is declared as three tiers
    And 3 dependency edges between tiered nodes and 2 with an untiered end
    When the project is linted
    Then the run states that it evaluated 3 of 5 dependency edges
    And no finding is a layering violation
