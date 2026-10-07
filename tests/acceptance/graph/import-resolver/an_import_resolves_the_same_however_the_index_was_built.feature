# BDL-078, `beadloom-nh7h`. Measured on 2026-10-04: the data file a fresh clone published
# had 582 edges and a developer's checkout of the same commit had 583. A fresh index
# resolved `tui`'s import of `beadloom.application.graph_reads` to `application`, and the
# same tree indexed a second time resolved it to `graph-reads`, the node whose source is
# that file. The resolver asked the index whether the imported file existed; a module of
# re-exports has no symbol, and a full reindex filled its file list only after resolving
# the imports, so the answer depended on whether an index had existed before.
#
# The fixture is a project that is not this one: a screen that imports a facade module
# made of re-exports, and the facade is a node of its own inside its domain.

@bead:beadloom-nh7h @node:import-resolver
Feature: an import resolves to the same node however the index was built

  Scenario: a fresh index resolves an import of a symbol-less module to the node owning its file
    Given a project whose screen imports a facade module that only re-exports
    When the project is indexed
    Then the import "shop.app.facade" of "src/shop/ui/screen.py" resolves to "facade"

  Scenario: an incremental index after the facade is added equals a fresh index
    Given a project whose screen imports a facade module that does not exist yet
    And the project is indexed
    When the facade module is written and the index is updated
    Then the import "shop.app.facade" of "src/shop/ui/screen.py" resolves to "facade"
    And every resolved import and every derived edge equals a fresh index of the same tree

  Scenario: an incremental index after the facade is removed equals a fresh index
    Given a project whose screen imports a facade module that only re-exports
    And the project is indexed
    When the facade module is deleted and the index is updated
    Then every resolved import and every derived edge equals a fresh index of the same tree
