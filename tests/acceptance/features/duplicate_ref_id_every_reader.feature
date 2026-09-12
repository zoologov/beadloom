# BDL-069 acceptance (`beadloom-956f`). US-3's criterion, under the name the PRD
# references it by, stated over the WHOLE population rather than over the two
# readers `beadloom-39ap` changed.
#
# `features/duplicate_ref_id_report.feature` pins what the loader and `graph-diff`
# do with a duplicate. That is two bodies. The PRD's goal is wider — "reported
# rather than silently reduced, through every reader of `.beadloom/_graph/` —
# measured at seven, of which one is the declared policy" — and a scenario over
# two of seven would read as covering all of them.
#
# The population is DERIVED, never listed here: `beadloom-4ad3` classified the
# seven by experiment, and `tests/test_what_each_reader_of_the_graph_directory_
# reads_for.py` is where that classification lives. A reader added to the graph
# directory reaches this scenario by being added there, which is what stops an
# eighth reader being born outside the claim.
#
# MEASURED on 2026-09-12, every reader asked for its whole answer over one file
# carrying `ledger` twice — a `service` root with no source, then a `domain`
# holding `src/ledger/`:
#
#   load_graph          reduces to one and NAMES both nodes and the consequence
#   compute_diff        reduces to one and carries the same report on the diff
#   update_node_in_yaml does not reduce — it answers about one ref_id, not a set
#   link                does not reduce — same shape
#   read_declared_docs  does not reduce — both nodes' documents come back
#   _scan_project_files reads bytes; a file that will not parse still has bytes
#   _graph_files_now    reads bytes, same reason
#
# So the claim that holds is: no reader hands back a reduced answer without
# naming what it dropped. The scenario is stated that way rather than as "all
# seven print a warning", because five of them have nothing to warn about and a
# check demanding a warning from them would be satisfied by noise.

@bead:beadloom-956f @node:graph-loader
Feature: a duplicate ref_id is reported by every reader that reduces it away

  Scenario: A graph file carrying one ref_id twice is reported by every reader of the directory
    Given a project that is not this one, whose graph file carries one ref_id twice
    When every reader of the graph directory is asked for its whole answer
    Then the readers that reduce the file to one node name both nodes and the file
    And no reader hands back a reduced answer without naming what it dropped
    And each reader outside that population is named with the reason it drops nothing
    And the population asked is the whole declared population of readers
