# BDL-076 J2, scope added from J3 (`beadloom-tmxa`). J3 made a component's script
# blocks readable for symbols; its imports were still not extracted, so on A0's
# two-file Vue fixture `beadloom why` on a composable reported no dependents even
# though a component imports it. A dynamic `import('...')` is a call expression
# rather than an import statement and was not read either, so a lazily loaded
# module was invisible to the graph.
#
# The fixture is a Vue app that is not this repository.

@bead:beadloom-g9fb @node:import-resolver
Feature: a component's imports and a literal dynamic import become edges

  Scenario: why on a composable lists the component that imports it
    Given a Vue app whose component imports a composable from its script setup block
    When the project is indexed
    Then why on "composables" lists "components" as a dependent
    And the import "../composables/useCounter.js" of "src/components/Counter.vue" is on line 5

  Scenario: a dynamic import with a literal specifier is an edge
    Given a Vue app whose component imports a composable from its script setup block
    When the project is indexed
    Then why on "charts" lists "components" as a dependent
    And the depends_on edges are exactly "components -> composables", "components -> charts"
