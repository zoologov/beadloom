# BDL-080 S3c (`beadloom-5t8d`), RFC D4. Measured before this bead on the synthetic tree
# of `tests/support/fsd_tree.py`: init chose the monolith preset, wrote each layer as a
# domain and each slice as the layer's child, declared no layer rule, and `lint --strict`
# found nothing — a cross-import inside a layer, a deep import past a slice's index and a
# slice holding a folder that is no segment all read green. Measured during this bead: an
# import edge init writes into the YAML is declared, and kept a cross-import removed from
# the code red; so init writes none for an FSD frontend and the reindex derives them.

@bead:beadloom-5t8d @node:agent-prime
Feature: init reads a Feature-Sliced frontend slice by slice and writes the FSD rules

  Background:
    Given a frontend in the Feature-Sliced layout with legacy folders beside its layers
    When beadloom init is run with --bootstrap

  Scenario: each slice is a component tagged with its layer, part of the frontend
    Then init chose the "fsd" preset
    And the node "features-auth" is a component tagged "fsd-features" and part of the root
    And the node "shared-ui" is a component tagged "fsd-shared" and part of "shared"
    And no node is written for the layer folder "src/features"

  Scenario: folders beside the layers are nodes outside the layer rule
    Then the node "components" is a component tagged "fsd-legacy" and part of the root
    And the node "hooks" is a component tagged "fsd-legacy" and part of the root

  Scenario: the rules init writes find the three planted violations
    When beadloom lint --strict is run
    Then lint exits 1
    And lint reports "fsd-public-api" for "src/widgets/header/ui/Header.ts"
    And lint reports "fsd-layers" for the edge "features-cart" -> "features-auth"
    And lint reports "fsd-slice-shape" for "features-cart"

  Scenario: a cross-import removed from the code is no longer reported
    Then init wrote no depends_on edge into the graph YAML
    When the cross-import from "src/features/cart/model/cart.ts" is removed
    And beadloom lint --strict is run
    Then lint does not report "fsd-layers" for the edge "features-cart" -> "features-auth"

  Scenario: a project that runs no Steiger is given the lint:fsd script
    Then package.json runs "steiger ./src" as "lint:fsd"

  Scenario: init names the code, not the scaffold, as what breaks the rules it wrote
    Then init exits 1
    And init says "your code does not pass the rules this command wrote"
    And init does not say "defect in Beadloom's bootstrap"
