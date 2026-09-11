# BDL-069 S1, `beadloom-8lmj`, found by `beadloom-qylh` and not fixed there.
#
# A skeleton's `## Public API` table was read out of the index. `init --yes` and
# `init --bootstrap` write their skeletons BEFORE their reindex, so on a virgin
# project there is no index at that moment and every skeleton was written without
# the table. The wizard re-indexes before it asks "Generate doc skeletons?", so
# the same project got a different document depending on which entry point ran.
# Measured on a wheel built from this tree against a foreign repository holding
# `src/ledger/` and `src/billing/`: `diff -r` between the `--yes` and wizard
# `docs/` trees differed in exactly the two tables, and `beadloom ci` was rc 0 on
# both, because no rule reads the table.
#
# A fourth case has the same cause: `init` lists the index in `.gitignore`, so a
# clone has none, and `beadloom docs generate` there wrote the document without
# the table too.
#
# The fix reads the symbols off the disk inside the skeleton writer. The order
# `init` runs its steps in is untouched: skeletons still precede the reindex that
# loads the `docs:` field they patch into the graph.

@bead:beadloom-8lmj @node:doc-generator
Feature: the documents init writes list the public API of the code they describe

  Scenario: init without prompts lists each package's public symbols before any index exists
    Given a git repository holding two Python packages with public and private symbols
    When beadloom init is run without prompts on it
    Then every package document carries a Public API table
    And each table names every public symbol of its package and no private one

  Scenario: the three ways to run init write the same documents for one project
    Given three copies of a git repository holding two Python packages with public and private symbols
    When beadloom init is run without prompts on the first copy
    And beadloom init is run with the bootstrap flag on the second copy
    And the beadloom init wizard is run with every default answer on the third copy
    Then the three copies hold the same documents, byte for byte
    And every package document of the first copy carries a Public API table

  Scenario: a clone without an index regenerates the document its original holds
    Given a git repository holding two Python packages with public and private symbols
    And beadloom init has been run without prompts on it and the result committed
    And a clone of that repository, which carries no index
    When one package document is deleted from the clone
    And beadloom docs generate is run on the clone
    Then the clone's regenerated document is byte-identical to the original's
