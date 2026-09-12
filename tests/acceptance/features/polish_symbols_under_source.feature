# BDL-069, `beadloom-6rgr`, found by `beadloom-8lmj` and not fixed there.
#
# `beadloom docs polish`, and the MCP `generate_docs` tool that returns the same
# data, hand an AI agent each node's symbols and tell it to describe the node
# "based on its public API symbols". The symbols were the index rows whose file
# path started with the node's source as a STRING, so a node whose source is
# `src/ledger/` also took `src/ledger_archive/` and `src/ledger_tools.py`.
#
# Measured on a foreign repository with the tree's own `beadloom`, after `init
# --yes --mode bootstrap` and `reindex`: `docs polish --ref-id ledger` named
# `export, record, replay`, where the package holds `record` only. The skeleton
# `init` wrote for the same node listed `record` alone, because since `beadloom-8lmj`
# it walks the directory. No rule reads the polish symbols, so nothing went red.

@bead:beadloom-6rgr @node:doc-generator
Feature: docs polish describes a node from the code under its source and nothing beside it

  Scenario: a package is not given the symbols of a sibling whose name it prefixes
    Given a git repository holding a package, a sibling package and a sibling module whose names start with the package's name
    And beadloom init has been run without prompts on it and the index rebuilt
    When beadloom docs polish is asked for the package's node
    Then the symbols it names are the public symbols of the package and no others

  Scenario: a node whose source is one file is given that file's symbols
    Given a git repository holding a package, a sibling package and a sibling module whose names start with the package's name
    And beadloom init has been run without prompts on it and the index rebuilt
    And a node whose source is one module of the package has been declared and the index rebuilt
    When beadloom docs polish is asked for that node
    Then the symbols it names are the public symbols of that module and no others

  Scenario: docs polish and the document init wrote name the same public symbols for a node
    Given a git repository holding a package, a sibling package and a sibling module whose names start with the package's name
    And beadloom init has been run without prompts on it and the index rebuilt
    When beadloom docs polish is asked for the package's node
    Then the symbols it names are the ones the package's document lists in its Public API table
