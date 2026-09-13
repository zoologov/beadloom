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

  # BDL-070 B5 (`beadloom-bi78`). The three scenarios below are named by the
  # PRD, and the two after them exist because a part ONE generation under its
  # tagged container cannot tell a climb to the NEAREST tagged ancestor from a
  # climb to the last one — the graphs above have only one tagged ancestor to
  # reach, so both readings give the same answer there.
  #
  # The import project declares its layers as `application` / `domain` /
  # `infrastructure` over the tags `zone-app` / `zone-domain` / `zone-infra`,
  # so the name a finding prints and the tag a node carries are different
  # strings: a message that echoed the tag would read the same under an
  # implementation that never opened the declaration.

  @bead:beadloom-bi78
  Scenario: an import from infrastructure into a domain is reported
    Given a project whose dependencies come only from Python imports
    When the project is linted
    Then no dependency edge was written in the graph file by hand
    And "storage-pool -> catalog" is reported as a layering violation
    And the finding says the source is in layer "infrastructure" and the target in layer "domain"
    And the finding says that layer was inherited from "storage"

  @bead:beadloom-bi78
  Scenario: an import running down the layering is not reported
    Given a project whose dependencies come only from Python imports
    When the project is linted
    Then no finding names "checkout -> catalog"

  @bead:beadloom-bi78
  Scenario: a node with its own tag keeps it rather than inheriting
    Given a project where a part carries a tier its container does not
    When the project is linted
    Then "web-cache -> web-api" is reported as a layering violation
    And "web-cache -> store-db" is reported as a same-layer crossing
    And no finding says "web-cache" inherited a layer
    And no finding names "web-api -> web-cache"

  @bead:beadloom-bi78
  Scenario: a container between the part and the tagged one does not change the answer
    Given a project whose parts are two part_of generations below the tagged container
    When the project is linted
    Then "store-db-pool -> web-api-handlers" is reported as a layering violation
    And the finding says that layer was inherited from "store"

  @bead:beadloom-bi78
  Scenario: the nearer of two tagged containers decides
    Given a project whose parts are two generations down and the nearer container is tagged
    When the project is linted
    Then "store-db-pool -> web-api-handlers" is reported as a same-layer crossing
    And no finding says "web-api-handlers" is in a layer inherited from "web"
