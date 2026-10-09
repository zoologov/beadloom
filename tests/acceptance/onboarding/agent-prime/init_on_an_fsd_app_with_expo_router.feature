# BDL-080 S3e (`beadloom-af99.12`). Measured by S3d (`beadloom-chdx`) on the rn-fsd adopter
# fixture: init clustered Expo Router's `app/trail/` as a node named after the route, and
# `app/_layout.tsx` and `app/index.tsx` had no owner but the root service, so the layer
# rule judged 12 of the fixture's 15 depends_on edges and none of the routes'. FSD's
# guidance for Expo Router keeps the routes in `app/` at the root, beside `src/`, and reads
# them as the top layer. The routes are one node here, not one per route (`beadloom-mnuu`).

@bead:beadloom-af99.12 @node:agent-prime
Feature: init reads Expo Router's routes beside a Feature-Sliced src/ as one segment of the app layer

  Background:
    Given an Expo app in the Feature-Sliced layout with Expo Router's routes in app/
    When beadloom init is run with --bootstrap

  Scenario: the routes are one component tagged with the app layer, part of its container
    Then the node "app-routes" is a component with the source "app/"
    And the node "app-routes" is tagged "fsd-app" and part of "app"
    And no node has a source below "app/"

  Scenario: the layer rule judges the routes as the top layer
    When beadloom lint --strict is run
    Then lint reports "fsd-layers" for the edge "pages-trail" -> "app-routes"
    And lint does not report "fsd-layers" for the edge "app-routes" -> "pages-home"

  Scenario: an app/ folder in a project that does not depend on the router is not read as routes
    Given the project does not depend on expo-router
    When beadloom init is run with --bootstrap
    Then no node has the source "app/"
