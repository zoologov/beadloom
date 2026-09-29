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

  Rule: an end with no tier of its own is in the tier of its nearest tagged container

    Scenario: a component inherits its layer from the nearest tagged ancestor
      Given a project with two containers in different tiers
      When the project is linted
      Then "store-db -> web-api" is reported as a layering violation
      And the finding says that layer was inherited from "store"

    Scenario: a dependency between peers inside one layer is reported
      Given a project with two peer containers in one tier
      When the project is linted
      Then "ledger-api -> postings-api" is reported as a same-layer crossing

    Scenario Outline: a dependency the layering allows is not reported
      Given a project with <shape>
      When the project is linted
      Then no finding names "<source> -> <target>"

      Examples:
        | shape                             | source     | target       |
        | two containers in different tiers | web-api    | store-db     |
        | two peer containers in one tier   | ledger-api | ledger-store |

    Scenario: a graph with no containment is judged as it was before
      Given a project whose layering is declared as three tiers
      And 3 dependency edges between tiered nodes and 2 with an untiered end
      When the project is linted
      Then the run states that it evaluated 3 of 5 dependency edges
      And no finding is a layering violation

  # BDL-070 B5 (`beadloom-bi78`). A part ONE generation under its tagged container
  # cannot tell a climb to the NEAREST tagged ancestor from a climb to the last one
  # — the graphs above have only one tagged ancestor to reach — so the parts here
  # sit two generations down, carry a tier of their own, or reach their container
  # through a derived edge.
  #
  # The import project declares its layers as `application` / `domain` /
  # `infrastructure` over the tags `zone-app` / `zone-domain` / `zone-infra`, so the
  # name a finding prints and the tag a node carries are different strings: a
  # message that echoed the tag would read the same under an implementation that
  # never opened the declaration.
  @bead:beadloom-bi78
  Rule: the nearest tagged container decides, however the part reaches it

    Scenario: a container between the part and the tagged one does not change the answer
      Given a project with parts two part_of generations below their tagged container
      When the project is linted
      Then "store-db-pool -> web-api-handlers" is reported as a layering violation
      And the finding says that layer was inherited from "store"

    Scenario: the nearer of two tagged containers decides
      Given a project with parts two generations down under a tagged middle container
      When the project is linted
      Then "store-db-pool -> web-api-handlers" is reported as a same-layer crossing
      And no finding says "web-api-handlers" is in a layer inherited from "web"

    Scenario: a node with its own tag keeps it rather than inheriting
      Given a project with a part carrying a tier its container does not
      When the project is linted
      Then "web-cache -> web-api" is reported as a layering violation
      And "web-cache -> store-db" is reported as a same-layer crossing
      And no finding says "web-cache" inherited a layer

    Scenario: an import from infrastructure into a domain is reported
      Given a project with dependencies derived only from Python imports
      When the project is linted
      Then no dependency edge was written in the graph file by hand
      And "storage-pool -> catalog" is reported as a layering violation
      And the finding says the source is in layer "infrastructure" and the target in layer "domain"
      And the finding says that layer was inherited from "storage"

    Scenario Outline: a dependency running down the layering is not reported
      Given a project with <shape>
      When the project is linted
      Then no finding names "<source> -> <target>"

      Examples:
        | shape                                         | source   | target    |
        | dependencies derived only from Python imports | checkout | catalog   |
        | a part carrying a tier its container does not | web-api  | web-cache |
