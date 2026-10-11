# BDL-082 S1a (`beadloom-r15q`), RFC D1. When every import behind a derived `depends_on` edge
# lands on the target's `@x/<importer's folder>` — feature-sliced.design's cross-import API,
# `entities/song/@x/artist.ts` for the artist entity — the reindex writes `via: "@x"` into the
# edge's `extra`; when some do and one does not, `partly_via: "@x"` and `not_via` naming that
# import. The fact is rebuilt with the import edges on a full and on an incremental index, and
# `beadloom export` carries `via` on the edge.

@bead:beadloom-r15q @node:import-resolver
Feature: a derived edge records whether its imports are cross-imports

  Scenario: an edge every import of which goes through the API is recorded as via @x
    Given the specification's song and artist entities, the artist importing the song's API three ways
    When the project is indexed
    Then the edge from "entities-artist" to "entities-song" records via "@x"
    And beadloom export carries via "@x" on the edge from "entities-artist" to "entities-song"

  Scenario: an incremental index re-derives the fact when one import stops going through the API
    Given the specification's song and artist entities, the artist importing the song's API three ways
    And the project is indexed
    When "src/entities/artist/model/rel.ts" imports the song through its index and the index is updated
    Then the edge from "entities-artist" to "entities-song" records partly via "@x", not via "src/entities/artist/model/rel.ts:1"
    And every derived edge and its extra equals a fresh index of the same tree

  Scenario: an incremental index keeps the fact when the API moves from a file to a folder
    Given the specification's song and artist entities, the artist importing the song's API three ways
    And the project is indexed
    When the song's API for the artist moves into "src/entities/song/@x/artist/index.ts" and the index is updated
    Then the edge from "entities-artist" to "entities-song" records via "@x"
    And every derived edge and its extra equals a fresh index of the same tree
