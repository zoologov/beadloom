# BDL-076 J1. Measured by A0 (`beadloom-kcwz`) on 2026-09-30: the resolver skipped
# every relative JS/TS specifier on purpose, so none of the site theme's 26 relative
# imports became an edge, and on a two-file Vue fixture `beadloom why` reported
# "No downstream dependents" for a composable that a component imports. A JS/TS
# project got no `depends_on` edge between its own modules.
#
# The fixtures are not this repository: a TypeScript package with nested folders and
# a JavaScript package whose folders are entered through index files. This
# repository's scan path holds Python only, so a fix that recognised our own tree
# would pass nothing here.

@bead:beadloom-hjr1 @node:import-resolver
Feature: a relative JS/TS import becomes an edge to the node that owns the file it names

  Scenario: why lists the modules that reach a TypeScript node by a relative import
    Given a TypeScript package with nested folders and relative imports
    When the project is indexed
    Then why on "shared" lists "app" and "tracking" as dependents
    And why on "tracking" lists "app" as a dependent

  Scenario: the TypeScript package's edges are exactly the edges its imports name
    Given a TypeScript package with nested folders and relative imports
    When the project is indexed
    Then the depends_on edges are exactly "app -> tracking", "app -> shared", "tracking -> shared"

  Scenario: an import written with a .js extension resolves to the TypeScript source
    Given a TypeScript package with nested folders and relative imports
    When the project is indexed
    Then the import "../tracking/carriers/carrier.js" of "src/app/main.ts" resolves to "tracking"

  Scenario: a relative import that names no file is recorded as unresolved
    Given a TypeScript package with nested folders and relative imports
    When the project is indexed
    Then the import "./missing" of "src/app/main.ts" is recorded with no node
    And the import "lodash" of "src/tracking/track.ts" is recorded with no node

  Scenario: a folder entered through its index file resolves to the folder's node
    Given a JavaScript package whose folders are entered through index files
    When the project is indexed
    Then why on "ui" lists "pages" as a dependent
    And why on "data" lists "pages" as a dependent
    And the depends_on edges are exactly "pages -> ui", "pages -> data"
