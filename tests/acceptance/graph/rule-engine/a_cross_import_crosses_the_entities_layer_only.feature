# BDL-082 S1a (`beadloom-r15q`), RFC D1. feature-sliced.design gives the entities layer one
# sanctioned cross-import: entity A declares `entities/A/@x/B`, a public API for entity B
# alone, "and only use this notation on the Entities layer". The reindex records on a derived
# edge whether every import behind it goes through that API (`via: "@x"`); the layer rule
# reads the fact off the edge, accepts it between two entities and reports it on any other
# layer. Each scenario is the specification's own example or one step away from it, with the
# graph written by hand so no preset decides it.

@bead:beadloom-r15q @node:rule-engine
Feature: a cross-import crosses the entities layer only

  Scenario: the specification's example is clean
    Given the specification's artist entity importing the song's API for it three ways
    And the rules declare the Feature-Sliced layers
    When the project is linted
    Then the layer rule reports nothing between "entities-artist" and "entities-song"

  Scenario: a cross-import between two features is reported in the specification's words
    Given the feature "b" importing the API the feature "a" opens to it
    And the rules declare the Feature-Sliced layers
    When the project is linted
    Then the layer rule reports "features-b" depending on "features-a" once
    And that finding says "`@x` is for the Entities layer only"

  Scenario: an edge one import of which does not go through the API names that import
    Given the specification's artist entity importing the song's API for it three ways
    And "src/entities/artist/model/rel.ts" importing the song through its index on line 2
    And the rules declare the Feature-Sliced layers
    When the project is linted
    Then the layer rule reports "entities-artist" depending on "entities-song" once
    And that finding sits at line 2 of "src/entities/artist/model/rel.ts"

  Scenario: an edge the graph declares by hand keeps its row and is judged as declared
    Given the specification's artist entity importing the song's API for it three ways
    And the graph declares "entities-artist" depending on "entities-song"
    And the rules declare the Feature-Sliced layers
    When the project is linted
    Then the layer rule reports "entities-artist" depending on "entities-song" once
    And that finding does not say "@x"
