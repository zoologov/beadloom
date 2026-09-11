# BDL-069 S2, the LOADER half of BDL-UX #214. `beadloom-cgco` closed the writer
# half: a root node and the sole package no longer take one `ref_id`. This half
# is for the graphs that already exist — bootstrapped by an earlier release, or
# written by hand — where two nodes still share a `ref_id` and the reduction to
# one was performed with five words that named neither node.
#
# Measured on `myapp` / `src/myapp/` at 390850ae, before this bead: the loader
# said `Duplicate ref_id 'myapp', skipped` and kept the FIRST node, the empty
# service root; the node it dropped was the `domain` carrying `src/myapp/`.
# `graph/diff.py` read the same file and kept the LAST, so a `beadloom diff`
# described a node the graph does not hold, and said nothing about why.
#
# The report is placed where the parse happens, not in
# `onboarding.graph_files.each_graph_file`: six of the seven readers of
# `.beadloom/_graph/` do not go through that policy (`beadloom-4ad3`'s
# measurement), so a report there would cover one reader and read as covering
# the directory. `graph-diff` is the named demonstration — it reaches neither
# the policy nor `load_graph`, and it now reports what it dropped.
#
# The fixture is a project that is not this one. This repository cannot produce
# the collision: `src/beadloom/` holds seven packages and none is named
# `beadloom`.

@bead:beadloom-39ap @node:graph-loader
Feature: a graph that carries one ref_id twice says which node it kept

  Scenario: the loader names the node it kept and the node it dropped
    Given a graph file that carries one ref_id twice, where only the dropped node declares a source
    When the graph is loaded
    Then the report names the ref_id and the file, the kind and the source of both nodes
    And the report says what the dropped node's source now owns

  Scenario: the report reaches graph-diff, which reads the directory without the policy
    Given a graph file that carries one ref_id twice, where only the dropped node declares a source
    When the graph diff reads that graph against the commit before the duplicate
    Then graph-diff reports the same duplicate the loader reports
    And graph-diff and the loader name the same node as the one that was kept

  Scenario: the report is a report and not a refusal
    Given a graph file that carries one ref_id twice, where only the dropped node declares a source
    When the graph is loaded
    Then the load is not refused and every node it can keep is in the graph
    And a graph whose only anomaly is the duplicate reports no change against itself
