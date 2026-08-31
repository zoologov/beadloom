# BDL-067, closing BDL-UX #192.
#
# `beadloom init --yes --mode bootstrap` wrote a graph and, one step later,
# wrote the rules that graph fails. Measured on a TypeScript project with a
# single flat `src/index.ts`: rc 0, `Graph: 2 nodes, 0 edges`, then
# `lint --strict` rc 1 on `domain-needs-parent`.
#
# The hole is one branch of `bootstrap_project` — the fallback that runs when
# no source dir has code-bearing subdirectories. It writes one node per source
# dir at the preset's default kind (`domain` under MONOLITH) and no edge, and
# the root-attachment loop that would have rescued it iterates the clusters,
# which are empty on exactly that path.
#
# The scenarios below are stated over the bootstrap's output, not over the one
# branch, because a branch patch leaves the next branch free to forget the edge
# again. The fixture is a project that is not us: a rule that passed by
# recognising Beadloom's own tree would fail these.

@bead:beadloom-e8s4.1 @node:agent-prime
Feature: the bootstrap writes a graph that satisfies the rules it writes

  Scenario: A flat single-source-dir project bootstraps into a graph that passes its own rules
    Given a project whose only source file sits directly in its source directory
    When the project is bootstrapped
    And the bootstrapped graph is linted
    Then the lint reports no error-severity violation

  Scenario: Every domain the bootstrap writes carries a part_of edge
    Given a project whose only source file sits directly in its source directory
    When the project is bootstrapped
    Then every node written with kind domain has an outgoing part_of edge
    And each of those edges names the root node by the ref_id the bootstrap wrote

  Scenario: A parenthesised project name is still the name the edge points at
    Given a project whose name carries parentheses and whose source file sits directly in its source directory
    When the project is bootstrapped
    Then every node written with kind domain has an outgoing part_of edge
    And each of those edges names the root node by the ref_id the bootstrap wrote
    And every edge the bootstrap wrote points at a node the bootstrap wrote

  Scenario: A nested project keeps the parent its classifier chose
    Given a project whose source directory has code-bearing subdirectories
    When the project is bootstrapped
    Then no domain is attached to the root when its classifier already gave it a parent
