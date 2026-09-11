# BDL-069, `beadloom-rqma.4`, found by `beadloom-6rgr` and not fixed there.
#
# `beadloom reindex` stores each node's HTTP routes in `nodes.extra`, and `beadloom
# docs polish`, and the MCP `generate_docs` tool that returns the same data, hand
# them to an AI agent as the node's API. A route was given to every node whose
# source was a STRING prefix of the route's file, so a node whose source is
# `src/ledger/` also took the routes of `src/ledger_archive/`.
#
# Measured on a foreign repository with the tree's own `beadloom`, after `init --yes
# --mode bootstrap` and `reindex`: with a FastAPI handler for `/replay` in
# `src/ledger_archive/api.py`, `docs polish --ref-id ledger --format json` named
# `GET /replay` from that file as a route of `ledger`.
#
# The rule "a file lies under a node's source" was written three times, in three
# domains, and only this one was wrong. The routes now go through the one rule the
# other two readers call, so these scenarios bind to the reader that was wrong.

@bead:beadloom-rqma.4 @node:reindex
Feature: docs polish names a node's routes from the code under its source and nothing beside it

  Scenario: a package is not given the routes of a sibling whose name it prefixes
    Given a git repository holding a package and a sibling package whose name starts with the package's name, each serving one route
    And beadloom init has been run without prompts on it and the index rebuilt
    When beadloom docs polish is asked for the package's node
    Then the routes it names are the routes the package serves and no others

  Scenario: a node whose source is one file is given that file's routes
    Given a git repository holding a package and a sibling package whose name starts with the package's name, each serving one route
    And beadloom init has been run without prompts on it and the index rebuilt
    And a node whose source is the package's route module has been declared and the index rebuilt
    When beadloom docs polish is asked for that node
    Then the routes it names are the routes that module serves and no others
