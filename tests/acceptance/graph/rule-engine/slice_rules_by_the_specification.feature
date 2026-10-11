# BDL-082 S1b (`beadloom-8sml`), RFC D1, D4, D5. The slice rules read feature-sliced.design
# 2.1 rather than a stricter reading of it: `entities/A/@x/B` is a public API A opens to B
# alone, a segment of `shared` or `app` is entered through its index or, in `shared/ui` and
# `shared/lib`, through a per-component index, a segment is named by its purpose, and a slice
# group shares no code. Each scenario is one of the specification's own examples, the trees
# the work item's axes measured, with the graph written by hand so no preset decides it.

@bead:beadloom-8sml @node:rule-engine
Feature: the slice rules read Feature-Sliced Design as the specification writes it

  Scenario: the slice a cross-import API names enters through it, a third slice does not
    Given the specification's song and artist entities, and an album reaching the song's API for the artist
    And the rules declare slice_public_api over the entities layer
    When the project is linted
    Then "slice_public_api" reports nothing from "src/entities/artist/model/artist.ts"
    And "slice_public_api" reports "src/entities/album/model/album.ts" reaching into "entities-song"

  Scenario: a segment of shared is entered through its per-component index and no deeper
    Given a page importing the segments of shared, and shared's segments importing each other
    And the rules declare slice_public_api over the pages and the shared layer
    When the project is linted
    Then "slice_public_api" reports line 2 of "src/pages/home/ui/home.ts" and no other line of it
    And "slice_public_api" reports nothing from "src/shared/routes/paths.ts"

  Scenario: a segment named by its essence is reported, one named by its purpose is not
    Given a feature holding the segments "analytics" and "components"
    And the rules declare slice_shape over the features layer
    When the project is linted
    Then "slice_shape" reports the folder "components/" of "features-x"
    And "slice_shape" reports nothing naming "analytics/"

  Scenario: a code file at the top of a slice group is reported
    Given the slice group "auth" of the features layer, holding "login", "register" and a code file
    And the rules declare slice_shape over the features layer
    When the project is linted
    Then "slice_shape" reports the code file "src/features/auth/shared.ts" of a group
